# ADR-001: Eval framework

**Status:** Proposed  
**Date:** 2026-11-08
**Decision Makers:** Kei Oka

## 1. Context

What problem are we trying to solve?

- Current situation: 
We need to have eval framework to run the eval. Writing the eval from scratch takes time.

- Technical requirements: 
    - Python
    - Works on CI
- Constraints:
    - Free
    - Not much learning curve 
- Why a decision is needed now:
    - We need to eval our prompt.

## 2. Decision Drivers

What factors are most important?

- Cost
- Implementation complexity
- Developer experience
- Reliability
- Performance / Latency
- Scalability

## 3. Considered Options

### Option A: [DeepEval]
- Pros: 
  - Works on Python (+ Implementation complexity)
  - Works on Python test (+ Implementation complexity)
  - Free for eval in local (+ Cost)

- Cons:
  - A little bit of learning curve (- Developer experience)
  - Blackbox for LLM as a judge (- Reliability)

### Option B: [LangSmith]
- Pros:
  - Solid platform.
  - Works well with LangChain and LangGraph.
  
- Cons:
  - 

### Option C: [Ragas]
- Pros:
  - Good at RAG.
- Cons:
  -  

## 4. Decision

**We decided to use Deepeval.**

Reasons:
1. Free
2. Implementation complexity is relatively low
3. Developer experience is not too bad if you know some methods. Was able to create and run the test within an hour

## 5. Consequences

### Positive
- Good so far. Easy to use. 
- Well documented

### Negative / Trade-offs
- Just need to run the document.
- No GUI for free.

### Risks
- [Risk and mitigation]

## 6. Validation

How will we know this was the right decision?

- Success metrics: Any engineer can add test within an hour.
- Testing / Benchmarking: N/A
- Conditions for reconsideration: Become not free.

## 7. References

- [Benchmark]
- [Documentation]
- [Related ADR]