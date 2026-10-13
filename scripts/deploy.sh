#!/bin/bash
set -e
PROJECT=tood-os
REGION=europe-west2
echo "Building and deploying TOOD-OS to Cloud Run (project: $PROJECT, region: $REGION)"
# Build and push API
gcloud builds submit apps/api --tag europe-west2-docker.pkg.dev/$PROJECT/tood/api:latest
# Build and push Web
gcloud builds submit apps/web --tag europe-west2-docker.pkg.dev/$PROJECT/tood/web:latest
# Deploy to Cloud Run
gcloud run services replace infra/cloudrun/api.yaml --region=$REGION
gcloud run services replace infra/cloudrun/web.yaml --region=$REGION
echo "Deployed successfully"
