"""
Directory Client using dirctl CLI via subprocess.

This implementation avoids the protobuf version conflict by using the
dirctl CLI tool instead of the Python SDK.
"""
import os
import logging
import subprocess
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DirectoryClient:
    """Client for interacting with the Agency Directory Service via dirctl CLI."""
    
    def __init__(self):
        # Default to directory-service:8888 as per docker-compose (gRPC port)
        self.server_address = os.getenv("DIRECTORY_SERVICE_ADDR", "directory-service:8888")
        logger.info(f"Directory Client initialized with address: {self.server_address}")

    def register_agent(self, record_path: str = "agent_record.json") -> Optional[str]:
        """
        Registers the agent using the record found at record_path.
        Uses dirctl CLI via subprocess to bypass protobuf version conflict.
        Returns the CID if successful.
        """
        try:
            if not os.path.exists(record_path):
                logger.error(f"Agent record file not found at {record_path}")
                return None

            with open(record_path, "r") as f:
                record_data = json.load(f)

            logger.info(f"Registering agent: {record_data.get('name', 'Unknown')}")
            
            cmd = [
                "dirctl", "push",
                "--server-addr", self.server_address,
                "--stdin",
                "--output", "raw"
            ]
            
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

    def find_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Searches for an agent by name and returns the full agent record.
        
        Returns dict with agent record including locators and modules, or None if not found.
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

    def get_agent_slim_topic(self, name: str) -> Optional[str]:
        """
        Convenience method to get the SLIM topic for an agent.
        Extracts the topic from the agent record's locators.
        
        Returns the topic string (e.g., 'booking-agent') or None if not found.
        """
        record = self.find_agent_by_name(name)
        if not record:
            return None
        
        locators = record.get("locators", [])
        for locator in locators:
            if locator.get("protocol") == "SLIM" or "slim://" in locator.get("url", ""):
                url = locator.get("url", "")
                if url.startswith("slim://"):
                    topic = url.replace("slim://", "").split(":")[0]
                    logger.info(f"Extracted SLIM topic '{topic}' for agent '{name}'")
                    return topic
        
        logger.warning(f"No SLIM endpoint found in locators for agent '{name}'")
        return None

    def _search_agent(self, name: str) -> Optional[str]:
        """Search for agent CID by name."""
        try:
            cmd = [
                "dirctl", "search",
                name,
                "--server-addr", self.server_address,
                "--output", "raw"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"dirctl search failed: {result.stderr}")
                return None
            
            cid = result.stdout.strip()
            if cid and cid != "No record CIDs found":
                return cid
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
            cmd = [
                "dirctl", "pull",
                cid,
                "--server-addr", self.server_address,
                "--output", "json"
            ]
            
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
