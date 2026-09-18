# Deploying ClaimBack to AWS

**Live as of 18 Sep 2026** in account 656791094360, region ap-south-1:

| What | Where |
|---|---|
| Web app (Amplify Hosting) | https://main.d2nbtgk28gfk1k.amplifyapp.com |
| API (API Gateway + Lambda) | https://pngg77cn4c.execute-api.ap-south-1.amazonaws.com |
| Stack | `claimback` |
| Knowledge Base | `SIP3PORRNW` (created; ingestion pending Bedrock account verification) |

Redeploy after a code change:

```bash
cd backend && uv run python scripts/build_lambda.py && cd ..
sam deploy --template-file infra/template.yaml --stack-name claimback --region ap-south-1   --capabilities CAPABILITY_IAM --resolve-s3 --no-confirm-changeset   --parameter-overrides ModelId=global.anthropic.claude-opus-5 BedrockClient=invoke   KnowledgeBaseId=SIP3PORRNW FrontendOrigin=https://main.d2nbtgk28gfk1k.amplifyapp.com

cd frontend && VITE_API_BASE=https://pngg77cn4c.execute-api.ap-south-1.amazonaws.com npm run build && cd ..
uv run --project backend python infra/deploy_frontend.py --region ap-south-1
```

## Two things learned the hard way

1. **The Messages-API Bedrock endpoint (`bedrock-mantle`) does not exist in ap-south-1** - it returns 404, while the same call in us-east-1 returns a normal 403 for an ungranted model. So in Mumbai, call Claude through `bedrock-runtime` InvokeModel: parameter `BedrockClient=invoke` with an inference-profile model id (`global.anthropic.claude-opus-5`). `apac.anthropic.claude-opus-5` does not exist; `global.` does, and it may serve requests outside India.
2. **A new AWS account is verified for Bedrock before any model can be called** ("Your account is currently being verified... normally takes less than 2 hours"). Until it clears, even Titan embeddings return 403, so Knowledge Base ingestion fails.

## Still to do on this account

- [ ] **Submit the Anthropic use-case form** for Claude Opus 5 in the Bedrock console (Mumbai). Until then every Claude call returns 403 "not available for this account". The app degrades gracefully: sample claims work, uploads fail, and the AI review step is skipped with a note.
- [ ] **Re-run Knowledge Base ingestion** once verification clears: `uv run --project backend python infra/setup_knowledge_base.py --stack claimback --region ap-south-1 --ingest-only`
- [ ] **Set a budget alert** (Billing -> Budgets), e.g. $20/month.

## Original first-time instructions

Nothing here had been deployed when this was written. These steps create billable resources in your account. The serverless pieces cost close to nothing when idle; Claude Opus 5 on Bedrock is roughly $0.50–1 per analysed uploaded claim.

Region: `ap-south-1` (Mumbai) keeps policyholders' medical documents in India. Claude Opus 5, Titan Text Embeddings V2 and S3 Vectors are all available there, as verified on 2026-09-17.

## Prerequisites

- AWS CLI v2 logged in to the target account, and Docker running
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (not installed on this machine yet)
- Python 3.13 with `uv`, and Node 24

## 1. API, pipeline and storage (SAM)

```bash
cd backend
uv run python scripts/build_lambda.py          # assembles backend/.build/lambda, incl. Linux wheels - no Docker needed
cd ..
sam deploy --template-file infra/template.yaml --stack-name claimback --region ap-south-1   --capabilities CAPABILITY_IAM --resolve-s3 --no-confirm-changeset
```

`build_lambda.py` installs dependencies for `x86_64-manylinux2014` / Python 3.13, so `sam build --use-container`
(and Docker) are not required. Keep the `*.dist-info` folders: `httpx2` reads its own version from installed
metadata at import time and crashes without them.

Note the `ApiUrl` output.

## 2. Knowledge Base on S3 Vectors

```bash
cd ..
uv run --project backend python infra/setup_knowledge_base.py --stack claimback --region ap-south-1
cd infra
sam deploy --stack-name claimback --region ap-south-1 --capabilities CAPABILITY_IAM \
  --parameter-overrides KnowledgeBaseId=<id printed above> FrontendOrigin=<your Amplify URL>
```

S3 Vectors is used instead of OpenSearch Serverless, which has a minimum monthly cost that would use up the hackathon credits.

## 3. Frontend (Amplify Hosting)

```bash
cd frontend
VITE_API_BASE=<ApiUrl> npm run build           # on Windows: set VITE_API_BASE=<ApiUrl> && npm run build
```

Then deploy `dist/` to Amplify Hosting:

```bash
uv run --project backend python infra/deploy_frontend.py --region ap-south-1
```

That script creates the app and `main` branch on first run, adds the SPA rewrite so React Router URLs survive a
refresh, uploads `dist/` and starts the deployment. Connecting the Git repository instead also works: the root
`amplify.yml` builds `frontend/`, with `VITE_API_BASE` set under the app's environment variables. Add a rewrite of `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>` to `/index.html` (200) so React Router URLs work. Then redeploy the SAM stack with `FrontendOrigin` set to the Amplify URL (step 2).

## Check before the demo

- [ ] **Bedrock permissions.** The template grants `bedrock:InvokeModel*` (the invoke path in use) and `bedrock-mantle:*` (for regions where the Messages-API endpoint exists). Both were accepted by IAM.
- [ ] **Model access.** Anthropic models on Bedrock may require submitting the use-case form once per account. Try a small request in the Bedrock console playground first.
- [ ] **API Gateway timeout.** The API Lambda has a 29-second limit. Document reading runs in Step Functions (10 minutes per step), and letter polishing falls back to the template letter if Claude errors.
- [ ] **Smoke test.** Run a sample claim first, which doesn't need Claude, then an uploaded claim, e.g. `samples/s1-consumables-mix-cashless/hospital_bill_photo.jpg` plus the other S1 PDFs.

## Tear down

```bash
sam delete --stack-name claimback --region ap-south-1
aws bedrock-agent delete-knowledge-base --knowledge-base-id <id> --region ap-south-1
aws s3vectors delete-index --vector-bucket-name claimback-kb-vectors --index-name claimback-index --region ap-south-1
aws s3vectors delete-vector-bucket --vector-bucket-name claimback-kb-vectors --region ap-south-1
```

S3 buckets must be emptied before `sam delete` can remove them.
