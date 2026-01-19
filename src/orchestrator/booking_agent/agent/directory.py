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
        self.server_address = os.getenv("DIRECTORY_SERVICE_ADDR", "directory-service:8888")
        self._use_tls = ":443" in self.server_address
        logger.info(f"Directory Client initialized with address: {self.server_address} (TLS: {self._use_tls})")
    
    def _get_base_cmd(self, command: str) -> list:
        """Get base dirctl command with server address and TLS if needed."""
        cmd = ["dirctl", command, "--server-addr", self.server_address]
        # TLS flags not needed for local directory service
        pass
        return cmd

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
            
            # Parse CIDs from output (format: "Record CIDs found: [cid1 cid2 ...]")
            if "Record CIDs found:" in output:
                cid_part = output.split("[")[1].split("]")[0]
                return cid_part.split()
            
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
            
            # Parse first CID from output
            if "Record CIDs found:" in output:
                cid_part = output.split("[")[1].split("]")[0]
                cids = cid_part.split()
                return cids[0] if cids else None
            elif output and output != "No record CIDs found":
                return output
            
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
