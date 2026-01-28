"""
Subprocess-based dirctl client for AGNTCY Directory Service.

This implementation wraps the dirctl CLI binary using subprocess calls.
It's useful for local development or when native gRPC stubs are not available.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import AgentRecord, RecordMeta, SearchQuery, ConnectionConfig
from .exceptions import (
    DirectoryError,
    ConnectionError,
    RecordNotFoundError,
    RegistrationError,
    SearchError,
)

logger = logging.getLogger("agntcy_directory.dirctl")


class DirctlDirectoryClient:
    """
    Directory client using dirctl CLI subprocess calls.
    
    This implementation wraps the dirctl binary and is suitable for:
    - Local development with directory-service container
    - Environments where native gRPC is not practical
    - Testing and debugging
    
    Example:
        client = DirctlDirectoryClient()
        cid = client.push(agent_record)
        record = client.pull(cid)
    """
    
    def __init__(self, config: Optional[ConnectionConfig] = None):
        """
        Initialize the dirctl client.
        
        Args:
            config: Connection configuration. If None, reads from environment.
        """
        self.config = config or ConnectionConfig.from_env()
        
        logger.info(
            f"DirctlDirectoryClient initialized: {self.config.server_addr} "
            f"(TLS: {self.config.use_tls})"
        )
    
    def _get_base_cmd(self, command: str) -> List[str]:
        """Build base dirctl command with connection flags."""
        cmd = ["dirctl", command, "--server-addr", self.config.server_addr]
        
        # Add TLS flags if needed (for production)
        # Note: dirctl requires explicit TLS config which may not work with ALB
        # This is why we have the GrpcDirectoryClient as an alternative
        if self.config.use_tls:
            # The dirctl CLI has limited TLS support
            # For now, we rely on plain gRPC which the grpc_client handles
            pass
        
        return cmd
    
    def _run_command(
        self,
        cmd: List[str],
        input_data: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> subprocess.CompletedProcess:
        """Run a dirctl command and return the result."""
        timeout = timeout or self.config.timeout_seconds
        
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except FileNotFoundError:
            raise ConnectionError("dirctl binary not found in PATH")
        except subprocess.TimeoutExpired:
            raise ConnectionError(f"Command timed out after {timeout}s")
    
    def health_check(self) -> bool:
        """Check if the Directory Service is reachable."""
        try:
            # Try a simple search to verify connectivity
            cmd = self._get_base_cmd("search")
            cmd.extend(["--limit", "1", "--output", "raw"])
            result = self._run_command(cmd, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def push(self, record: AgentRecord) -> str:
        """Push an agent record to the Directory Service."""
        try:
            logger.info(f"Pushing agent: {record.name}")
            
            cmd = self._get_base_cmd("push")
            cmd.extend(["--stdin", "--output", "raw"])
            
            record_json = json.dumps(record.to_dict())
            result = self._run_command(cmd, input_data=record_json)
            
            if result.returncode != 0:
                logger.error(f"dirctl push failed: {result.stderr}")
                raise RegistrationError(f"Failed to push: {result.stderr}")
            
            cid = result.stdout.strip()
            logger.info(f"Successfully pushed. CID: {cid}")
            return cid
            
        except RegistrationError:
            raise
        except Exception as e:
            logger.error(f"Push failed: {e}")
            raise RegistrationError(str(e))
    
    def pull(self, cid: str) -> AgentRecord:
        """Pull a record by CID."""
        try:
            cmd = self._get_base_cmd("pull")
            cmd.extend([cid, "--output", "json"])
            
            result = self._run_command(cmd)
            
            if result.returncode != 0:
                if "not found" in result.stderr.lower():
                    raise RecordNotFoundError(f"Record not found: {cid}")
                raise DirectoryError(f"Pull failed: {result.stderr}")
            
            data = json.loads(result.stdout)
            return AgentRecord.from_dict(data)
            
        except (RecordNotFoundError, DirectoryError):
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse record: {e}")
            raise DirectoryError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Pull failed: {e}")
            raise DirectoryError(str(e))
    
    def search_cids(self, query: Optional[SearchQuery] = None) -> List[str]:
        """Search for CIDs matching the query."""
        try:
            cmd = self._get_base_cmd("search")
            
            # Add query parameters
            if query:
                if query.name:
                    cmd.extend(["--name", query.name])
                if query.skill:
                    for skill in query.skill:
                        cmd.extend(["--skill", skill])
                if query.domain:
                    for domain in query.domain:
                        cmd.extend(["--domain", domain])
                if query.limit:
                    cmd.extend(["--limit", str(query.limit)])
            else:
                # Empty query - search all
                cmd.append("")
            
            cmd.extend(["--output", "raw"])
            
            result = self._run_command(cmd)
            
            if result.returncode != 0:
                logger.warning(f"Search failed: {result.stderr}")
                return []
            
            output = result.stdout.strip()
            if not output or output == "No record CIDs found":
                return []
            
            # Parse CIDs from output
            # Format: "[cid1 cid2 ...]" or "Record CIDs found: [cid1 cid2 ...]"
            return self._parse_cid_output(output)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise SearchError(str(e))
    
    def _parse_cid_output(self, output: str) -> List[str]:
        """Parse CIDs from dirctl search output."""
        clean = output.strip()
        
        if "Record CIDs found:" in clean:
            clean = clean.split("Record CIDs found:")[1].strip()
        
        if clean.startswith("[") and clean.endswith("]"):
            cid_content = clean[1:-1].strip()
            if cid_content:
                return cid_content.split()
        
        # Fallback for single CID or other formats
        if clean and " " not in clean and "[" not in clean:
            return [clean]
        
        return []
    
    def search_records(self, query: Optional[SearchQuery] = None) -> List[AgentRecord]:
        """Search for full records."""
        cids = self.search_cids(query)
        records = []
        for cid in cids:
            try:
                records.append(self.pull(cid))
            except RecordNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Failed to pull {cid}: {e}")
                continue
        return records
    
    def delete(self, cid: str) -> bool:
        """Delete a record."""
        try:
            cmd = self._get_base_cmd("delete")
            cmd.extend([cid, "--output", "raw"])
            
            result = self._run_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def info(self, cid: str) -> RecordMeta:
        """Get record metadata."""
        try:
            cmd = self._get_base_cmd("info")
            cmd.extend([cid, "--output", "json"])
            
            result = self._run_command(cmd)
            
            if result.returncode != 0:
                if "not found" in result.stderr.lower():
                    raise RecordNotFoundError(f"Record not found: {cid}")
                raise DirectoryError(f"Info failed: {result.stderr}")
            
            data = json.loads(result.stdout)
            return RecordMeta(
                cid=cid,
                size=data.get("size"),
                created_at=data.get("created_at"),
                media_type=data.get("media_type")
            )
            
        except (RecordNotFoundError, DirectoryError):
            raise
        except Exception as e:
            raise DirectoryError(str(e))
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """Get all registered agents with their capabilities."""
        records = self.search_records()
        agents = []
        
        for record in records:
            agents.append({
                "name": record.name,
                "description": record.description[:150],
                "capabilities": record.get_capabilities(),
                "slim_topic": record.get_slim_topic(),
            })
        
        return agents
    
    def find_agent_by_capability(self, capability: str) -> Optional[AgentRecord]:
        """Find an agent with the specified capability."""
        records = self.search_records()
        
        for record in records:
            if capability in record.get_capabilities():
                logger.info(f"Found agent '{record.name}' with capability '{capability}'")
                return record
        
        logger.warning(f"No agent found with capability: {capability}")
        return None
    
    def register_agent(self, record_path: str = "agent_record.json") -> Optional[str]:
        """Register an agent from a JSON file."""
        try:
            # Handle relative paths
            if not os.path.isabs(record_path):
                possible_paths = [
                    Path(record_path),
                    Path(__file__).parent.parent.parent / record_path,
                    Path("/app") / record_path,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        record_path = str(path)
                        break
                else:
                    logger.error(f"Agent record not found: {record_path}")
                    return None
            
            record = AgentRecord.from_json_file(record_path)
            logger.info(f"Registering agent: {record.name}")
            return self.push(record)
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return None
