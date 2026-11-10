"""content_hash for prompt registry entries (used by faq_bot on load and by commands/update_hashes.py).

content_hash = sha256 of everything the model sees for that version: model, template,
               the resolved shot texts, the context config, and the knowledge base text.
Does not import faq_bot, because faq_bot refuses to load while a hash is stale.
"""

import hashlib
import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).parents[1] / "prompts"


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _load_shots(bot: str) -> dict[str, dict]:
    path = PROMPTS_DIR / f"{bot}_shots.jsonl"
    if not path.exists():
        return {}
    return {s["id"]: s for s in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def get_content_hash(entry: dict, bot: str) -> str:
    """Hash one registry entry together with the shot and knowledge base files it points to."""
    shots = _load_shots(bot)
    payload = {
        "model": entry["model"],
        "template": entry["template"],
        # Hash the shot texts, not just the IDs, so editing a shot in the pool changes the hash
        "shots": {**entry["shots"], "resolved": [shots[i] for i in entry["shots"].get("ids", [])]},
        # Same for the knowledge base: hash its text, so an in-place edit changes the hash
        "context": {**entry["context"], "kb_text_sha256": _sha256((PROMPTS_DIR / entry["context"]["kb"]).read_text(encoding="utf-8"))},
    }
    return _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
