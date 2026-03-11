"""SharePoint connector — syncs documents via Microsoft Graph API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx
import structlog

from src.connectors.base import BaseConnector, ConnectorStatus, RawDocument

logger = structlog.get_logger()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md"}


class SharePointConnector(BaseConnector):
    """Microsoft SharePoint document connector using Graph API."""

    connector_type = "sharepoint"

    def __init__(self, config: dict):
        self.site_url = config.get("site_url", "")
        self.library_name = config.get("library_name", "Documents")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.tenant_id = config.get("tenant_id", "")
        self._access_token: str | None = None
        self._delta_link: str | None = config.get("_delta_link")

    async def _get_token(self) -> str:
        """Acquire access token via Client Credentials flow."""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async def connect(self, config: dict) -> bool:
        """Test connection to SharePoint."""
        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                # Try to access the site
                resp = await client.get(
                    f"{GRAPH_BASE}/sites/root",
                    headers=self._headers(token),
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error("SharePoint connect failed", error=str(e))
            return False

    async def sync(self, last_sync_at: Optional[datetime] = None) -> list[RawDocument]:
        """Sync documents from SharePoint library."""
        token = await self._get_token()
        documents = []

        async with httpx.AsyncClient(timeout=60) as client:
            # Get site ID from URL
            hostname = self.site_url.split("//")[1].split("/")[0]
            site_path = "/".join(self.site_url.split("//")[1].split("/")[1:])

            site_resp = await client.get(
                f"{GRAPH_BASE}/sites/{hostname}:/{site_path}",
                headers=self._headers(token),
            )
            site_resp.raise_for_status()
            site_id = site_resp.json()["id"]

            # Use delta query for incremental sync
            if self._delta_link:
                url = self._delta_link
            else:
                url = f"{GRAPH_BASE}/sites/{site_id}/drive/root/delta"

            while url:
                resp = await client.get(url, headers=self._headers(token))
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("value", []):
                    if item.get("file") and not item.get("deleted"):
                        name = item.get("name", "")
                        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""

                        if ext not in SUPPORTED_EXTENSIONS:
                            continue

                        # Download file content
                        download_url = item.get("@microsoft.graph.downloadUrl")
                        if download_url:
                            file_resp = await client.get(download_url)
                            content = file_resp.content
                        else:
                            item_id = item["id"]
                            file_resp = await client.get(
                                f"{GRAPH_BASE}/sites/{site_id}/drive/items/{item_id}/content",
                                headers=self._headers(token),
                            )
                            content = file_resp.content

                        documents.append(RawDocument(
                            external_id=item["id"],
                            title=name,
                            content=content,
                            mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                            source_url=item.get("webUrl"),
                            metadata={
                                "size": item.get("size"),
                                "created_by": item.get("createdBy", {}).get("user", {}).get("displayName"),
                                "last_modified_by": item.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
                            },
                            last_modified=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
                            if "lastModifiedDateTime" in item else None,
                        ))

                # Follow pagination or save delta link
                url = data.get("@odata.nextLink")
                if "@odata.deltaLink" in data:
                    self._delta_link = data["@odata.deltaLink"]

        logger.info("SharePoint sync complete", documents=len(documents))
        return documents

    async def get_status(self) -> ConnectorStatus:
        try:
            connected = await self.connect({})
            return ConnectorStatus(is_connected=connected, message="OK" if connected else "Connection failed")
        except Exception as e:
            return ConnectorStatus(is_connected=False, message=str(e))

    def validate_config(self, config: dict) -> bool:
        required = ["site_url", "client_id", "client_secret", "tenant_id"]
        return all(config.get(k) for k in required)
