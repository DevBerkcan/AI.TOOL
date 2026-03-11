"""Base connector interface for all document sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawDocument:
    """A document fetched from an external source."""
    external_id: str
    title: str
    content: bytes
    mime_type: str
    source_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    last_modified: Optional[datetime] = None


@dataclass
class ConnectorStatus:
    is_connected: bool
    message: str = ""
    documents_available: int = 0


class BaseConnector(ABC):
    """Abstract base class for document connectors."""

    connector_type: str = "unknown"

    @abstractmethod
    async def connect(self, config: dict) -> bool:
        """Test connection with given config. Returns True if successful."""
        ...

    @abstractmethod
    async def sync(self, last_sync_at: Optional[datetime] = None) -> list[RawDocument]:
        """Fetch documents since last_sync_at (or all if None)."""
        ...

    @abstractmethod
    async def get_status(self) -> ConnectorStatus:
        """Get current connector status."""
        ...

    def validate_config(self, config: dict) -> bool:
        """Validate connector configuration. Override in subclasses."""
        return True
