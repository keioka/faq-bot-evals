"""Recompute content_hash for every version in prompts/<bot>.json.

    uv run python -m app.llm.commands.update_hashes           # rewrite stale hashes in place
    uv run python -m app.llm.commands.update_hashes --check   # exit 1 if any hash is stale (for CI)
"""

import json
import sys

from app.llm.utils.get_content_hash import PROMPTS_DIR, get_content_hash


def main(check: bool) -> int:
    stale = []
    for registry in sorted(PROMPTS_DIR.glob("*.json")):
        versions = json.loads(registry.read_text(encoding="utf-8"))
        changed = False
        for name, entry in versions.items():
            content_hash = get_content_hash(entry, registry.stem)
            if entry.get("content_hash") != content_hash:
                stale.append(f"{registry.name} {name}")
                entry["content_hash"] = content_hash
                changed = True
        if changed and not check:
            registry.write_text(json.dumps(versions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not stale:
        print("All hashes are up to date.")
        return 0
    if check:
        print("Stale hashes (run `uv run python -m app.llm.commands.update_hashes`):\n  " + "\n  ".join(stale))
        return 1
    print("Updated:\n  " + "\n  ".join(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv[1:]))
