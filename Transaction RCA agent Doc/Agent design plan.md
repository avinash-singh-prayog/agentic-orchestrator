Human-in-the-Loop RCA Reasoning Agent

Phase 1 Specification (BRD 7.3 Aligned)

⸻

1. Objective

Build a stateless AI RCA agent that analyzes a single unprocessed transaction and performs Root Cause Analysis (RCA) strictly as defined in BRD section 7.3.

The agent:
	•	Performs reasoning comparable to a senior fintech operations analyst
	•	Uses judgement-based reasoning, not deterministic rules
	•	Classifies the issue into exactly ONE RCA category
	•	Produces evidence-backed, explainable analysis
	•	Stops for human confirmation before any ticket creation

🚫 The agent must never auto-create tickets

⸻

2. Model & Execution Constraints
	•	LLM Model: gemini-3-flash-preview
	•	Execution Mode: Stateless (single request → single response)
	•	Persistence: None
	•	Storage: None
	•	Memory: None
	•	Embeddings / vectors: Not allowed
	•	Cross-transaction reasoning: Not allowed

Decision Authority
	•	AI: RCA analysis & recommendation only
	•	Human: Final decision on ticket creation

Idempotency and duplicate ticket prevention are assumed to be handled downstream using transaction_id.

⸻

3. Phase-1 Scope

In Scope
	•	Single transaction RCA analysis
	•	Root cause classification (BRD 7.3)
	•	Explainable reasoning with explicit evidence
	•	Identification of last successful checkpoint
	•	Human-in-the-loop confirmation prompt

Out of Scope
	•	Auto ticket creation
	•	Self-healing actions
	•	Rule engines
	•	Model training or learning
	•	Multi-transaction correlation
	•	State, persistence, or memory

⸻

4. RCA Categories (BRD 7.3)

The agent must classify into exactly ONE category:
	•	Sync Issues
	•	Configuration Issues
	•	Routing Issues
	•	Dependency Failures
	•	Merchant Data Issues
	•	Compliance / Risk Holds
	•	Unknown / System Defect

Classification Principle
	•	Classification is judgement-based
	•	No category may be forced
	•	Unknown / System Defect is a valid and successful outcome when evidence quality is insufficient

⸻

5. Judgement Guardrails (Mandatory)

The agent must adhere to the following reasoning guardrails:
	•	Direct system signals override inferred absence
	•	Missing data must reduce confidence
	•	Contradictory signals must be explicitly surfaced
	•	If two or more RCA categories are equally plausible → classify as Unknown / System Defect
	•	The agent must never invent:
	•	Logs
	•	Timestamps
	•	Status transitions
	•	External failures

⸻

6. Analyst Reasoning Compass (Non-Binding Heuristics)

These heuristics guide judgement but must not force classification:
	•	Prefer Configuration Issues when required static attributes (TID, MDR, routing config) are missing or invalid
	•	Prefer Merchant Data Issues when merchant account, IFSC, or bank details are invalid or changed
	•	Prefer Dependency Failures only when explicit external signals exist (bank downtime, file rejection)
	•	Prefer Sync Issues when transaction data exists across systems but is inconsistent or partially written
	•	Prefer Routing Issues when transaction is routed incorrectly despite valid configuration
	•	Prefer Unknown / System Defect when evidence is weak, indirect, or contradictory

⸻

7. Transaction Journey & Checkpoints

Allowed System Checkpoints (Ordered)

The agent must reason only using these checkpoints:
	1.	ingestion
	2.	authorization
	3.	routing
	4.	ledger
	5.	settlement_file_generated
	6.	bank_acknowledged
	7.	credited

Last Successful Checkpoint
	•	Defined as the furthest checkpoint with explicit success confirmation
	•	Pending or inferred states do not count as successful

⸻

8. Input Expectations

Input Format

The agent receives a single transaction context JSON, which may include:
	•	Transaction identifiers
	•	Status flags per system checkpoint
	•	Merchant configuration data (TID, MDR, routing)
	•	Merchant master data (account number, IFSC)
	•	External dependency signals (bank health, rejections)
	•	Risk / compliance indicators
	•	Observational notes (optional)

Input Rules
	•	Treat input as ground truth
	•	Do not assume missing data
	•	Absence of data is not proof of success or failure

⸻

9. Core Reasoning Behavior (Mandatory)

The agent must internally follow this reasoning sequence:
	1.	Reconstruct the full transaction journey end-to-end
	2.	Identify the last successful checkpoint
	3.	Identify abnormal, missing, or stalled steps
	4.	Consider multiple plausible RCA categories
	5.	Evaluate strength and quality of evidence
	6.	Identify contradictions or missing signals
	7.	Select the most plausible RCA category
	8.	Clearly justify the decision using explicit evidence

Evidence Quality Awareness

Evidence must be evaluated as:
	•	Direct: Explicit system signal
	•	Indirect: Inferred from sequence or absence
	•	Weak / Contradictory

Lower evidence quality must:
	•	Reduce confidence
	•	Increase likelihood of Unknown / System Defect

⸻

10. Confidence Scoring Guidelines

confidence must be a number between 0 and 1, representing subjective certainty.

Guidance (Non-Binding)
	•	Missing critical checkpoints → confidence ≤ 0.6
	•	Contradictory signals → confidence ≤ 0.5
	•	Only indirect evidence → confidence ≤ 0.5
	•	Clear direct signals with no contradiction → confidence ≥ 0.7

⸻

11. Output Contract (STRICT)

The agent must return ONLY valid JSON:

{
  "rca_analysis": {
    "rca_category": "<one allowed category>",
    "confidence": 0.0,

    "last_successful_checkpoint": "<checkpoint name>",

    "transaction_narrative": "<concise journey summary>",

    "key_anomalies": [
      "<abnormal or missing observations>"
    ],

    "contradictions_observed": [
      "<conflicting signals, if any>"
    ],

    "evidence": [
      "<explicit evidence taken directly from input>"
    ],

    "alternative_causes_considered": [
      "<other plausible categories evaluated>"
    ],

    "final_reasoning": "<why this RCA category fits best>"
  },

  "human_intervention": {
    "action_required": true,
    "prompt": "Based on this analysis, do you want to create a ticket for this issue?"
  }
}

🚫 No additional fields
🚫 No free text outside JSON

⸻

12. Phase-1 Design Principles
	•	Explainability over automation
	•	Judgement over rigid rules
	•	Safety over false certainty
	•	Human control over irreversible actions
	•	Unknown outcomes are acceptable and expected

⸻

13. Phase-1 Success Criteria

Phase-1 is considered successful if:
	•	RCA outputs are consistent and explainable
	•	Humans trust both confident and uncertain results
	•	No auto-actions occur
	•	Unknown / System Defect is used appropriately
	•	The agent becomes a decision aid, not a decision maker

⸻

Outcome

This Phase-1 agent establishes a trustworthy analytical foundation for:
	•	Phase-2 controlled self-healing
	•	Phase-3 predictive prevention and transparency