"""CLI context and configuration."""

from __future__ import annotations

import urllib3
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
        no_verify: Skip TLS certificate verification (self-signed certs)
        session: Requests session (initialized later)
    """

    server: str
    port: int
    api_key: str
    debug: bool = False
    https: bool = False
    no_verify: bool = False
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

    def __enter__(self) -> CLIContext:
        """Context manager entry - create session."""
        if self.no_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.Session()
        self.session.verify = not self.no_verify
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: object,
    ) -> None:
        """Context manager exit - close session."""
        if self.session:
            self.session.close()
