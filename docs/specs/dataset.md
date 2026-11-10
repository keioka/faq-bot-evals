# Golden dataset

- We put together the golden dataset from the website, but ideally it should be written by domain experts such as customer support.
- Source: the international (en-gl) Onitsuka Tiger store pages listed in `backend/app/llm/prompts/faq_bot_kb_v1.md` (return policy, size guide, Global-e, ASICS terms, California privacy notice). English only.
- The total number of cases is 57: 32 factual, 5 procedural, 13 edge, and 7 unanswerable (6 not covered by the policies, 1 out of scope). One edge case is a prompt-injection attempt.
- `must_include` holds short literal keywords (case-insensitive) that every correct answer must contain. Each keyword appears in the case's `ideal_answer`.
- Few-shot examples live in `backend/app/llm/prompts/faq_bot_shots.jsonl` (prompt, not test data) and must not overlap these questions.
