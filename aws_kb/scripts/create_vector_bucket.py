#!/usr/bin/env -S uv run
# /// script
# dependencies = ["boto3"]
# ///
import boto3
import sys

region = 'ap-southeast-2'
vector_bucket_name = 'sdlc-docs-vectors'

client = boto3.client('s3vectors', region_name=region)

try:
    response = client.create_vector_bucket(
        vectorBucketName=vector_bucket_name,
        encryptionConfiguration={'sseType': 'AES256'}
    )
    print(f"✅ Vector bucket created: {response['vectorBucketArn']}")
except client.exceptions.ConflictException:
    print(f"✅ Vector bucket already exists: arn:aws:s3vectors:{region}:*:vector-bucket/{vector_bucket_name}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
