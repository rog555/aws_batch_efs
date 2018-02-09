#!/bin/bash
# CHANGE
AWS_ACCOUNT_ID=123456789012
REPO=aws_batch_efs
REGION=us-east-1
$(aws ecr get-login --no-include-email --region $REGION)
docker tag disktest:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest