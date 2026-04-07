import datetime
import logging

from notion_client import Client

from config import NOTION_PAGE_ID, NOTION_TOKEN


def append_to_notion(text: str) -> None:
    """Append a timestamped dictation entry to the configured Notion page."""
    if not NOTION_TOKEN or not NOTION_PAGE_ID:
        logging.warning("Notion not configured — set NOTION_TOKEN and NOTION_PAGE_ID in .env.")
        return

    client = Client(auth=NOTION_TOKEN)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"{timestamp}  →  {text}"

    client.blocks.children.append(
        NOTION_PAGE_ID,
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
