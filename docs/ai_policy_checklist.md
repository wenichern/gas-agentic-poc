# AI policy checklist (adapt to your company's defined AI policies)
- [ ] Data classification: no customer PII or critical-infrastructure details leave approved AWS accounts/regions
- [ ] Bedrock Guardrails enabled (PII redaction, denied topics)
- [ ] Human-in-the-loop for safety, financial, regulatory actions
- [ ] Every tool call and model output logged (CloudWatch / S3) for audit
- [ ] Least-privilege IAM (see infra/poc1-stack.yaml)
- [ ] Model + prompt versioned in git, changes reviewed
- [ ] OT/SCADA systems are READ-ONLY for the agent in the POC
- [ ] Documented fallback when the model is unavailable
