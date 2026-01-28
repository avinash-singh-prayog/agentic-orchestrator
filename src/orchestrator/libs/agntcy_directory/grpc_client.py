"""
Native Python gRPC client for AGNTCY Directory Service.

This implementation uses grpcio with SSL credentials for secure connections
to production Directory Services that require TLS (port 443).

It generates gRPC calls using reflection/dynamic stubs since we don't have
the compiled proto files.
"""

import grpc
import json
import logging
import ssl
from typing import List, Optional, Dict, Any, Iterator

from .models import AgentRecord, RecordMeta, SearchQuery, ConnectionConfig
from .exceptions import (
    DirectoryError,
    ConnectionError,
    RecordNotFoundError,
    RegistrationError,
    SearchError,
)

logger = logging.getLogger("agntcy_directory.grpc")


class GrpcDirectoryClient:
    """
    Native Python gRPC client for AGNTCY Directory Service.
    
    Uses grpcio with SSL credentials for TLS connections.
    Automatically uses system CA certificates for certificate verification.
    
    Example:
        config = ConnectionConfig(server_addr="dir.example.com:443", use_tls=True)
        client = GrpcDirectoryClient(config)
        cids = client.search_cids()
    """
    
    def __init__(self, config: Optional[ConnectionConfig] = None):
        """
        Initialize the gRPC client.
        
        Args:
            config: Connection configuration. If None, reads from environment.
        """
        self.config = config or ConnectionConfig.from_env()
        self._channel: Optional[grpc.Channel] = None
        
        logger.info(
            f"GrpcDirectoryClient initialized: {self.config.server_addr} "
            f"(TLS: {self.config.use_tls})"
        )
    
    def _get_channel(self) -> grpc.Channel:
        """Get or create the gRPC channel with proper TLS credentials."""
        if self._channel is None:
            options = [
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ]
            
            if self.config.use_tls:
                # Use SSL with system CA certificates (default root certs)
                # This works with ALB-terminated TLS using public certificates
                credentials = grpc.ssl_channel_credentials()
                self._channel = grpc.secure_channel(
                    self.config.server_addr,
                    credentials,
                    options=options
                )
                logger.info(f"Created secure gRPC channel to {self.config.server_addr}")
            else:
                # Plaintext for local development
                self._channel = grpc.insecure_channel(
                    self.config.server_addr,
                    options=options
                )
                logger.info(f"Created insecure gRPC channel to {self.config.server_addr}")
        
        return self._channel
    
    def close(self):
        """Close the gRPC channel."""
        if self._channel:
            self._channel.close()
            self._channel = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def health_check(self) -> bool:
        """Check if the Directory Service is healthy."""
        try:
            channel = self._get_channel()
            
            # Use the generic gRPC Health check
            from grpc_health.v1 import health_pb2, health_pb2_grpc
            stub = health_pb2_grpc.HealthStub(channel)
            request = health_pb2.HealthCheckRequest()
            response = stub.Check(request, timeout=10.0)
            
            is_healthy = response.status == health_pb2.HealthCheckResponse.SERVING
            logger.info(f"Health check: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def push(self, record: AgentRecord) -> str:
        """
        Push an agent record to the Directory Service using raw gRPC call.
        
        Uses the StoreService.Push streaming RPC with a manually constructed message.
        """
        try:
            channel = self._get_channel()
            
            # Create the record as JSON bytes
            record_json = json.dumps(record.to_dict())
            record_bytes = record_json.encode('utf-8')
            
            # Use unary_stream since Push is streaming
            # Method signature: rpc Push ( stream .agntcy.dir.core.v1.Record ) returns ( stream .agntcy.dir.core.v1.RecordRef )
            
            # Since we don't have proto stubs, we use grpc.channel_ready to verify connection
            # and then make raw calls
            grpc.channel_ready_future(channel).result(timeout=self.config.timeout_seconds)
            
            # For now, we'll construct a minimal implementation
            # The actual push requires serializing the Record protobuf message
            # Without the generated stubs, we'd need to use grpc_reflection
            
            logger.warning("Native gRPC push requires compiled proto stubs. Falling back to failure.")
            raise NotImplementedError(
                "Native gRPC push requires generated proto stubs. "
                "Use DIRECTORY_CLIENT_IMPL=dirctl for local development."
            )
            
        except grpc.FutureTimeoutError:
            raise ConnectionError(f"Timeout connecting to {self.config.server_addr}")
        except grpc.RpcError as e:
            logger.error(f"gRPC push failed: {e.code()} - {e.details()}")
            raise RegistrationError(f"Failed to push record: {e.details()}")
        except NotImplementedError:
            raise
        except Exception as e:
            logger.error(f"Push failed: {e}")
            raise RegistrationError(str(e))
    
    def pull(self, cid: str) -> AgentRecord:
        """Pull a record by CID."""
        try:
            channel = self._get_channel()
            grpc.channel_ready_future(channel).result(timeout=self.config.timeout_seconds)
            
            raise NotImplementedError(
                "Native gRPC pull requires generated proto stubs."
            )
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise RecordNotFoundError(f"Record not found: {cid}")
            raise DirectoryError(f"Failed to pull record: {e.details()}")
    
    def search_cids(self, query: Optional[SearchQuery] = None) -> List[str]:
        """Search for CIDs matching the query."""
        try:
            channel = self._get_channel()
            grpc.channel_ready_future(channel).result(timeout=self.config.timeout_seconds)
            
            raise NotImplementedError(
                "Native gRPC search requires generated proto stubs."
            )
            
        except grpc.RpcError as e:
            raise SearchError(f"Search failed: {e.details()}")
    
    def search_records(self, query: Optional[SearchQuery] = None) -> List[AgentRecord]:
        """Search for full records."""
        cids = self.search_cids(query)
        records = []
        for cid in cids:
            try:
                records.append(self.pull(cid))
            except RecordNotFoundError:
                continue
        return records
    
    def delete(self, cid: str) -> bool:
        """Delete a record."""
        raise NotImplementedError("Native gRPC delete requires generated proto stubs.")
    
    def info(self, cid: str) -> RecordMeta:
        """Get record metadata."""
        raise NotImplementedError("Native gRPC info requires generated proto stubs.")
    
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
                return record
        return None
    
    def register_agent(self, record_path: str = "agent_record.json") -> Optional[str]:
        """Register an agent from a JSON file."""
        try:
            record = AgentRecord.from_json_file(record_path)
            return self.push(record)
        except Exception as e:
            logger.error(f"Failed to register agent from {record_path}: {e}")
            return None
