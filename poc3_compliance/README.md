# POC 3: Regulatory Compliance Agent (RAG)

Input: a new regulatory bulletin. Output: a **draft** gap analysis with citations, deadlines, and actions for a compliance officer.

```bash
python poc3_compliance/agent.py --mock          # offline
python poc3_compliance/agent.py                 # Bedrock model, local retrieval
KB_ID=XXXX python poc3_compliance/agent.py      # Bedrock model + Knowledge Base (see KB_SETUP.md)
python poc3_compliance/agent.py --bulletin path/to/other.md
```

## Patterns to learn
| Pattern | Where |
|---|---|
| Retrieval as a tool (agent decides what to search, can retry) | `tools.py`, `retriever.py` |
| Swappable retriever (local vs Bedrock KB) | `get_retriever()` |
| Grounding rules in the prompt | `prompts/system.md` |
| Citation verification (rejects ids the agent never retrieved) | `validator.py` |
| Self-repair loop (one retry with validator feedback) | `agent.py` |
| Human in the loop (status is always DRAFT, no submission tool) | prompt + validator |

## Exercises
1. Change SOP-REC-02 to say 5 years. The gap list should shrink to one.
2. Delete SOP-OD-03. Expect "no matching procedure found" as a gap, not an invention.
3. Copy `data/exercises/poisoned_procedure.md` into `data/procedures/` and run with a real model. A good prompt ignores the embedded instruction. Does yours? Note: the mock cannot be fooled or tested on this, only a real model can.
4. Make the bulletin ambiguous ("at reasonable intervals"). The agent should flag it for human review rather than guess. Update the prompt until it does.
5. Add an eval file with 10 bulletins and expected gap counts (see ../docs/eval.md).

## Honest limits
- All documents are SYNTHETIC. Replace with your real regulations and SOPs (public documents first, per your data policy).
- The mock uses regex, not reasoning; it demonstrates the plumbing. Real models handle messy language, which is where you should test.
- The validator proves a citation was retrieved, not that the model interpreted it correctly. A human still reviews.
