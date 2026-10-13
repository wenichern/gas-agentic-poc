# Gas BU Agentic AI POCs (AWS + Bedrock)

Learn to build and prompt AI agents for a natural gas business unit. Starts offline (no cost), then moves to AWS.

## Use cases
| # | Agent | Status | Prompt |
|---|-------|--------|--------|
| 1 | Field Operations Assistant | **Runnable** | `poc1_field_ops/prompts/system.md` |
| 2 | Supply-Chain Optimization | Prompt + exercises | `prompts/02_supply_chain.md` |
| 3 | Regulatory Compliance (RAG) | **Runnable** | `poc3_compliance/` |
| 4 | Safety Monitoring | Prompt + exercises | `prompts/04_safety.md` |
| 5 | Customer Service Chatbot | Prompt + exercises | `prompts/05_customer_service.md` |
| 6 | Trading & Risk (decision support) | Prompt + exercises | `prompts/06_trading_risk.md` |
| 7 | Asset Performance | Prompt + exercises | `prompts/07_asset_performance.md` |
| 8 | Carbon / ESG | Prompt + exercises | `prompts/08_carbon_esg.md` |

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Offline, no AWS (learn the agent loop)
SCENARIO=breach python poc1_field_ops/agent.py --mock
SCENARIO=normal python poc1_field_ops/agent.py --mock
pytest -q

# 2. Real model on Bedrock (enable model access in the Bedrock console first)
cp .env.example .env   # set model ID, then: set -a; source .env; set +a
python poc1_field_ops/agent.py

# 3. Real alerts and work orders on AWS
scripts/deploy.sh you@company.com   # SNS + DynamoDB + least-privilege policy
# put the outputs in .env, rerun step 2
scripts/destroy.sh                  # clean up
```
Outputs are also written to `out/alerts.jsonl` and `out/work_orders.jsonl`.

## POC 3 (Compliance RAG)
`python poc3_compliance/agent.py --mock`; see `poc3_compliance/README.md` and `KB_SETUP.md`.

## How it works
`agent.py` is the whole agent pattern: send messages + tool definitions to Bedrock Converse, run any tool the model requests, return results, repeat until done (capped at 8 steps). Sensors are simulated in `tools.py`; replace them with IoT Core / historian reads when ready.

## Learning path
1. Read `prompts/00_prompt_engineering_guide.md`.
2. Edit `poc1_field_ops/prompts/system.md` (change a threshold, break a rule) and watch behavior change.
3. Use Claude/Cursor to generate POC 3 from the template (instruction in the guide).
4. Review `docs/ai_policy_checklist.md` before touching real data.
5. Explore `docs/advanced_ideas.md`.

## Safety
Simulated data only. Agents are read-only and propose actions; humans approve. Not for operational use without engineering and safety review.
