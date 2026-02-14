"""Chat persistence - JSON-based storage for chat conversations."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CHATS_DIR = Path.home() / ".ralph-dashboard" / "chats"


def _ensure_dir():
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def list_conversations() -> list[dict]:
    """List all saved conversations, sorted by last update."""
    _ensure_dir()
    convos = []
    for f in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            convos.append({
                "id": data.get("id", f.stem),
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "message_count": len(data.get("messages", [])),
                "model": data.get("model", ""),
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Failed to read chat file %s: %s", f, e)
    convos.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    return convos


def get_conversation(conv_id: str) -> dict | None:
    """Get a single conversation by ID."""
    _ensure_dir()
    path = CHATS_DIR / f"{conv_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def create_conversation(title: str = "Nuova chat", model: str = "") -> dict:
    """Create a new empty conversation."""
    _ensure_dir()
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    data = {
        "id": conv_id,
        "title": title,
        "model": model,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    path = CHATS_DIR / f"{conv_id}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def update_conversation(conv_id: str, updates: dict) -> dict | None:
    """Update conversation fields (title, messages, etc.)."""
    _ensure_dir()
    path = CHATS_DIR / f"{conv_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if "title" in updates:
        data["title"] = updates["title"]
    if "messages" in updates:
        data["messages"] = updates["messages"]
    if "model" in updates:
        data["model"] = updates["model"]
    data["updated_at"] = datetime.now().isoformat()

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def add_message(conv_id: str, role: str, content: str) -> dict | None:
    """Append a single message to a conversation."""
    _ensure_dir()
    path = CHATS_DIR / f"{conv_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    data["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    data["updated_at"] = datetime.now().isoformat()

    # Auto-title from first user message if still default
    if data["title"] in ("Nuova chat", "Untitled", "") and role == "user":
        data["title"] = content[:60] + ("..." if len(content) > 60 else "")

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def delete_conversation(conv_id: str) -> bool:
    """Delete a conversation."""
    path = CHATS_DIR / f"{conv_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
