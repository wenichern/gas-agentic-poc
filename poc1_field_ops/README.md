# POC 1: Intelligent Field Operations Assistant

```
sensor -> IoT Core -> Lambda -> store -> trend model -> GATE -+-> (normal) stop
                                                              +-> (needs reasoning) Bedrock agent -> alert / work order
                                                                                                    -> assessment log -> shift handover report
```

## Run locally (no AWS, no cost)
```bash
python poc1_field_ops/pipeline.py --scenario creep --mock --reset   # replay 6h of data, count LLM calls
python poc1_field_ops/handover.py --mock                            # handover report from what just happened
python poc1_field_ops/agent.py --mock                               # single assessment (original demo)
scripts/test.sh
```
Scenarios: `normal` (no LLM calls), `creep` (slow pressure rise, predicted ~4h before the limit; preventive P2 order), `spike`, `breach`.

## Key ideas
| Idea | Where |
|---|---|
| **Don't call the LLM per reading.** Cheap math screens the stream; the agent wakes only on a breach, a projected breach, or an anomaly. | `gate.py`, `config.py` |
| Prediction as a tool, with confidence and "insufficient data" | `analytics.py` (swap for a SageMaker endpoint, same output shape) |
| Safety floor: if the model is down, a real breach still alerts | `pipeline.py` |
| Untrusted sensor input is validated (asset_id goes into a prompt) | `pipeline.parse_event` |
| Work-order dedupe (24h) so hourly runs don't spam | `tools.create_work_order` |
| Handover generated only from logged records, no invented facts | `handover.py`, `prompts/handover.md` |

## On AWS
```bash
scripts/deploy.sh you@company.com          # SNS + work-order table (base stack)
scripts/deploy_poc1_streaming.sh           # Lambda + IoT rule + readings table
export READINGS_TABLE=<printed value> AWS_REGION=us-east-1
python poc1_field_ops/simulator.py --scenario creep --publish   # history to DynamoDB, newest reading via IoT Core
python poc1_field_ops/handover.py                               # real model, reads logs from DynamoDB
scripts/destroy.sh
```
### What triggers what
1. `simulator.py --publish` (on your Mac) stores the history in DynamoDB and publishes the newest reading to the IoT Core topic `gas/sensors/<asset_id>`.
2. The IoT rule `gas_poc1_sensor_rule` (created by `infra/poc1-streaming.yaml`) matches `gas/sensors/+` and invokes the Lambda.
3. The Lambda runs `lambda_handler.py` -> `pipeline.py`: store, trend model, gate, then the Bedrock agent only if needed.

The Python files never call the Lambda directly, and nothing exists in AWS until both deploy scripts have run.

### Test the Lambda by itself (skips IoT)
Use the function name printed by the stack output (`FunctionName`):
```bash
aws lambda invoke --function-name <FunctionName> --cli-binary-format raw-in-base64-out \
  --payload '{"asset_id":"VALVE-101","pressure_psi":842,"flow_m3h":47,"temperature_c":88}' /tmp/out.json && cat /tmp/out.json
```
If direct invoke works but publishing through IoT does not, the problem is the IoT rule or its Lambda permission, not your code.

### Where to look
CloudWatch Logs for the function show `invoked: true/false` and the reasons for each reading. Rejected sensor messages are logged as `rejected`.

## Honest limits
- The trend model is a linear fit. It assumes steady drift and will miss cycles, step changes, and multi-sensor patterns. It is a teaching stand-in for a real model.
- The mock agent is rules, not a language model. Test the prompts with a real Bedrock model.
- AWS deployment and IoT publishing are untested from my side; I could only test locally. Expect small fixes.
- A single replay of 6h of data costs almost nothing, but a real fleet sending readings every few seconds would still invoke the Lambda constantly. Check IoT Core and Lambda pricing and consider batching at the edge before connecting real devices.
- Read-only toward operations: the agent proposes work orders, humans approve. Do not connect to live SCADA without engineering and safety review.
