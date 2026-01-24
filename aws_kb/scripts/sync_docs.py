#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
import boto3

def load_config():
    config_path = Path(__file__).parent.parent / 'config.json'
    with open(config_path) as f:
        return json.load(f)

def sync_docs(config):
    s3 = boto3.client('s3', region_name=config['region'])
    bucket = config['bucket_name']
    docs_dir = Path(__file__).parent.parent.parent / 'docs'
    
    print(f"Syncing documents from {docs_dir} to s3://{bucket}/")
    
    for md_file in docs_dir.rglob('*.md'):
        key = str(md_file.relative_to(docs_dir))
        print(f"  Uploading {key}...")
        s3.upload_file(str(md_file), bucket, key)
    
    print("Upload complete!")

def start_ingestion(config):
    bedrock = boto3.client('bedrock-agent', region_name=config['region'])
    
    print("Starting Knowledge Base ingestion...")
    response = bedrock.start_ingestion_job(
        knowledgeBaseId=config['knowledge_base_id'],
        dataSourceId=config['data_source_id']
    )
    
    job_id = response['ingestionJob']['ingestionJobId']
    print(f"Ingestion job started: {job_id}")
    
    while True:
        status = bedrock.get_ingestion_job(
            knowledgeBaseId=config['knowledge_base_id'],
            dataSourceId=config['data_source_id'],
            ingestionJobId=job_id
        )
        
        state = status['ingestionJob']['status']
        print(f"  Status: {state}")
        
        if state in ['COMPLETE', 'FAILED']:
            break
        
        time.sleep(10)
    
    if state == 'COMPLETE':
        print("Ingestion complete!")
    else:
        print("Ingestion failed!")
        sys.exit(1)

if __name__ == '__main__':
    config = load_config()
    sync_docs(config)
    start_ingestion(config)
