Q&A bot for this project is meant to demonstrate how I would evaluate the model and improve it. This is not showing my frontend or full stack ability.

This project contains some LLM app concepts like 

- Eval for answers and RAG.
- Prompt Management 
- Contenxt Engineering


# Structure

```
faq-regression-eval/
├── backend/                          FastAPI app + eval (managed with uv)
│   ├── app/
│   │   ├── main.py                   API: POST /api/faq, GET /api/versions, GET /api/health
│   │   └── llm/
│   │       ├── faq_bot.py            Loads a version, verifies its content_hash, calls the model
│   │       ├── rag.py                Markdown-section chunking + embedding retrieval (LlamaIndex)
│   │       ├── prompts/              Everything the model sees, versioned
│   │       │   ├── faq_bot.json          Prompt registry: v1–v8 (template, shots, context, content_hash)
│   │       │   ├── faq_bot_shots.jsonl   Few-shot example pool, referenced by ID
│   │       │   └── faq_bot_kb_v1.md      Knowledge base (store policies, size guide, terms)
│   │       ├── versions/
│   │       │   └── faq_bot.json      Live pointer: the version the API serves
│   │       ├── utils/
│   │       │   └── get_content_hash.py   sha256 of model + template + shots + context + KB
│   │       ├── commands/
│   │       │   └── update_hashes.py  Regenerate hashes, or --check in CI
│   │       └── tests/
│   │           └── test_faq_bot.py   Rule check + LLM-judge metrics (deepeval)
│   └── eval_results/faq_bot/         Saved run per version: v1.json … v8.json  (planned)
├── test_data/
│   ├── golden_set.jsonl              57 cases: question, ideal_answer, must_include, type
│   └── safety_set.jsonl              6 cases: off-topic advice, abusive users
├── frontend/                         React + Vite chat UI with a prompt-version selector
│   └── src/App.tsx
├── docs/
│   ├── specs/
│   │   ├── spec.md                   Requirements, version ladder, metric choices
│   │   ├── token_budget.md           Measured tokens and cost per version
│   │   ├── dataset.md                How the golden set was built
│   │   ├── eval.md                   Eval design and findings log
│   │   └── prompt.md                 Prompt registry notes
│   └── decisions/
│       └── ADR-001-eval.md           Why deepeval and Ragas
└── .github/workflows/llm-eval.yml    CI: hash check on every PR; eval when the live version changes
```

## Command

```bash
# backend (http://localhost:8000)
cd backend
uv run fastapi dev app/main.py

# frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```

## Eval

Run from `backend/`. The LLM eval needs `OPENAI_API_KEY`; the hash check does not.

```bash
cd backend
uv sync                                                   # first time only

# Check content_hash in prompts/*.json is up to date (no API calls)
uv run python -m app.llm.commands.update_hashes --check
# Regenerate it after editing a template, shot, or knowledge base file
uv run python -m app.llm.commands.update_hashes

# Full eval: all golden and safety cases against the live version in app/llm/versions/faq_bot.json
uv run deepeval test run app/llm/tests/test_faq_bot.py -n 8

# Evaluate a specific version (default: the live version in app/llm/versions/faq_bot.json)
FAQ_BOT_VERSION=v3 uv run deepeval test run app/llm/tests/test_faq_bot.py -n 8

# One or a few cases
uv run pytest app/llm/tests/test_faq_bot.py -k "EN-004"
uv run pytest app/llm/tests/test_faq_bot.py -k "EN-004 or SF-001"

# Repeat each case 3 times to see run-to-run noise
uv run deepeval test run app/llm/tests/test_faq_bot.py -n 8 --repeat 3
```

`FAQ_BOT_VERSION` only affects that run; `app/llm/versions/faq_bot.json` (the live version the API serves) is never edited.


| Version | Change | Pass | Golden | Safety | Avg input tokens | Cost / question | Avg latency |
|---|---|---|---|---|---|---|---|
| v1 | Naive prompt (baseline) | 46 (73%) | 42/57 | 4/6 | 3,956 | $0.00042 | 1.92 s |
| v2 | + Rules | 60 (95%) | 55/57 | 5/6 | 4,072 | $0.00043 | 1.49 s |
| v3 | + One-shot example | 62 (98%) | 56/57 | 6/6 | 4,117 | $0.00043 | 1.85 s |
| v4 | + Few-shot examples | 61 (97%) | 56/57 | 5/6 | 4,203 | $0.00044 | 1.49 s |
| v5 | RAG, top-3 sections (v4 prompt) | 57 (90%) | 51/57 | 6/6 | 926 | $0.00011 | 1.88 s |
| v6 | RAG, top-5 sections | 60 (95%) | 54/57 | 6/6 | 1,223 | $0.00014 | 1.98 s |
| v7 | + 128-token chunks ✗ | 49 (78%) | 43/57 | 6/6 | 689 | $0.00009 | 1.99 s |
| v8 | v6 + source citations | 57 (90%) | 51/57 | 6/6 | 1,275 | $0.00015 | 2.02 s |
