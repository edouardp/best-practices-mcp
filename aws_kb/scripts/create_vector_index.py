#!/usr/bin/env -S uv run
# /// script
# dependencies = ["boto3"]
# ///
import boto3
import sys

region = 'ap-southeast-2'
vector_bucket_name = 'sdlc-docs-vectors'
index_name = 'sdlc-docs-kb-index'

client = boto3.client('s3vectors', region_name=region)

try:
    response = client.create_index(
        vectorBucketName=vector_bucket_name,
        indexName=index_name,
        dataType='float32',
        dimension=1024,  # Titan Embeddings v2 dimension
        distanceMetric='cosine'
    )
    print(f"✅ Vector index created: {response['indexArn']}")
except client.exceptions.ConflictException:
    print(f"✅ Vector index already exists")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
