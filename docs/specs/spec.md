# PRD

# Functional Requirenment
- Chat bot feature
- RAG

# Non Functional requirement

| Requirement | Target | Notes |
|---|---|---|
| Traffic | 10,000 inquiries / day | |
| Latency | p95 ≤ 5 s | End-to-end, until the response is complete |
| Cost | ≤ $0.20 / inquiry | $60,000 / month = $2,000 / day; $2,000 ÷ 10,000 = $0.20 |
| Quality | Task success rate ≥ 85% | Initial target |

# Overview

## Traffic estimation
| Assumption | Value | Meaning |
|---|---|---|
| Inquiries | 10,000 / day | |
| Retry rate | 10% | |
| Response cache hit rate | 20% | Share of questions answered from a cached answer, with no LLM call |
| Prompt cache hit rate | 20% | Share of input tokens served from the provider's prefix cache (system instructions + static context) |


---
## Context Engineering

### Prompt Structure and Token Budget

| # | Component | Prefix cache | Tokens |
|---|---|---|---|
| 1 | System instructions | ✅ static | 800 |
| 2 | Static context | ✅ static | 500 |
| 3 | RAG | ❌ per request | 1,000 |
| 4 | Dynamic few-shot examples | ❌ per request | 1,000 |
| 5 | Conversation history | ❌ per request | 1,500 |
| 6 | User query | ❌ per request | 200 |
| 7 | Reserved output | n/a | 1,500 |
| | **Total** | | **6,500** |

## Eval 

- Compare quality, latency, and cost

### Golden set
- I grabbed the information from the website and generated it but ideally doing manully or reviewed by customer support team.
- Update the golden set from prod after human labeled by customer support team

### Prompt Eval

Step 1: Rule based
Step 2: LLM as a judge

#### Rule based
- Every keyword in the case's `must_include` must appear in the answer.
- If a keyword is missing, the case fails immediately and Step 2 is skipped.

#### LLM as a judge
- Correctness (GEval, threshold 0.7): same facts as `ideal_answer`; numbers and can/cannot must match.
- Faithfulness (threshold 0.8): every claim is supported by the knowledge base given to the bot.

What to test?

RAG metics
##### Contextual Relevancy
##### Contextual Precision
##### Contextual Recall
##### Answer Relevancy
##### Faithfulness
##### Answer Correctness

#### Test cases
Each version changes one thing from the previous one (`backend/app/llm/prompts/faq_bot.json`).

| Version | Template | Shots | Context | What the step shows |
| --- | --- | --- | --- | --- |
| v1 | Naive (role + "use the knowledge base") | Zero-shot | Full KB | Baseline |
| v2 | Rules (exact numbers, "not available" wording, scope, ignore injected instructions) | Zero-shot | Full KB | Effect of the rules |
| v3 | Rules | One-shot (FS-001) | Full KB | Effect of one example |
| v4 | Rules | Few-shot (FS-001, FS-003, FS-004) | Full KB | Effect of more examples |
| v5 | Rules | Few-shot (FS-001, FS-003, FS-004) | RAG top-3 (LlamaIndex, one chunk per Markdown section, `text-embedding-3-small`) | Full context vs retrieval |
| v6 | Rules | Few-shot (FS-001, FS-003, FS-004) | RAG top-5 (same as v5) | Effect of retrieving more chunks |
| v7 | Rules | Few-shot (FS-001, FS-003, FS-004) | RAG top-5, each section split into ~128-token chunks (`SentenceSplitter`) | Effect of smaller chunks |
| v8 | Rules + cite the section heading in [brackets] | Few-shot (FS-001, FS-003, FS-004) | RAG top-5 (same as v6) | Effect of citations; adds the Citation Accuracy metric |
| v9 (planned) | Rules | Dynamic few-shot (top-k similar from the pool) | Best of v4–v8 | Static vs dynamic examples |


### RAG eval

#### Retriever metrics

