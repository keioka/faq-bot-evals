import json
import os
from functools import cache
from pathlib import Path

from openai import OpenAI

from app.llm.rag import retrieve
from app.llm.utils.get_content_hash import get_content_hash

VERSION_FILE = Path(__file__).parent / "versions" / "faq_bot.json"
PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPTS_FILE = PROMPTS_DIR / "faq_bot.json"
SHOTS_FILE = PROMPTS_DIR / "faq_bot_shots.jsonl"


def live_version() -> str:
    """The version the API serves by default (versions/faq_bot.json)."""
    return str(json.loads(VERSION_FILE.read_text(encoding="utf-8"))["version"])


def list_versions() -> dict[str, dict]:
    """All registry entries, keyed by version."""
    return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))


@cache
def load_prompt(version: str) -> dict:
    """Load one registry entry and refuse it if its content was edited without updating content_hash."""
    prompts = list_versions()
    if version not in prompts:
        raise KeyError(f"version {version} not found in {PROMPTS_FILE.name} (available: {sorted(prompts)})")
    prompt = prompts[version]
    if (digest := get_content_hash(prompt, "faq_bot")) != prompt["content_hash"]:
        raise ValueError(
            f"{version} content_hash is {prompt['content_hash']} but the content hashes to {digest}. "
            "Run `uv run python -m app.llm.commands.update_hashes`."
        )
    return prompt


# Default version: FAQ_BOT_VERSION if set (evals), else the live version. The live pointer is never edited.
DEFAULT_VERSION = os.environ.get("FAQ_BOT_VERSION") or live_version()
PROMPT = load_prompt(DEFAULT_VERSION)  # checked at import, so a stale hash still stops the server from starting
MODEL = PROMPT["model"]


def _load_shot_messages(ids: list[str]) -> list[dict]:
    """Look up the version's shot IDs in the pool and turn each into a user/assistant message pair."""
    pool = {s["id"]: s for s in map(json.loads, SHOTS_FILE.read_text(encoding="utf-8").splitlines())}
    if missing := [i for i in ids if i not in pool]:
        raise KeyError(f"shot IDs {missing} not found in {SHOTS_FILE.name}")
    messages = []
    for i in ids:
        messages += [
            {"role": "user", "content": pool[i]["question"]},
            {"role": "assistant", "content": pool[i]["answer"]},
        ]
    return messages


@cache
def _knowledge_base(kb_file: str) -> str:
    return (PROMPTS_DIR / kb_file).read_text(encoding="utf-8")

@cache
def _client() -> OpenAI:
    return OpenAI()


def answer(question: str, version: str | None = None) -> tuple[str, list[str], dict[str, int]]:
    """Return the answer, the context it was grounded on (used as retrieval_context in evals), and token usage.

    version: any registry version (the chat UI's selector); None uses DEFAULT_VERSION.
    """
    prompt = load_prompt(version or DEFAULT_VERSION)
    knowledge_base = _knowledge_base(prompt["context"]["kb"])
    # "full": pass the whole knowledge base. "rag": pass only the top-k sections for this question.
    ctx = prompt["context"]
    if ctx["mode"] == "rag":
        context = retrieve(question, knowledge_base, ctx["k"], ctx["embed_model"], ctx.get("chunk_size"))
    else:
        context = [knowledge_base]
    response = _client().responses.create(
        model=prompt["model"],
        instructions=f"{prompt['template']}\n\n# Knowledge base\n" + "\n\n".join(context),
        input=[*_load_shot_messages(prompt["shots"]["ids"]), {"role": "user", "content": question}],
        reasoning={"effort": "low"},
    )
    if response.status != "completed":
        raise RuntimeError(f"response {response.status}: {response.incomplete_details}")
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    return response.output_text.strip(), context, usage
