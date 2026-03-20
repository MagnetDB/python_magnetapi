"""CLI context and configuration."""

from dataclasses import dataclass, field
from typing import Optional
import requests


@dataclass
class CLIContext:
    """Context passed to all command handlers.

    Attributes:
        server: API server hostname
        port: API port number
        api_key: API authentication key
        debug: Debug mode flag
        https: Use HTTPS flag
        session: Requests session (initialized later)
    """

    server: str
    port: int
    api_key: str
    debug: bool = False
    https: bool = False
    session: Optional[requests.Session] = field(default=None, repr=False)

    @property
    def headers(self) -> dict:
        """HTTP headers for API authentication."""
        return {"Authorization": self.api_key}

    @property
    def web(self) -> str:
        """Full API base URL."""
        if self.https:
            return f"https://{self.server}"
        return f"http://{self.server}:{self.port}"

    @property
    def verify_ssl(self) -> bool:
        """Whether to verify SSL certificates."""
        return not self.https

    def __enter__(self):
        """Context manager entry - create session."""
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        if self.session:
            self.session.close()
