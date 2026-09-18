"""One-time setup of the Bedrock Knowledge Base on S3 Vectors, after `sam deploy`.

1. uploads knowledge-base/ (documents + .metadata.json sidecars) to the stack's KnowledgeBucket
2. creates an S3 vector bucket + index (Titan Text Embeddings V2, 1024 dimensions, cosine)
3. creates the knowledge base and its S3 data source, and runs ingestion
Prints the KnowledgeBaseId to pass back to `sam deploy --parameter-overrides KnowledgeBaseId=...`.

Usage: uv run --project backend python infra/setup_knowledge_base.py --stack claimback --region ap-south-1
"""

import argparse
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DIMENSIONS = 1024


def stack_outputs(cfn, stack: str) -> dict[str, str]:
    outputs = cfn.describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
    return {o["OutputKey"]: o["OutputValue"] for o in outputs}


def upload_knowledge(s3, bucket: str) -> int:
    count = 0
    for path in sorted((ROOT / "knowledge-base").rglob("*")):
        if path.is_file():
            key = path.relative_to(ROOT / "knowledge-base").as_posix()
            s3.upload_file(str(path), bucket, key)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="claimback")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--name", default="claimback-kb")
    parser.add_argument("--ingest-only", action="store_true", help="skip the upload; only (re)run ingestion")
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region)
    outputs = stack_outputs(session.client("cloudformation"), args.stack)
    bucket, role_arn = outputs["KnowledgeBucketName"], outputs["KnowledgeBaseRoleArn"]

    if not args.ingest_only:
        print(f"uploading knowledge-base/ to s3://{bucket} ...")
        print(f"  {upload_knowledge(session.client('s3'), bucket)} files")

    vectors = session.client("s3vectors")
    vector_bucket = f"{args.name}-vectors"
    index_name = "claimback-index"
    try:
        vectors.create_vector_bucket(vectorBucketName=vector_bucket)
    except vectors.exceptions.ConflictException:
        pass
    try:
        vectors.create_index(
            vectorBucketName=vector_bucket, indexName=index_name, dataType="float32", dimension=DIMENSIONS, distanceMetric="cosine",
            # chunk text is stored as vector metadata; keep it out of the small filterable-metadata budget
            metadataConfiguration={"nonFilterableMetadataKeys": ["AMAZON_BEDROCK_TEXT"]},
        )
    except vectors.exceptions.ConflictException:
        pass
    index_arn = vectors.get_index(vectorBucketName=vector_bucket, indexName=index_name)["index"]["indexArn"]
    vector_bucket_arn = vectors.get_vector_bucket(vectorBucketName=vector_bucket)["vectorBucket"]["vectorBucketArn"]

    agent = session.client("bedrock-agent")
    existing = next((k for k in agent.list_knowledge_bases()["knowledgeBaseSummaries"] if k["name"] == args.name), None)
    kb = agent.get_knowledge_base(knowledgeBaseId=existing["knowledgeBaseId"])["knowledgeBase"] if existing else agent.create_knowledge_base(
        name=args.name,
        description="IRDAI regulations, Arogya Sanjeevani policy wordings, non-payable item lists and real Ombudsman / court decisions",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": f"arn:aws:bedrock:{args.region}::foundation-model/{EMBEDDING_MODEL}",
                "embeddingModelConfiguration": {"bedrockEmbeddingModelConfiguration": {"dimensions": DIMENSIONS, "embeddingDataType": "FLOAT32"}},
            },
        },
        storageConfiguration={"type": "S3_VECTORS", "s3VectorsConfiguration": {"vectorBucketArn": vector_bucket_arn, "indexArn": index_arn}},
    )["knowledgeBase"]
    print(f"knowledge base {'reused' if existing else 'created'}: {kb['knowledgeBaseId']}")
    kb_id = kb["knowledgeBaseId"]
    while agent.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]["status"] == "CREATING":
        time.sleep(5)

    sources = agent.list_data_sources(knowledgeBaseId=kb_id)["dataSourceSummaries"]
    existing_source = next((d for d in sources if d["name"] == "claimback-documents"), None)
    source = {"dataSourceId": existing_source["dataSourceId"]} if existing_source else agent.create_data_source(
        knowledgeBaseId=kb_id,
        name="claimback-documents",
        dataSourceConfiguration={"type": "S3", "s3Configuration": {"bucketArn": f"arn:aws:s3:::{bucket}"}},
        vectorIngestionConfiguration={
            "chunkingConfiguration": {"chunkingStrategy": "FIXED_SIZE", "fixedSizeChunkingConfiguration": {"maxTokens": 400, "overlapPercentage": 15}}
        },
    )["dataSource"]
    job = agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=source["dataSourceId"])["ingestionJob"]
    print("ingesting ...")
    while True:
        job = agent.get_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=source["dataSourceId"], ingestionJobId=job["ingestionJobId"])["ingestionJob"]
        if job["status"] in ("COMPLETE", "FAILED", "STOPPED"):
            break
        time.sleep(10)
    print(f"ingestion {job['status']}: {job.get('statistics')}")
    if job["status"] == "FAILED":
        print("failures:", job.get("failureReasons"))
    print(f"\nKnowledgeBaseId={kb_id}\nNow run: sam deploy --parameter-overrides KnowledgeBaseId={kb_id} ...")


if __name__ == "__main__":
    main()
