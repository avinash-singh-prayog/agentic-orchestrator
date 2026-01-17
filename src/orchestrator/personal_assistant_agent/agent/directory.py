"""
Directory Client for Personal Assistant Agent.
"""
import os
import logging
import subprocess
import json
from pathlib import Path

logger = logging.getLogger("personal_assistant.directory")


class DirectoryClient:
    """Client for registering with the Agency Directory Service."""
    
    def __init__(self):
        self.server_address = os.getenv("DIRECTORY_SERVICE_ADDR", "directory-service:8888")
        self._use_tls = ":443" in self.server_address
    
    def register_agent(self, record_path: str = "agent_record.json") -> bool:
        """Register this agent with the Directory Service."""
        try:
            if not os.path.isabs(record_path):
                possible_paths = [
                    Path(record_path),
                    Path(__file__).parent.parent / record_path,
                    Path("/app") / record_path,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        record_path = str(path)
                        break
                else:
                    logger.error(f"Agent record not found")
                    return False
            
            with open(record_path, "r") as f:
                record_data = json.load(f)
            
            logger.info(f"Registering agent: {record_data.get('name', 'Unknown')}")
            
            cmd = [
                "dirctl", "push",
                "--server-addr", self.server_address,
            ]
            if self._use_tls:
                # Use TLS authentication mode for gRPC on port 443
                cmd.extend(["--auth-mode", "tls", "--tls-skip-verify"])
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
                return False
            
            logger.info(f"Successfully registered. CID: {result.stdout.strip()}")
            return True
            
        except FileNotFoundError:
            logger.warning("dirctl not found. Skipping registration.")
            return False
        except Exception as e:
            logger.error(f"Failed to register: {e}")
            return False
