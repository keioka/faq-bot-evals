# Token budget: v1–v5

Actual token use per prompt version, compared with the budget in [spec.md](spec.md) (Prompt Structure and Token Budget).

## How it was counted

- **Per component:** `tiktoken` `o200k_base`, counted offline from `backend/app/llm/prompts/` (template, the shots in `faq_bot_shots.jsonl`, and the knowledge base text including the `# Knowledge base` heading).
  - For v5, this is the 3 sections retrieved for the test question.
- **Measured input:** `response.usage.input_tokens` from one real call per version with the question "Can I return socks?" (5 tokens).
- **Message overhead:** the measured input minus the offline sum. These are the tokens the API adds for each message: 1 message in v1/v2, 3 in v3, 7 in v4/v5 (shot questions, shot answers, user question).
- **Reserved output:** the budget value from spec.md. One sample answer used 36–83 output tokens.

## Results

| # | Component | Budget | v1 | v2 | v3 | v4 | v5 |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | System instructions (template) | 800 | 26 | 142 | 142 | 142 | 142 |
| 2 | Static context (full knowledge base) | 500 | **3,909** ❌ | **3,909** ❌ | **3,909** ❌ | **3,909** ❌ | 0 |
| 3 | RAG (top-3 sections) | 1,000 | 0 | 0 | 0 | 0 | 417 |
| 4 | Few-shot examples | 1,000 | 0 | 0 | 35 (FS-001) | 101 (FS-001, 003, 004) | 101 (FS-001, 003, 004) |
| 5 | Conversation history | 1,500 | 0 | 0 | 0 | 0 | 0 |
| 6 | User query | 200 | 5 | 5 | 5 | 5 | 5 |
| – | Message overhead | – | 9 | 9 | 19 | 39 | 39 |
| | **Input (measured)** | **5,000** | **3,949** | **4,065** | **4,110** | **4,196** | **704** |
| 7 | Reserved output | 1,500 | 1,500 | 1,500 | 1,500 | 1,500 | 1,500 |
| | **Total** | **6,500** | **5,449** ✅ | **5,565** ✅ | **5,610** ✅ | **5,696** ✅ | **2,204** ✅ |

- Golden set questions average 11.5 tokens (max 22), so the user query stays well under its 200-token budget.
- v5's RAG size depends on which sections are retrieved. The largest section is about 2,400 characters (a size table), so 3 large sections could approach the 1,000-token RAG budget.

## Cost estimate

**Prices (per 1M tokens):**

| Model | Input | Output | Source |
|---|---:|---:|---|
| `gpt-6-luna` (bot) | $0.10 | $0.50 | `PRICE_PER_1M` in `backend/app/llm/tests/test_faq_bot.py` (from deepeval's price table) |
| `text-embedding-3-small` (v5 only) | $0.02 | – | OpenAI list price |

**Per question:** input × $0.10/1M + output × $0.50/1M, plus the question embedding for v5 (5 tokens, about $0.0000001).
- **Typical** uses the sample's measured output tokens. These include reasoning tokens, which are billed as output.
- **Worst case** uses the full 1,500 reserved output tokens.

| | v1 | v2 | v3 | v4 | v5 |
|---|---:|---:|---:|---:|---:|
| Input tokens (measured) | 3,949 | 4,065 | 4,110 | 4,196 | 704 |
| Output tokens (sample) | 36 | 83 | 62 | 56 | 60 |
| Input cost | $0.000395 | $0.000407 | $0.000411 | $0.000420 | $0.000070 |
| Output cost | $0.000018 | $0.000042 | $0.000031 | $0.000028 | $0.000030 |
| **Typical / question** | **$0.00041** | **$0.00045** | **$0.00044** | **$0.00045** | **$0.00010** |
| Worst case / question (1,500 output) | $0.00115 | $0.00116 | $0.00116 | $0.00117 | $0.00082 |
| Typical / day (10,000 questions) | $4.13 | $4.48 | $4.42 | $4.48 | $1.01 |
| Typical / month (30 days) | $124 | $134 | $133 | $134 | $30 |
| vs $0.20 / question budget | ~490× under | ~450× under | ~450× under | ~450× under | ~2,000× under |

- **v5's index:** embedding the 21 sections (~3,900 tokens) costs about $0.00008 once per process start, so it's left out of the per-question cost.
- **Not included:** the 10% retry rate, the 20% response cache and 20% prompt cache from the spec's traffic table, and the eval judge's cost. These are per-question model costs only.
- **Accuracy:** each figure comes from one question, so treat these as order-of-magnitude estimates. A full eval run records `token_cost` per case for averages over 63 questions.
