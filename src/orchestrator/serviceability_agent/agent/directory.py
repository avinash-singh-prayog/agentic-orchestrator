"""
Directory Client using dirctl CLI via subprocess.

This implementation avoids the protobuf version conflict by using the
dirctl CLI tool instead of the Python SDK.
"""
import os
import logging
import subprocess
import json
from typing import Optional

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
            
            # Use dirctl push via subprocess
            # The dirctl binary should be available in the container
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

    def find_agent_by_name(self, name: str) -> Optional[str]:
        """
        Searches for an agent by name using dirctl search.
        Returns the CID if found.
        """
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
                logger.info(f"Found agent '{name}' with CID: {cid}")
                return cid
            return None

        except FileNotFoundError:
            logger.warning("dirctl not found in PATH. Skipping directory search.")
            return None
        except Exception as e:
            logger.error(f"Failed to search for agent: {e}")
            return None
