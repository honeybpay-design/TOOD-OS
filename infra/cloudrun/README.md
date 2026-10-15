# Cloud Run Deployment Guide

## Prerequisites
- gcloud CLI authenticated with `honeybpay@gmail.com`
- Project: `tood-os`, Region: `europe-west2`
- Artifact Registry repo `tood` created in `europe-west2`
- Secret Manager secrets: `tood-secrets` with keys DATABASE_URL, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

## Deploy

```bash
bash scripts/deploy.sh
```

## DNS Setup at Fasthosts for tood.uk

After deploying, note the Cloud Run service URLs from the gcloud output.
Then set these DNS records in your Fasthosts control panel:

| Type  | Name | Value                          | Notes                        |
|-------|------|--------------------------------|------------------------------|
| A     | @    | [Cloud Run IP from gcloud]     | tood.uk root domain          |
| A     | www  | [Cloud Run IP from gcloud]     | www.tood.uk                  |
| CNAME | api  | ghs.googlehosted.com           | api.tood.uk → API service    |
| TXT   | @    | google-site-verification=xxx   | Google domain verification   |

For Cloud Run custom domains, use:
```bash
gcloud run domain-mappings create --service tood-os-web --domain tood.uk --region europe-west2
gcloud run domain-mappings create --service tood-os-web --domain www.tood.uk --region europe-west2
gcloud run domain-mappings create --service tood-os-api --domain api.tood.uk --region europe-west2
```

The `gcloud` command will output the IP addresses to use in Fasthosts DNS.

## Stripe Webhook

After deploying, register the webhook endpoint in the Stripe Dashboard:
- URL: `https://api.tood.uk/v1/billing/webhook`
- Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

Copy the webhook signing secret into Secret Manager:
```bash
echo -n "whsec_xxx" | gcloud secrets versions add tood-secrets --data-file=-
```
