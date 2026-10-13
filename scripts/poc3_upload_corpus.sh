#!/usr/bin/env bash
# Deploys the bucket and uploads the corpus. Usage: scripts/poc3_upload_corpus.sh
set -euo pipefail
aws cloudformation deploy --stack-name gas-poc3-corpus --template-file infra/poc3-bucket.yaml
B=$(aws cloudformation describe-stacks --stack-name gas-poc3-corpus --query "Stacks[0].Outputs[?OutputKey==\`BucketName\`].OutputValue" --output text)
aws s3 sync poc3_compliance/data/regulations "s3://$B/regulations/"
aws s3 sync poc3_compliance/data/procedures  "s3://$B/procedures/"
echo "Bucket: $B  -> now create the Knowledge Base (poc3_compliance/KB_SETUP.md)"