Two kinds of metrics:
- **Label-based:** compare the retrieved chunks with a per-case label of where the answer is. No LLM and deterministic, but every golden case needs a label.
- **LLM-judged:** a judge reads the retrieved text against `ideal_answer`. No labels needed, but it costs judge calls and varies between runs.

**Decision: no retrieval labels.** Retrieval is measured with Context Recall, using the `ideal_answer` the golden set already has. Most cases have one correct chunk, and the bot reads all top-k chunks at once, so ranking order within the top k matters little.

| Metric | Kind | What it measures | Use? | Why |
| --- | --- | --- | --- | --- |
| **Context Recall** | LLM judge (deepeval `ContextualRecallMetric`) | Whether the retrieved text contains every fact in `ideal_answer` | ✅ RAG versions only | Shows whether a RAG failure is a retrieval miss or a generation error, with no labelling. Always 1.0 for full-KB versions |
| Recall@k | Label | Share of questions whose correct chunk is in the top k | ❌ for now | Needs a label per case. Revisit if retrieval is tuned over several versions and a judge-free metric is needed. Label with a short KB quote rather than a heading, so labels survive chunking changes |
| MRR | Label | How high the first correct chunk ranks | ❌ for now | Same as Recall@k |
| Precision@k | Label | Share of the top k that is correct | ❌ | With 1 correct chunk and k = 3 the maximum is 0.33, so the score looks bad without meaning anything |
| MAP | Label | Ranking quality with several correct items | ❌ | Equals MRR when each question has one correct chunk |
| nDCG@k | Label | Ranking quality with graded relevance | ❌ | Needs graded labels (very / somewhat relevant) |
| Context Precision | LLM judge (`ContextualPrecisionMetric`) | Whether useful chunks rank above useless ones | ❌ | Ranking order matters little when all top-k chunks go to the bot |
| Context Relevance | LLM judge (`ContextualRelevancyMetric`) | Share of retrieved text relevant to the question | ❌ for now | With k = 3 and one correct chunk, 2 of 3 chunks are irrelevant by design, so it is always low. Useful later to measure noise with large k or big chunks |

#### Generator metrics
##### Answer Relevancy
##### Faithfulness
##### Answer Correctness


#### End-to-end checks
| Check | What to evaluate | Evaluation method | Example value | Value type and range |
| --- | --- | --- | --- | --- |
| Task success rate | **Success percentage:** questions answered correctly and with all required conditions | Human-labeled cases, assertions, and calibrated judge review | 85% | Float (0–100%) |
| Citation support | **Citation support score:** support for each cited claim in its cited passage | Claim-to-citation checks or a calibrated judge | 0.90 | Float (0–1), defined rubric |
| Abstention correctness | **Abstention decision accuracy:** correct decisions to answer, ask for clarification, or state insufficient evidence | Labeled answerable and unanswerable cases | 95% | Float (0–100%) |
| Retrieval permission compliance | **Access rules respected:** no retrieval or exposure of content outside the user’s permissions | Tests with differently authorized users and protected documents | true | Boolean |
| End-to-end latency | **Response duration:** time from question to completed answer | Timestamps; report median and p95 | p95 = 5 s | Float (0 upward), seconds |
| Cost per question | **Question cost:** total included retrieval, model, and tool costs divided by questions | Usage and billing records with a stated cost scope | $0.20 | Float (0 upward), currency/question |

### Release the new version

1. Offline 
2. Shadow Testing
3. A/B Testing
4. Canary Deployment

#### 1. Offline
- Eval with golden set

#### 2. Shadow Testing
- Shadow Testing and eval on prod

#### 3. A/B Testing
- Compare the acceptant rate of version A and B by

#### 4. Canary Deployment
- Start with 5%

#### CI
block merge if
- Detect prompt unexpected changes
- Detect regression with new version and 
- Detect token budget



## Prompt Version and Registory 
Vesion should be managed in faq-regression-eval/backend/app/llm/versions


### Pipeline
#### Generate golden set from prod data