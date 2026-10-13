#!/usr/bin/env bash
aws cloudformation delete-stack --stack-name gas-poc1 && echo "Deleting gas-poc1 (stops all cost)."
