import datetime
import logging

from notion_client import Client

from config import NOTION_PAGE_ID, NOTION_TOKEN

# ---------------------------------------------------------------------------
# Client cache — reused across calls; recreated only if token changes
# ---------------------------------------------------------------------------

_notion_client: Client | None = None
_notion_client_token: str = ""


def _get_client(token: str) -> Client:
    global _notion_client, _notion_client_token
    if _notion_client is None or _notion_client_token != token:
        _notion_client       = Client(auth=token)
        _notion_client_token = token
    return _notion_client


def append_to_notion(text: str, token: str = None, page_id: str = None) -> None:
    """Append a timestamped dictation entry to the configured Notion page.

    token and page_id override the values from .env (used by the settings
    Test Connection button without requiring a module reload).
    """
    token   = token   or NOTION_TOKEN
    page_id = page_id or NOTION_PAGE_ID

    if not token or not page_id:
        logging.warning("Notion not configured — set NOTION_TOKEN and NOTION_PAGE_ID in .env.")
        return

    client    = _get_client(token)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry     = f"{timestamp}  →  {text}"

    client.blocks.children.append(
        page_id,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": entry}}]
                },
            }
        ],
    )
    logging.info("Notion logged: %s", entry)
