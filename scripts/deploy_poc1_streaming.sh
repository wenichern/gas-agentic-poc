#!/usr/bin/env bash
# Prereq: scripts/deploy.sh already created stack gas-poc1 (SNS topic + work-order table).
set -euo pipefail
cd "$(dirname "$0")/.."
REGION="${AWS_REGION:-$(aws configure get region)}"
ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="gas-poc1-code-$ACCT-$REGION"
aws s3 mb "s3://$BUCKET" --region "$REGION" 2>/dev/null || true
out() { aws cloudformation describe-stacks --stack-name gas-poc1 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws cloudformation package --template-file infra/poc1-streaming.yaml --s3-bucket "$BUCKET" --output-template-file /tmp/poc1-streaming.packaged.yaml
aws cloudformation deploy --stack-name gas-poc1-streaming --template-file /tmp/poc1-streaming.packaged.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides AlertTopicArn="$(out AlertTopicArn)" WorkOrderTable="$(out WorkOrderTable)" ${BEDROCK_MODEL_ID:+ModelId=$BEDROCK_MODEL_ID}
T=$(aws cloudformation describe-stacks --stack-name gas-poc1-streaming --query "Stacks[0].Outputs[?OutputKey=='ReadingsTable'].OutputValue" --output text)
echo; echo "Deployed. For the simulator and handover on your Mac:  export READINGS_TABLE=$T AWS_REGION=$REGION"
echo "Then: python poc1_field_ops/simulator.py --scenario creep --publish"
