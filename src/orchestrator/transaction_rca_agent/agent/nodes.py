"""
Transaction RCA Agent Nodes.

Business logic nodes for performing root cause analysis on unprocessed transactions.
"""

import logging
import json
import copy
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from agent.state import TransactionRCAAgentState
from domain.models import TransactionContext, RCAAnalysis, RCAResponse, HumanIntervention
from agent.llm_factory import LLMFactory

logger = logging.getLogger("transaction_rca_agent.nodes")

# Allowed checkpoint names (ordered)
ALLOWED_CHECKPOINTS = [
    "ingestion",
    "authorization",
    "routing",
    "ledger",
    "settlement_file_generated",
    "bank_acknowledged",
    "credited",
]

# Allowed RCA categories
RCA_CATEGORIES = [
    "Sync Issues",
    "Configuration Issues",
    "Routing Issues",
    "Dependency Failures",
    "Merchant Data Issues",
    "Compliance / Risk Holds",
    "Unknown / System Defect",
]

RCA_SYSTEM_PROMPT = """You are a senior fintech operations analyst performing Root Cause Analysis (RCA) on unprocessed transactions.

Your task is to analyze a single transaction and classify the root cause into exactly ONE category.

## Allowed RCA Categories:
- Sync Issues: Data mismatch between systems, partial writes
- Configuration Issues: Wrong TID / MDR / routing config
- Routing Issues: Incorrect bank or network routing
- Dependency Failures: Bank downtime, file rejection
- Merchant Data Issues: Account closed/changed, invalid IFSC
- Compliance / Risk Holds: Regulatory or risk-related holds
- Unknown / System Defect: When evidence is weak, indirect, or contradictory

## Allowed Checkpoints (in order):
1. ingestion
2. authorization
3. routing
4. ledger
5. settlement_file_generated
6. bank_acknowledged
7. credited

## Mandatory Reasoning Sequence:
1. Reconstruct the full transaction journey end-to-end
2. Identify the last successful checkpoint (furthest checkpoint with explicit success confirmation)
3. Identify abnormal, missing, or stalled steps
4. Consider multiple plausible RCA categories
5. Evaluate strength and quality of evidence:
   - Direct: Explicit system signal
   - Indirect: Inferred from sequence or absence
   - Weak / Contradictory
6. Identify contradictions or missing signals
7. Select the most plausible RCA category
8. Clearly justify the decision using explicit evidence

## Judgement Guardrails (MANDATORY):
- Direct system signals override inferred absence
- Missing data must reduce confidence
- Contradictory signals must be explicitly surfaced
- If two or more RCA categories are equally plausible → classify as "Unknown / System Defect"
- NEVER invent: logs, timestamps, status transitions, external failures
- Treat input as ground truth - do not assume missing data
- Absence of data is NOT proof of success or failure

## Confidence Scoring:
- Missing critical checkpoints → confidence ≤ 0.6
- Contradictory signals → confidence ≤ 0.5
- Only indirect evidence → confidence ≤ 0.5
- Clear direct signals with no contradiction → confidence ≥ 0.7

## Analyst Reasoning Heuristics (Non-Binding):
- Prefer Configuration Issues when required static attributes (TID, MDR, routing config) are missing or invalid
- Prefer Merchant Data Issues when merchant account, IFSC, or bank details are invalid or changed
- Prefer Dependency Failures only when explicit external signals exist (bank downtime, file rejection)
- Prefer Sync Issues when transaction data exists across systems but is inconsistent or partially written
- Prefer Routing Issues when transaction is routed incorrectly despite valid configuration
- Prefer Unknown / System Defect when evidence is weak, indirect, or contradictory

## Output Requirements:
You MUST return ONLY valid JSON matching this exact structure:
{
  "rca_analysis": {
    "rca_category": "<one allowed category>",
    "confidence": 0.0,
    "last_successful_checkpoint": "<checkpoint name>",
    "transaction_narrative": "<concise journey summary>",
    "key_anomalies": ["<abnormal or missing observations>"],
    "contradictions_observed": ["<conflicting signals, if any>"],
    "evidence": ["<explicit evidence taken directly from input>"],
    "alternative_causes_considered": ["<other plausible categories evaluated>"],
    "final_reasoning": "<why this RCA category fits best>"
  },
  "human_intervention": {
    "action_required": true,
    "prompt": ""
  }
}

🚫 CRITICAL RESTRICTIONS:
- No additional fields
- No free text outside JSON
- rca_category must be exactly one of the allowed categories
- last_successful_checkpoint must be exactly one of the allowed checkpoint names
- DO NOT include questions, prompts, or "Next Steps" in ANY field
- DO NOT ask "Would you like to..." or similar questions
- DO NOT include action items or recommendations in final_reasoning
- final_reasoning should ONLY explain why the RCA category fits best - nothing else
- human_intervention.prompt must ALWAYS be an empty string ""
"""


