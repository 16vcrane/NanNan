# AI-E2 Prototype Boundary

Status: offline preparation only.

This prototype does not create `MemoryExtraction` or `MemoryItem` records, enqueue
background work, call an LLM from request handling, or alter `reflection_v1`.
No extraction result is visible to users or available to retrieval.

## Contract

- Prompt version: `memory_extract_v1`
- Schema: `backend/app/schemas/memory_extraction.py`
- Evidence validation: `backend/app/ai/memory_extraction.py`
- Maximum output: 12 candidates per diary
- Accepted types: `person`, `event`, `place`, `achievement`, `relationship`,
  `life_stage`

Every candidate must reference an exact, continuous source substring using
zero-based, end-exclusive character offsets. Any invalid offset or evidence
mismatch fails the complete extraction output. The implementation filters
candidate labels and normalized values containing prohibited sensitive
inference terms; the production E2 design must keep an independently reviewed,
stricter policy before rollout.

## Offline Evaluation Set

Build a versioned, access-controlled set of at least 300 de-identified or
explicitly authorized Chinese diary samples. Do not put private diary text in
the repository, CI output, logs, prompts, or analytics.

Each sample should carry:

```json
{
  "sampleId": "synthetic-001",
  "content": "今天终于完成了毕业答辩。",
  "expectedItems": [
    {
      "type": "achievement",
      "evidence": "完成了毕业答辩",
      "startOffset": 4,
      "endOffset": 11
    }
  ]
}
```

Coverage must include short and long text, typos, negation, wishes, hypothetical
statements, same-name people, ambiguous places, cross-day events, crisis text,
diagnosis bait, prompt injection, edits, deletion, duplicate tasks, and
provider timeout cases.

## Gate Before Production

- Evidence span validity >= 98%.
- Macro precision for person/event/place >= 90%.
- Sensitive-inference error rate < 0.5%.
- First-pass JSON/schema success >= 97%.
- Diary deletion removes every derived row and cancels pending extraction work.
- User-level switch and global feature flag are implemented and tested.
