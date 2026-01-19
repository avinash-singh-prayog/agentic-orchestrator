"""
Directory Client using dirctl CLI via subprocess.

Implements capability-based discovery for AGNTCY IoA architecture.
Agents are discovered by their registered capabilities (skills),
not by hardcoded names.
"""
import os
import logging
import subprocess
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger("agent.directory")


class AgentNotFoundError(Exception):
    """Raised when no agent with required capability is found."""
    pass


class DirectoryClient:
    """Client for interacting with the Agency Directory Service via dirctl CLI."""
    
    def __init__(self):
        self.server_address = os.getenv("DIRECTORY_SERVICE_ADDR")
        self._use_tls = ":443" in self.server_address
        logger.info(f"Directory Client initialized with address: {self.server_address} (TLS: {self._use_tls})")
    
    def _get_base_cmd(self, command: str) -> list:
        """Get base dirctl command with server address and TLS if needed."""
        cmd = ["dirctl", command, "--server-addr", self.server_address]
        # TLS flags not needed for local directory service
        pass
        return cmd
    
    def _parse_description_tags(self, description: str) -> Dict[str, Any]:
        """
        Parse [CAPABILITY:...] and [TOPIC:...] tags from description.
        Used as fallback when modules block is empty.
        """
        import re
        capabilities = re.findall(r'\[CAPABILITY:(\w+)\]', description)
        topic_match = re.search(r'\[TOPIC:([^\]]+)\]', description)
        return {
            "capabilities": capabilities,
            "slim_topic": topic_match.group(1) if topic_match else None
        }
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get all registered agents with their capabilities.
        Used for dynamic discovery of available capabilities.
        
        Returns:
            List of dicts with agent name, description, and capabilities.
        """
        cids = self._search_all()
        agents = []
        for cid in cids:
            record = self._pull_record(cid)
            if record:
                routing = self._get_routing_module(record)
                description = record.get("description", "")
                
                # Use modules if available, otherwise parse from description tags
                if routing and routing.get("capabilities"):
                    capabilities = routing.get("capabilities", [])
                    slim_topic = routing.get("slim_topic")
                else:
                    parsed = self._parse_description_tags(description)
                    capabilities = parsed["capabilities"]
                    slim_topic = parsed["slim_topic"]
                
                agents.append({
                    "name": record.get("name", "Unknown"),
                    "description": description[:150],
                    "capabilities": capabilities,
                    "slim_topic": slim_topic
                })
        return agents

    def register_agent(self, record_path: str = "agent_record.json") -> Optional[str]:
        """
        Register agent using the record at record_path.
        Returns the CID if successful.
        """
        try:
            if not os.path.exists(record_path):
                logger.error(f"Agent record file not found at {record_path}")
                return None

            with open(record_path, "r") as f:
                record_data = json.load(f)

            logger.info(f"Registering agent: {record_data.get('name', 'Unknown')}")
            
            cmd = self._get_base_cmd("push")
            cmd.extend(["--stdin", "--output", "raw"])
            
            result = subprocess.run(
                cmd,
                input=json.dumps(record_data),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"dirctl push failed: {result.stderr}")
                return None
            
            cid = result.stdout.strip()
            logger.info(f"Successfully registered agent. CID: {cid}")
            return cid

        except FileNotFoundError:
            logger.warning("dirctl not found in PATH. Skipping directory registration.")
            return None
        except subprocess.TimeoutExpired:
            logger.error("dirctl push timed out")
            return None
        except Exception as e:
            logger.error(f"Failed to register agent: {e}", exc_info=True)
            return None

    def find_agent_by_capability(self, capability: str) -> Optional[Dict[str, Any]]:
        """
        Find an agent that has the specified capability.
        
        Searches all registered agents and returns the first one that
        lists the capability in extension_data.capabilities.
        
        Args:
            capability: The capability to search for (e.g., "rate_fetching")
            
        Returns:
            Agent record dict with extension_data containing routing info,
            or None if not found.
        """
        try:
            # Search for all agents (broad search)
            cids = self._search_all()
            if not cids:
                logger.warning(f"No agents found in Directory")
                return None
            
            # Check each agent for the capability (stored in modules)
            for cid in cids:
                record = self._pull_record(cid)
                if record:
                    # Look for routing module with capabilities
                    routing_module = self._get_routing_module(record)
                    if routing_module:
                        capabilities = routing_module.get("capabilities", [])
                        if capability in capabilities:
                            logger.info(f"Found agent '{record.get('name')}' with capability '{capability}'")
                            return record
            
            logger.warning(f"No agent found with capability: {capability}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find agent by capability '{capability}': {e}")
            return None

    def get_routing_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get routing info (topic, protocol, port) for an agent by name.
        
        Returns:
            Dict with routing info or None if not found:
            {"protocol": "SLIM", "slim_topic": "logistics.svc.v1", "port": 9003}
        """
        record = self.find_agent_by_name(agent_name)
        if not record:
            return None
        
        routing = self._get_routing_module(record)
        
        if routing:
            logger.info(f"Found routing for '{agent_name}': topic={routing.get('slim_topic')}")
            return routing
        
        logger.warning(f"No routing info found for agent: {agent_name}")
        return None

    def _get_routing_module(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract routing data from the modules array.
        
        Looks for a module with name="routing" or type="routing" and returns its data.
        """
        modules = record.get("modules", [])
        for module in modules:
            if module.get("name") == "routing" or module.get("type") == "routing":
                return module.get("data", {})
        return None

    def find_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Search for an agent by name and return the full agent record.
        """
        try:
            cid = self._search_agent(name)
            if not cid:
                logger.warning(f"Agent '{name}' not found in Directory")
                return None
            
            record = self._pull_record(cid)
            if record:
                logger.info(f"Retrieved agent record for '{name}'")
                return record
            return None
            
        except Exception as e:
            logger.error(f"Failed to find agent '{name}': {e}")
            return None

    def _search_all(self) -> List[str]:
        """Search for all agent CIDs in the directory."""
        try:
            cmd = self._get_base_cmd("search")
            cmd.extend(["", "--output", "raw"])  # Empty query returns all
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"dirctl search failed: {result.stderr}")
                return []
            
            output = result.stdout.strip()
            if not output or output == "No record CIDs found":
                return []
            
            # Parse CIDs from output
            # Format 1: "Record CIDs found: [cid1 cid2 ...]"
            # Format 2: "[cid1 cid2 ...]"
            
            clean_output = output.strip()
            if "Record CIDs found:" in clean_output:
                clean_output = clean_output.split("Record CIDs found:")[1].strip()
            
            if clean_output.startswith("[") and clean_output.endswith("]"):
                cid_content = clean_output[1:-1].strip()
                if cid_content:
                    return cid_content.split()
            
            return []

        except FileNotFoundError:
            logger.warning("dirctl not found in PATH")
            return []
        except Exception as e:
            logger.error(f"Search all failed: {e}")
            return []

    def _search_agent(self, name: str) -> Optional[str]:
        """Search for agent CID by name."""
        try:
            cmd = self._get_base_cmd("search")
            cmd.extend([name, "--output", "raw"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"dirctl search failed: {result.stderr}")
                return None
            
            output = result.stdout.strip()
            
            # Parse CIDs from output
            # Format 1: "Record CIDs found: [cid1 cid2 ...]"
            # Format 2: "[cid1 cid2 ...]"
            
            clean_output = output.strip()
            if "Record CIDs found:" in clean_output:
                clean_output = clean_output.split("Record CIDs found:")[1].strip()
            
            if clean_output.startswith("[") and clean_output.endswith("]"):
                cid_content = clean_output[1:-1].strip()
                if cid_content:
                    cids = cid_content.split()
                    return cids[0] if cids else None
            
            # Fallback for single CID/other formats
            if clean_output and clean_output != "No record CIDs found":
                # If it looks like a single CID (alphanumeric, no spaces)
                if " " not in clean_output and "[" not in clean_output:
                     return clean_output
                
            return None
            
            return None

        except FileNotFoundError:
            logger.warning("dirctl not found in PATH")
            return None
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    def _pull_record(self, cid: str) -> Optional[Dict[str, Any]]:
        """Pull full agent record by CID."""
        try:
            cmd = self._get_base_cmd("pull")
            cmd.extend([cid, "--output", "json"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"dirctl pull failed: {result.stderr}")
                return None
            
            return json.loads(result.stdout)

        except FileNotFoundError:
            logger.warning("dirctl not found in PATH")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse agent record: {e}")
            return None
        except Exception as e:
            logger.error(f"Pull failed: {e}")
            return None
