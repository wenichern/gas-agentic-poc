#!/usr/bin/env bash
set -euo pipefail
EMAIL="${1:?usage: scripts/deploy.sh you@company.com}"
aws cloudformation deploy --stack-name gas-poc1 --template-file infra/poc1-stack.yaml \
  --capabilities CAPABILITY_IAM --parameter-overrides AlertEmail="$EMAIL"
aws cloudformation describe-stacks --stack-name gas-poc1 --query 'Stacks[0].Outputs' --output table
echo "Copy AlertTopicArn / WorkOrderTable into .env, and confirm the SNS subscription email."