def extract_llm_error_message(error: Exception) -> str:
    """Extract a user-friendly message from LLM API errors."""
    error_str = str(error)

    # Check for common error patterns
    if "402" in error_str or "credits" in error_str.lower():
        return "⚠️ **API Credits Exhausted**\n\nThe AI service has run out of credits. Please try again later or contact support to add more credits."
    elif "429" in error_str or "rate limit" in error_str.lower():
        return "⚠️ **Rate Limit Reached**\n\nToo many requests. Please wait a moment and try again."
    elif "401" in error_str or "unauthorized" in error_str.lower():
        return "⚠️ **Authentication Error**\n\nThere's an issue with the AI service configuration. Please contact support."
    elif "timeout" in error_str.lower():
        return "⚠️ **Request Timeout**\n\nThe AI service took too long to respond. Please try again."
    else:
        return f"⚠️ **AI Service Error**\n\nUnable to process your request: {error_str[:200]}"


class TransactionRCANodes:
    """Business logic nodes for Transaction RCA analysis."""

    def __init__(self):
        self.llm = LLMFactory.get_llm(
            "TRANSACTION_RCA_AGENT_LLM", temperature=0.1, max_tokens=2000
        )
        self.json_parser = JsonOutputParser()

    async def normalize_input_with_llm(self, raw_input: Any) -> Dict[str, Any]:
        """
        Use LLM to normalize input data to the expected TransactionContext format.
        Handles type mismatches like empty strings for dicts, lists for strings, etc.
        """
        normalization_prompt = """You are a data normalization assistant. Your task is to convert input data into a valid TransactionContext JSON format.

The expected format is:
{
  "transaction_id": "string",
  "checkpoints": [
    {
      "checkpoint_name": "string",
      "status": "string",
      "timestamp": "string or null",
      "details": {}  // MUST be a dictionary/object, never a string. If empty string, convert to {}
    }
  ],
  "merchant_config": {},  // dictionary
  "merchant_data": {},    // dictionary
  "external_signals": {}, // dictionary
  "risk_indicators": {},  // dictionary
  "observational_notes": "string"  // MUST be a string, not a list. If list, join with "; "
}

IMPORTANT RULES:
1. If "details" is an empty string "", convert it to an empty dictionary {}
2. If "details" is a string with content, try to parse it as JSON, or wrap it in {"message": "..."}
3. If "observational_notes" is a list, join elements with "; " to make a string
4. If "observational_notes" is missing or null, set it to null
5. Preserve all other fields as-is
6. Return ONLY valid JSON, no markdown, no explanations

Input data:
{input_data}

Return the normalized JSON:"""

        try:
            # Convert input to JSON string for LLM
            if isinstance(raw_input, (dict, list)):
                input_str = json.dumps(raw_input, indent=2)
            else:
                input_str = str(raw_input)

            messages = [
                SystemMessage(content="You are a JSON data normalization assistant. Return only valid JSON."),
                HumanMessage(content=normalization_prompt.format(input_data=input_str))
            ]

            # Use a separate LLM instance for normalization (can be faster/lighter model)
            normalization_llm = LLMFactory.get_llm(
                "TRANSACTION_RCA_AGENT_LLM", temperature=0, max_tokens=2000
            )
            
            response = await normalization_llm.ainvoke(messages)
            content = response.content.strip()

            # Remove markdown code blocks if present
            if "```" in content:
                # Extract JSON from code blocks
                parts = content.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{") or part.startswith("["):
                        content = part
                        break
                content = content.strip()

            # Try to extract JSON from the response
            # Look for JSON object boundaries
            start_idx = content.find("{")
            if start_idx == -1:
                raise ValueError("No JSON object found in LLM response")
            
            # Find matching closing brace
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(content)):
                if content[i] == "{":
                    brace_count += 1
                elif content[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count != 0:
                # Incomplete JSON, try to parse what we have or fallback
                logger.warning("Incomplete JSON from LLM, attempting to parse partial JSON")
                # Try to parse anyway, might work if it's just trailing content
                try:
                    normalized_data = json.loads(content[start_idx:])
                except json.JSONDecodeError:
                    raise ValueError(f"Incomplete JSON from LLM: {content[:200]}")
            else:
                json_str = content[start_idx:end_idx]
                normalized_data = json.loads(json_str)
            
            logger.info("Successfully normalized input with LLM")
            return normalized_data

        except Exception as e:
            response_content = "N/A"
            try:
                if 'response' in locals() and hasattr(response, 'content'):
                    response_content = response.content[:500]
            except:
                pass
            logger.error(f"LLM normalization error: {e}. Response content: {response_content}")
            # Fallback: try to fix common issues manually
            logger.info("Falling back to manual normalization")
            return self._manual_normalize(raw_input)

    def _manual_normalize(self, raw_input: Any) -> Dict[str, Any]:
        """Fallback manual normalization for common issues."""
        logger.info("Starting manual normalization")
        
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse input as JSON: {raw_input[:200]}")
                return {"error": "Invalid input format - not valid JSON"}

        if not isinstance(raw_input, dict):
            logger.error(f"Input is not a dictionary: {type(raw_input)}")
            return {"error": "Input must be a dictionary"}

        normalized = copy.deepcopy(raw_input)
        logger.info(f"Normalizing input with keys: {list(normalized.keys())}")

        # Fix checkpoints details
        if "checkpoints" in normalized and isinstance(normalized["checkpoints"], list):
            logger.info(f"Normalizing {len(normalized['checkpoints'])} checkpoints")
            for i, checkpoint in enumerate(normalized["checkpoints"]):
                if isinstance(checkpoint, dict):
                    if "details" in checkpoint:
                        original_details = checkpoint["details"]
                        if checkpoint["details"] == "" or checkpoint["details"] is None:
                            checkpoint["details"] = {}
                            logger.debug(f"Checkpoint {i}: Converted empty string/None details to {{}}")
                        elif isinstance(checkpoint["details"], str):
                            # Try to parse as JSON, or wrap in dict
                            try:
                                checkpoint["details"] = json.loads(checkpoint["details"])
                                logger.debug(f"Checkpoint {i}: Parsed details string as JSON")
                            except json.JSONDecodeError:
                                checkpoint["details"] = {"message": checkpoint["details"]}
                                logger.debug(f"Checkpoint {i}: Wrapped details string in dict")
                        elif not isinstance(checkpoint["details"], dict):
                            # If it's some other type, try to convert
                            checkpoint["details"] = {"value": str(checkpoint["details"])}
                            logger.debug(f"Checkpoint {i}: Converted details to dict with value")
                else:
                    logger.warning(f"Checkpoint {i} is not a dict: {type(checkpoint)}")

        # Fix observational_notes
        if "observational_notes" in normalized:
            original_notes = normalized["observational_notes"]
            if isinstance(normalized["observational_notes"], list):
                normalized["observational_notes"] = "; ".join(
                    str(item) for item in normalized["observational_notes"]
                )
                logger.info(f"Converted observational_notes from list to string: {normalized['observational_notes'][:100]}")
            elif normalized["observational_notes"] == "":
                normalized["observational_notes"] = None
                logger.debug("Set empty observational_notes to None")
            elif not isinstance(normalized["observational_notes"], (str, type(None))):
                # Convert other types to string
                normalized["observational_notes"] = str(normalized["observational_notes"])
                logger.debug(f"Converted observational_notes to string: {type(original_notes)}")

        logger.info("Manual normalization completed successfully")
        return normalized

    async def parse_request(
        self, state: TransactionRCAAgentState
    ) -> Dict[str, Any]:
        """Parse transaction context from user message or input. Also detects ticket creation requests."""
        last_msg = state["messages"][-1].content if state["messages"] else ""
        logger.info(f"Parsing request from: {last_msg[:100]}...")

        # First, try to parse as JSON to check for structured requests
        parsed_json = None
        if isinstance(last_msg, str):
            try:
                parsed_json = json.loads(last_msg)
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(last_msg, dict):
            parsed_json = last_msg

        # Check if this is a structured ticket creation request (has "action" field)
        if isinstance(parsed_json, dict) and parsed_json.get("action") == "create_ticket":
            logger.info("Detected structured ticket creation request with action field")
            rca_analysis = parsed_json.get("rca_analysis")
            transaction_context_data = parsed_json.get("transaction_context")
            
            # Try to parse transaction context if provided (but don't fail if it's missing or invalid)
            transaction_context = None
            if transaction_context_data:
                try:
                    # Try to validate transaction context, but make it optional
                    if isinstance(transaction_context_data, dict):
                        transaction_context = TransactionContext(**transaction_context_data)
                        logger.info(f"Parsed transaction context for ticket: {transaction_context.transaction_id}")
                    else:
                        logger.warning(f"transaction_context is not a dict: {type(transaction_context_data)}")
                except Exception as e:
                    logger.warning(f"Could not parse transaction_context for ticket creation: {e}. Proceeding without it.")
                    # Continue without transaction context - ticket creation can work with just RCA analysis
            
            if rca_analysis:
                result = {"action": "create_ticket", "rca_analysis": rca_analysis}
                if transaction_context:
                    result["transaction_context"] = transaction_context
                logger.info("Found RCA analysis for ticket creation")
                return result
            else:
                # Try to get RCA analysis from state as fallback
                rca_analysis = None
                if hasattr(state, "rca_analysis"):
                    rca_analysis = state.rca_analysis
                elif isinstance(state, dict):
                    rca_analysis = state.get("rca_analysis")
                
                if rca_analysis:
                    result = {"action": "create_ticket", "rca_analysis": rca_analysis}
                    if transaction_context:
                        result["transaction_context"] = transaction_context
                    return result
                else:
                    logger.warning("No RCA analysis found in request or state for ticket creation")
                    return {
                        "error": "RCA analysis not found. Please perform RCA analysis first.",
                        "action": "create_ticket",
                        "messages": [
                            AIMessage(content="Cannot create ticket: RCA analysis not found. Please perform RCA analysis first.")
                        ]
                    }

        # Check if this is a natural language ticket creation request
        last_msg_lower = last_msg.lower() if isinstance(last_msg, str) else ""
        is_ticket_request = any(phrase in last_msg_lower for phrase in [
            "create ticket", "create a ticket", "yes", "yes create", "yes please",
            "create ticket for", "ticket for this", "ticket for the issue"
        ])
        
        # If it's a natural language ticket request, try to extract RCA analysis from state
        if is_ticket_request:
            logger.info("Detected natural language ticket creation request")
            rca_analysis = None
            
            # First check state
            if hasattr(state, "rca_analysis"):
                rca_analysis = state.rca_analysis
            elif isinstance(state, dict):
                rca_analysis = state.get("rca_analysis")
            
            if rca_analysis:
                logger.info("Found RCA analysis in state for ticket creation")
                return {"action": "create_ticket", "rca_analysis": rca_analysis}
            else:
                # If no RCA analysis found, return error
                return {
                    "error": "RCA analysis not found. Please perform RCA analysis first.",
                    "action": "create_ticket",
                    "messages": [
                        AIMessage(content="Cannot create ticket: RCA analysis not found. Please perform RCA analysis first.")
                    ]
                }

        # If not a ticket request, try to parse as TransactionContext
        try:
            # Try to parse as JSON first (if coming from API)
            context_data = None
            try:
                if parsed_json is not None:
                    context_data = parsed_json
                elif isinstance(last_msg, str):
                    # Already tried JSON parsing above, so this is likely not JSON
                    context_data = None
                elif isinstance(last_msg, dict):
                    context_data = last_msg
                else:
                    context_data = last_msg

                # If we have context_data, try to validate as TransactionContext
                if context_data is not None:
                    # Try to validate directly first
                    try:
                        transaction_context = TransactionContext(**context_data)
                        logger.info(f"Parsed transaction context: {transaction_context.transaction_id}")
                        return {"transaction_context": transaction_context}
                    except Exception as validation_error:
                        logger.warning(f"Direct validation failed: {validation_error}. Attempting LLM normalization...")
                        # Use LLM to normalize the input
                        normalized_data = await self.normalize_input_with_llm(context_data)
                        
                        if "error" in normalized_data:
                            return {
                                "error": normalized_data["error"],
                                "messages": [
                                    AIMessage(content=f"Error normalizing input: {normalized_data['error']}")
                                ],
                            }
                        
                        # Try validation again with normalized data
                        try:
                            transaction_context = TransactionContext(**normalized_data)
                            logger.info(f"Parsed transaction context after normalization: {transaction_context.transaction_id}")
                            return {"transaction_context": transaction_context}
                        except Exception as e:
                            logger.error(f"Validation failed even after normalization: {e}")
                            # Don't fail completely - try to extract what we can
                            return {
                                "error": f"Failed to parse transaction context after normalization: {str(e)}",
                                "messages": [
                                    AIMessage(content=f"Error parsing input: {str(e)}")
                                ],
                            }

            except (json.JSONDecodeError, TypeError) as e:
                # If not JSON, try to extract from natural language using LLM
                if isinstance(last_msg, str):
                    logger.info("Input is not JSON, attempting to extract from natural language...")
                    try:
                        extracted_data = await self._extract_from_natural_language(last_msg)
                        if "error" in extracted_data:
                            return {
                                "error": extracted_data["error"],
                                "messages": [
                                    AIMessage(content=extracted_data["error"])
                                ],
                            }
                        
                        # Normalize and validate
                        normalized_data = await self.normalize_input_with_llm(extracted_data)
                        transaction_context = TransactionContext(**normalized_data)
                        logger.info(f"Parsed transaction context from natural language: {transaction_context.transaction_id}")
                        return {"transaction_context": transaction_context}
                    except Exception as extract_error:
                        logger.error(f"Failed to extract from natural language: {extract_error}")
                        return {
                            "error": "Transaction context must be provided as JSON or natural language describing the transaction.",
                            "messages": [
                                AIMessage(
                                    content="I need transaction context (JSON or natural language) to perform RCA analysis."
                                )
                            ],
                        }
                else:
                    raise e
        except Exception as e:
            logger.error(f"Parse error: {e}", exc_info=True)
            return {
                "error": f"Failed to parse transaction context: {str(e)}",
                "messages": [
                    AIMessage(content=f"Error parsing input: {str(e)}")
                ],
            }

    async def _extract_from_natural_language(self, text: str) -> Dict[str, Any]:
        """Extract transaction context from natural language using LLM."""
        extraction_prompt = """Extract transaction context information from the following text and return it as JSON in the TransactionContext format.

Expected format:
{
  "transaction_id": "string",
  "checkpoints": [
    {
      "checkpoint_name": "string (ingestion, authorization, routing, ledger, settlement_file_generated, bank_acknowledged, credited)",
      "status": "string (SUCCESS, FAILED, PENDING, NOT_STARTED, NO_INTERACTION)",
      "timestamp": "ISO timestamp string or null",
      "details": {}  // dictionary, not string
    }
  ],
  "merchant_config": {},
  "merchant_data": {},
  "external_signals": {},
  "risk_indicators": {},
  "observational_notes": "string or null"
}

Text:
{text}

Return ONLY valid JSON:"""

        try:
            extraction_llm = LLMFactory.get_llm(
                "TRANSACTION_RCA_AGENT_LLM", temperature=0, max_tokens=2000
            )
            
            messages = [
                SystemMessage(content="You are a data extraction assistant. Extract transaction context and return only valid JSON."),
                HumanMessage(content=extraction_prompt.format(text=text))
            ]
            
            response = await extraction_llm.ainvoke(messages)
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            extracted_data = json.loads(content)
            logger.info("Successfully extracted transaction context from natural language")
            return extracted_data

        except Exception as e:
            logger.error(f"Natural language extraction error: {e}")
            return {"error": f"Failed to extract transaction context from text: {str(e)}"}

    async def analyze_rca(
        self, state: TransactionRCAAgentState
    ) -> Dict[str, Any]:
        """Perform RCA analysis using LLM reasoning."""
        context = state.get("transaction_context")
        if not context:
            return {
                "error": "No transaction context available for analysis",
                "messages": [
                    AIMessage(content="Missing transaction context for RCA analysis.")
                ],
            }

        logger.info(f"Analyzing RCA for transaction: {context.transaction_id}")

        try:
            # Build input context for LLM
            input_data = {
                "transaction_id": context.transaction_id,
                "checkpoints": [
                    {
                        "checkpoint_name": cp.checkpoint_name,
                        "status": cp.status,
                        "timestamp": cp.timestamp,
                        "details": cp.details,
                    }
                    for cp in context.checkpoints
                ],
                "merchant_config": context.merchant_config,
                "merchant_data": context.merchant_data,
                "external_signals": context.external_signals,
                "risk_indicators": context.risk_indicators,
                "observational_notes": context.observational_notes,
            }

            # Create messages for LLM
            messages = [
                SystemMessage(content=RCA_SYSTEM_PROMPT),
                HumanMessage(
                    content=f"Analyze this transaction:\n\n{json.dumps(input_data, indent=2)}"
                ),
            ]

            # Invoke LLM
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            # Parse JSON from response (handle markdown code blocks if present)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            # Parse JSON
            try:
                result_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {content[:500]}")
                return {
                    "error": f"LLM returned invalid JSON: {str(e)}",
                    "messages": [
                        AIMessage(
                            content="Error: Failed to parse RCA analysis result."
                        )
                    ],
                }

            # Validate and create RCA analysis
            rca_data = result_data.get("rca_analysis", {})
            intervention_data = result_data.get("human_intervention", {})

            # Validate RCA category
            rca_category = rca_data.get("rca_category", "")
            if rca_category not in RCA_CATEGORIES:
                logger.warning(
                    f"Invalid RCA category '{rca_category}', defaulting to 'Unknown / System Defect'"
                )
                rca_category = "Unknown / System Defect"

            # Validate checkpoint
            checkpoint = rca_data.get("last_successful_checkpoint", "")
            if checkpoint not in ALLOWED_CHECKPOINTS:
                logger.warning(
                    f"Invalid checkpoint '{checkpoint}', using first checkpoint"
                )
                checkpoint = ALLOWED_CHECKPOINTS[0] if ALLOWED_CHECKPOINTS else "ingestion"

            # Create models
            rca_analysis = RCAAnalysis(
                rca_category=rca_category,
                confidence=float(rca_data.get("confidence", 0.5)),
                last_successful_checkpoint=checkpoint,
                transaction_narrative=rca_data.get("transaction_narrative", ""),
                key_anomalies=rca_data.get("key_anomalies", []),
                contradictions_observed=rca_data.get("contradictions_observed", []),
                evidence=rca_data.get("evidence", []),
                alternative_causes_considered=rca_data.get(
                    "alternative_causes_considered", []
                ),
                final_reasoning=rca_data.get("final_reasoning", ""),
            )

            # Force prompt to be empty - never show ticket creation prompts
            human_intervention = HumanIntervention(
                action_required=intervention_data.get("action_required", True),
                prompt="",  # Always empty - no prompts or questions
            )

            logger.info(
                f"RCA analysis complete: {rca_category} (confidence: {rca_analysis.confidence})"
            )

            # Return state updates - LangGraph will merge these into the state
            # Convert Pydantic models to dicts to ensure proper state merging
            # LangGraph should handle Pydantic models, but converting to dicts ensures compatibility
            result = {
                "rca_analysis": rca_analysis.model_dump() if hasattr(rca_analysis, "model_dump") else rca_analysis,
                "human_intervention": human_intervention.model_dump() if hasattr(human_intervention, "model_dump") else human_intervention,
            }
            logger.info(f"[analyze_rca] Returning state update with keys: {list(result.keys())}")
            logger.info(f"[analyze_rca] rca_analysis type: {type(result['rca_analysis'])}, human_intervention type: {type(result['human_intervention'])}")
            logger.info(f"[analyze_rca] rca_analysis keys: {list(result['rca_analysis'].keys()) if isinstance(result['rca_analysis'], dict) else 'N/A'}")
            return result

        except Exception as e:
            logger.error(f"RCA analysis error: {e}", exc_info=True)
            error_message = extract_llm_error_message(e)
            return {
                "error": str(e),
                "messages": [AIMessage(content=error_message)],
            }

    def _format_rca_response_human_readable(
        self, rca_analysis: RCAAnalysis, human_intervention: HumanIntervention
    ) -> str:
        """Format RCA analysis in a human-readable, well-structured format."""
        
        # Format confidence as percentage
        confidence_pct = f"{rca_analysis.confidence * 100:.0f}%"
        
        # Format narrative with better structure
        narrative = rca_analysis.transaction_narrative.strip()
        if not narrative.endswith('.'):
            narrative += '.'
        
        # Build the formatted response
        formatted = f"""## Root Cause Analysis Summary

{narrative}

---

### Analysis Details

**Category:** {rca_analysis.rca_category}
**Confidence:** {confidence_pct}
**Last Successful Step:** {rca_analysis.last_successful_checkpoint.replace('_', ' ').title()}

### Key Issues Identified

"""
        
        # Format key anomalies
        if rca_analysis.key_anomalies:
            for anomaly in rca_analysis.key_anomalies:
                formatted += f"• {anomaly}\n"
        else:
            formatted += "• No specific anomalies identified\n"
        
        formatted += "\n### Supporting Evidence\n\n"
        
        # Format evidence - clean up technical formatting for readability
        if rca_analysis.evidence:
            for i, evidence_item in enumerate(rca_analysis.evidence, 1):
                # Make evidence more readable by converting technical format to natural language
                evidence_text = evidence_item
                # Replace common technical patterns with more readable text
                evidence_text = evidence_text.replace("checkpoint_name:", "Checkpoint:")
                evidence_text = evidence_text.replace("status:", "Status:")
                evidence_text = evidence_text.replace("observational_notes:", "Note:")
                formatted += f"{i}. {evidence_text}\n"
        else:
            formatted += "No explicit evidence recorded.\n"
        
        # Format alternative causes if any
        if rca_analysis.alternative_causes_considered:
            formatted += "\n### Other Causes Considered\n\n"
            for cause in rca_analysis.alternative_causes_considered:
                formatted += f"• {cause}\n"
        
        # Format contradictions if any
        if rca_analysis.contradictions_observed:
            formatted += "\n### Contradictions or Conflicts\n\n"
            for contradiction in rca_analysis.contradictions_observed:
                formatted += f"⚠️ {contradiction}\n"
        else:
            formatted += "\n### Contradictions or Conflicts\n\n"
            formatted += "None observed.\n"
        
        # Format final reasoning - clean up any questions or "Next Steps" sections
        final_reasoning = rca_analysis.final_reasoning.strip()
        # Remove "Next Steps:" sections and anything after them
        if "Next Steps:" in final_reasoning or "next steps:" in final_reasoning.lower():
            lines = final_reasoning.split('\n')
            cleaned_lines = []
            for line in lines:
                if "Next Steps:" in line or "next steps:" in line.lower():
                    break
                cleaned_lines.append(line)
            final_reasoning = '\n'.join(cleaned_lines).strip()
        # Remove any questions (lines ending with "?")
        lines = final_reasoning.split('\n')
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            # Skip lines that are questions or prompts
            if (line_stripped.endswith('?') and 
                ('would you like' in line_stripped.lower() or 
                 'do you want' in line_stripped.lower() or
                 'create a ticket' in line_stripped.lower())):
                continue
            cleaned_lines.append(line)
        final_reasoning = '\n'.join(cleaned_lines).strip()
        
        formatted += "\n### Analysis Conclusion\n\n"
        formatted += f"{final_reasoning}\n"
        
        # Add human intervention prompt (only if prompt is provided)
        if human_intervention.action_required and human_intervention.prompt and human_intervention.prompt.strip():
            formatted += f"\n---\n\n**{human_intervention.prompt}**\n"
        
        return formatted

    async def generate_response(
        self, state: TransactionRCAAgentState
    ) -> Dict[str, Any]:
        """Generate final response with RCA analysis and human intervention prompt."""
        # Try multiple ways to access state fields
        # MessagesState supports attribute access, but let's try all methods
        rca_analysis = None
        human_intervention = None
        
        # Method 1: Direct attribute access
        try:
            rca_analysis = state.rca_analysis
            human_intervention = state.human_intervention
        except AttributeError:
            pass
        
        # Method 2: getattr
        if rca_analysis is None:
            rca_analysis = getattr(state, "rca_analysis", None)
        if human_intervention is None:
            human_intervention = getattr(state, "human_intervention", None)
        
        # Method 3: Dict access
        if rca_analysis is None and hasattr(state, "get"):
            rca_analysis = state.get("rca_analysis", None)
        if human_intervention is None and hasattr(state, "get"):
            human_intervention = state.get("human_intervention", None)
        
        # Method 4: Check if state is a dict
        if rca_analysis is None and isinstance(state, dict):
            rca_analysis = state.get("rca_analysis", None)
        if human_intervention is None and isinstance(state, dict):
            human_intervention = state.get("human_intervention", None)
        
        logger.info(f"[generate_response] rca_analysis: {rca_analysis is not None}, human_intervention: {human_intervention is not None}")
        logger.info(f"[generate_response] State type: {type(state)}")
        logger.info(f"[generate_response] State dir: {[x for x in dir(state) if not x.startswith('_')][:10]}")
        
        # If stored as dicts, reconstruct Pydantic models
        if isinstance(rca_analysis, dict):
            from domain.models import RCAAnalysis
            try:
                rca_analysis = RCAAnalysis(**rca_analysis)
                logger.info("[generate_response] Reconstructed RCAAnalysis from dict")
            except Exception as e:
                logger.error(f"[generate_response] Failed to reconstruct RCAAnalysis: {e}")
        
        if isinstance(human_intervention, dict):
            from domain.models import HumanIntervention
            try:
                human_intervention = HumanIntervention(**human_intervention)
                logger.info("[generate_response] Reconstructed HumanIntervention from dict")
            except Exception as e:
                logger.error(f"[generate_response] Failed to reconstruct HumanIntervention: {e}")
        
        if not rca_analysis or not human_intervention:
            logger.warning(f"[generate_response] Missing data. rca_analysis={rca_analysis}, human_intervention={human_intervention}")
            # Try to inspect state more deeply
            try:
                if hasattr(state, "__dict__"):
                    logger.warning(f"[generate_response] State __dict__ keys: {list(state.__dict__.keys())}")
            except:
                pass
            return {
                "error": "RCA analysis not available",
                "messages": [
                    AIMessage(content="RCA analysis could not be completed.")
                ],
            }

        # Format response in human-readable format
        formatted_response = self._format_rca_response_human_readable(
            rca_analysis, human_intervention
        )
        
        # Also include JSON for programmatic access (but make it secondary)
        response_data = {
            "rca_analysis": {
                "rca_category": rca_analysis.rca_category,
                "confidence": rca_analysis.confidence,
                "last_successful_checkpoint": rca_analysis.last_successful_checkpoint,
                "transaction_narrative": rca_analysis.transaction_narrative,
                "key_anomalies": rca_analysis.key_anomalies,
                "contradictions_observed": rca_analysis.contradictions_observed,
                "evidence": rca_analysis.evidence,
                "alternative_causes_considered": rca_analysis.alternative_causes_considered,
                "final_reasoning": rca_analysis.final_reasoning,
            },
            "human_intervention": {
                "action_required": human_intervention.action_required,
                "prompt": human_intervention.prompt,
            },
        }

        return {
            "messages": [
                AIMessage(content=formatted_response)
            ],
        }

    async def create_ticket(
        self, state: TransactionRCAAgentState
    ) -> Dict[str, Any]:
        """Create a ticket using the RCA analysis output."""
        logger.info("Creating ticket from RCA analysis")
        
        # Get RCA analysis from state
        rca_analysis = None
        if hasattr(state, "rca_analysis"):
            rca_analysis = state.rca_analysis
        elif isinstance(state, dict):
            rca_analysis = state.get("rca_analysis")
        
        # If stored as dict, reconstruct Pydantic model
        if isinstance(rca_analysis, dict):
            from domain.models import RCAAnalysis
            try:
                rca_analysis = RCAAnalysis(**rca_analysis)
            except Exception as e:
                logger.error(f"Failed to reconstruct RCAAnalysis: {e}")
                return {
                    "error": "RCA analysis not available for ticket creation",
                    "messages": [AIMessage(content="Cannot create ticket: RCA analysis not found.")]
                }
        
        if not rca_analysis:
            return {
                "error": "RCA analysis not available for ticket creation",
                "messages": [AIMessage(content="Cannot create ticket: RCA analysis not found. Please perform RCA analysis first.")]
            }
        
        # Get transaction context for ticket details
        transaction_context = None
        if hasattr(state, "transaction_context"):
            transaction_context = state.transaction_context
        elif isinstance(state, dict):
            transaction_context = state.get("transaction_context")
        
        transaction_id = "UNKNOWN"
        if transaction_context:
            transaction_id = transaction_context.transaction_id if hasattr(transaction_context, "transaction_id") else str(transaction_context.get("transaction_id", "UNKNOWN"))
        
        # Generate ticket ID for display
        ticket_id = f"TICKET-{transaction_id}-{int(__import__('time').time())}"
        
        # Format ticket content for display in chat
        ticket_content = f"""## Ticket: {ticket_id}

**Transaction ID:** {transaction_id}

**RCA Category:** {rca_analysis.rca_category}
**Confidence:** {rca_analysis.confidence * 100:.0f}%
**Last Successful Checkpoint:** {rca_analysis.last_successful_checkpoint.replace('_', ' ').title()}

**Transaction Narrative:**
{rca_analysis.transaction_narrative}

**Key Anomalies:**
{chr(10).join(f"- {anomaly}" for anomaly in rca_analysis.key_anomalies) if rca_analysis.key_anomalies else "- None identified"}

**Evidence:**
{chr(10).join(f"- {evidence}" for evidence in rca_analysis.evidence) if rca_analysis.evidence else "- No explicit evidence recorded"}

**Alternative Causes Considered:**
{chr(10).join(f"- {cause}" for cause in rca_analysis.alternative_causes_considered) if rca_analysis.alternative_causes_considered else "- None"}

**Final Reasoning:**
{rca_analysis.final_reasoning}
"""
        
        logger.info(f"Displaying ticket: {ticket_id}")
        
        return {
            "messages": [
                AIMessage(content=ticket_content)
            ],
        }
