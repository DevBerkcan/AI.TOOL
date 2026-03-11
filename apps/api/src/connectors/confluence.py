"""Confluence connector — syncs pages via REST API v2."""

from __future__ import annotations

import base64
from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from src.connectors.base import BaseConnector, ConnectorStatus, RawDocument

logger = structlog.get_logger()


class ConfluenceConnector(BaseConnector):
    """Atlassian Confluence document connector."""

    connector_type = "confluence"

    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "").rstrip("/")
        self.email = config.get("email", "")
        self.api_token = config.get("api_token", "")
        self.space_keys = config.get("space_keys", [])

    def _auth_header(self) -> dict:
        """Basic auth header for Confluence Cloud."""
        creds = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
        }

    async def connect(self, config: dict) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/wiki/api/v2/spaces",
                    headers=self._auth_header(),
                    params={"limit": 1},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error("Confluence connect failed", error=str(e))
            return False

    async def sync(self, last_sync_at: datetime | None = None) -> list[RawDocument]:
        """Sync pages from configured Confluence spaces."""
        documents = []

        async with httpx.AsyncClient(timeout=60) as client:
            for space_key in self.space_keys:
                # Get space ID
                resp = await client.get(
                    f"{self.base_url}/wiki/api/v2/spaces",
                    headers=self._auth_header(),
                    params={"keys": space_key, "limit": 1},
                )
                resp.raise_for_status()
                spaces = resp.json().get("results", [])
                if not spaces:
                    logger.warning("Space not found", space_key=space_key)
                    continue

                space_id = spaces[0]["id"]

                # Get pages (with optional date filter via CQL)
                params = {"space-id": space_id, "limit": 50, "body-format": "storage"}
                if last_sync_at:
                    # Use CQL for delta sync
                    cql_time = last_sync_at.strftime("%Y-%m-%d %H:%M")
                    cql = f'space="{space_key}" AND lastModified >= "{cql_time}"'
                    search_resp = await client.get(
                        f"{self.base_url}/wiki/rest/api/content/search",
                        headers=self._auth_header(),
                        params={"cql": cql, "limit": 50, "expand": "body.storage,version"},
                    )
                    search_resp.raise_for_status()
                    pages = search_resp.json().get("results", [])
                else:
                    page_resp = await client.get(
                        f"{self.base_url}/wiki/api/v2/pages",
                        headers=self._auth_header(),
                        params=params,
                    )
                    page_resp.raise_for_status()
                    pages = page_resp.json().get("results", [])

                for page in pages:
                    # Extract HTML content and convert to text
                    html_content = ""
                    if "body" in page:
                        body = page["body"]
                        if "storage" in body:
                            html_content = body["storage"].get("value", "")
                        elif isinstance(body, dict) and "value" in body:
                            html_content = body["value"]

                    plain_text = self._html_to_text(html_content)

                    page_id = str(page.get("id", ""))
                    title = page.get("title", "Untitled")

                    documents.append(
                        RawDocument(
                            external_id=page_id,
                            title=title,
                            content=plain_text.encode("utf-8"),
                            mime_type="text/plain",
                            source_url=f"{self.base_url}/wiki/spaces/{space_key}/pages/{page_id}",
                            metadata={
                                "space_key": space_key,
                                "labels": [
                                    label.get("name")
                                    for label in page.get("labels", {}).get("results", [])
                                ],
                                "version": page.get("version", {}).get("number"),
                            },
                        )
                    )

        logger.info("Confluence sync complete", documents=len(documents))
        return documents

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert Confluence storage format HTML to clean plaintext."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        # Remove macros and other Confluence-specific elements
        for tag in soup.find_all(["ac:structured-macro", "ac:parameter"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    async def get_status(self) -> ConnectorStatus:
        connected = await self.connect({})
        return ConnectorStatus(is_connected=connected)

    def validate_config(self, config: dict) -> bool:
        required = ["base_url", "email", "api_token", "space_keys"]
        return all(config.get(k) for k in required)
