# Prompt anatomy for agents (learn this first)
Every agent prompt has 7 parts. POC1's `system.md` shows all of them.
1. **Role**: who the agent is and who it serves.
2. **Context/inputs**: what data it receives and how it is formatted.
3. **Tools**: what it may call, and when NOT to.
4. **Workflow**: numbered steps. Agents follow order well.
5. **Rules/guardrails**: hard limits, escalation, human approval.
6. **Output contract**: exact JSON schema so code can parse it.
7. **Failure behavior**: what to do on missing/conflicting data.

## Habits that matter
- Put thresholds in the prompt (or better, in a tool) rather than trusting model memory.
- Use temperature 0 for operational agents.
- Cap the loop (MAX_STEPS) and log every tool call.
- Test with adversarial and incomplete inputs, not only the happy path.
- Change one thing at a time and keep a small eval set (see docs/eval.md).

## Using Claude/Cursor to build with these
Paste this to your coding assistant:
> "Read prompts/00_prompt_engineering_guide.md and prompts/03_compliance.md. Create poc3_compliance/ following the structure of poc1_field_ops (llm.py, tools.py, agent.py, prompts/system.md, a test). Use simulated tools first, with a --mock flag."
