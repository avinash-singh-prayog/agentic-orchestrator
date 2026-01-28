"""
Data models for the AGNTCY Directory Client.

Uses Pydantic for validation and serialization.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Skill(BaseModel):
    """Agent skill/capability definition."""
    name: str
    id: Optional[int] = None


class Domain(BaseModel):
    """Agent domain classification."""
    name: str
    id: Optional[int] = None


class Locator(BaseModel):
    """Agent locator (source code, docker image, etc.)."""
    type: str
    url: str


class RoutingModule(BaseModel):
    """Routing module containing capabilities and SLIM topic."""
    name: str = "routing"
    type: str = "routing"
    data: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def capabilities(self) -> List[str]:
        return self.data.get("capabilities", [])
    
    @property
    def slim_topic(self) -> Optional[str]:
        return self.data.get("slim_topic")


class AgentRecord(BaseModel):
    """
    Full agent record structure matching OASF schema.
    
    This is the primary data structure for agent registration
    and discovery in the Directory Service.
    """
    name: str
    description: str
    version: str = "1.0.0"
    schema_version: str = "0.8.0"
    authors: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    skills: List[Skill] = Field(default_factory=list)
    domains: List[Domain] = Field(default_factory=list)
    locators: List[Locator] = Field(default_factory=list)
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    
    def get_routing_module(self) -> Optional[Dict[str, Any]]:
        """Extract routing module data if present."""
        for module in self.modules:
            if module.get("name") == "routing" or module.get("type") == "routing":
                return module.get("data", {})
        return None
    
    def get_capabilities(self) -> List[str]:
        """Get capabilities from routing module or description tags."""
        routing = self.get_routing_module()
        if routing and routing.get("capabilities"):
            return routing.get("capabilities", [])
        
        # Fallback: parse [CAPABILITY:...] tags from description
        import re
        return re.findall(r'\[CAPABILITY:(\w+)\]', self.description)
    
    def get_slim_topic(self) -> Optional[str]:
        """Get SLIM topic from routing module or description tags."""
        routing = self.get_routing_module()
        if routing and routing.get("slim_topic"):
            return routing.get("slim_topic")
        
        # Fallback: parse [TOPIC:...] tag from description
        import re
        match = re.search(r'\[TOPIC:([^\]]+)\]', self.description)
        return match.group(1) if match else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRecord":
        """Create from dictionary."""
        return cls.model_validate(data)
    
    @classmethod
    def from_json_file(cls, path: str) -> "AgentRecord":
        """Load from JSON file."""
        import json
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))


class RecordMeta(BaseModel):
    """Metadata about a record in the store."""
    cid: str
    size: Optional[int] = None
    created_at: Optional[str] = None
    media_type: Optional[str] = None


class SearchQuery(BaseModel):
    """
    Search query parameters for finding agents.
    
    Supports filtering by name, skills, domains, and other attributes.
    All fields are optional - empty query returns all records.
    """
    name: Optional[str] = None
    skill: Optional[List[str]] = None
    skill_id: Optional[List[str]] = None
    domain: Optional[List[str]] = None
    domain_id: Optional[List[str]] = None
    version: Optional[str] = None
    author: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ConnectionConfig(BaseModel):
    """
    Configuration for connecting to the Directory Service.
    
    Attributes:
        server_addr: Directory Server address (e.g., "localhost:8888" or "dir.example.com:443")
        use_tls: Whether to use TLS (auto-detected from port 443)
        tls_skip_verify: Skip TLS certificate verification (not recommended for production)
        timeout_seconds: Request timeout in seconds
    """
    server_addr: str = "localhost:8888"
    use_tls: bool = False
    tls_skip_verify: bool = False
    timeout_seconds: float = 30.0
    
    @classmethod
    def from_env(cls) -> "ConnectionConfig":
        """Create configuration from environment variables."""
        import os
        
        server_addr = os.getenv("DIRECTORY_SERVICE_ADDR", "localhost:8888")
        use_tls = ":443" in server_addr
        tls_skip_verify = os.getenv("DIRECTORY_TLS_SKIP_VERIFY", "false").lower() == "true"
        timeout = float(os.getenv("DIRECTORY_TIMEOUT", "30"))
        
        return cls(
            server_addr=server_addr,
            use_tls=use_tls,
            tls_skip_verify=tls_skip_verify,
            timeout_seconds=timeout
        )
    
    @property
    def host(self) -> str:
        """Extract host from server_addr."""
        return self.server_addr.split(":")[0]
    
    @property
    def port(self) -> int:
        """Extract port from server_addr."""
        parts = self.server_addr.split(":")
        return int(parts[1]) if len(parts) > 1 else 8888
