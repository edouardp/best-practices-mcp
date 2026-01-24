#!/usr/bin/env python3
import json
import os
from pathlib import Path
import boto3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AWS Knowledge Base SDLC Docs")

def load_config():
    config_path = Path(__file__).parent / 'config.json'
    with open(config_path) as f:
        return json.load(f)

config = load_config()
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=config['region'])
s3 = boto3.client('s3', region_name=config['region'])

@mcp.tool()
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> list[dict]:
    """Search SDLC documentation using hybrid retrieval + reranking."""
    
    response = bedrock_runtime.retrieve(
        knowledgeBaseId=config['knowledge_base_id'],
        retrievalQuery={'text': search_phrase},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': limit
            }
        }
    )
    
    results = []
    for item in response['retrievalResults']:
        content = item['content']['text']
        metadata = item.get('metadata', {})
        score = item.get('score', 0.0)
        
        # Extract filename from S3 location
        location = item.get('location', {})
        s3_uri = location.get('s3Location', {}).get('uri', '')
        filename = s3_uri.split('/')[-1] if s3_uri else 'Unknown'
        
        results.append({
            'title': filename.replace('.md', ''),
            'filename': filename,
            'start_line': 1,
            'end_line': content.count('\n') + 1,
            'content': content,
            'similarity': score
        })
    
    return results

@mcp.tool()
def pqsoft_read_docs(documentation_path: str, start_line: int, end_line: int) -> str:
    """Read specific line range from a documentation file."""
    
    # Security: validate path
    if '..' in documentation_path or documentation_path.startswith('/'):
        raise ValueError("Invalid path")
    if not documentation_path.endswith('.md'):
        raise ValueError("Only .md files allowed")
    if documentation_path.startswith('.'):
        raise ValueError("Hidden files not allowed")
    
    # Download from S3
    obj = s3.get_object(Bucket=config['bucket_name'], Key=documentation_path)
    content = obj['Body'].read().decode('utf-8')
    
    # Extract line range
    lines = content.split('\n')
    if start_line < 1 or end_line > len(lines):
        raise ValueError(f"Line range out of bounds (1-{len(lines)})")
    
    return '\n'.join(lines[start_line-1:end_line])

@mcp.tool()
def pqsoft_recommend_docs(title: str) -> list[dict]:
    """Get related documentation based on content similarity."""
    
    # Find document by title
    search_response = bedrock_runtime.retrieve(
        knowledgeBaseId=config['knowledge_base_id'],
        retrievalQuery={'text': title},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 1
            }
        }
    )
    
    if not search_response['retrievalResults']:
        return []
    
    # Use first result's content as query
    source_content = search_response['retrievalResults'][0]['content']['text']
    source_location = search_response['retrievalResults'][0].get('location', {})
    source_uri = source_location.get('s3Location', {}).get('uri', '')
    source_file = source_uri.split('/')[-1] if source_uri else ''
    
    # Find similar documents
    similar_response = bedrock_runtime.retrieve(
        knowledgeBaseId=config['knowledge_base_id'],
        retrievalQuery={'text': source_content[:1000]},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 10
            }
        }
    )
    
    results = []
    for item in similar_response['retrievalResults']:
        location = item.get('location', {})
        s3_uri = location.get('s3Location', {}).get('uri', '')
        filename = s3_uri.split('/')[-1] if s3_uri else 'Unknown'
        
        # Skip original document
        if filename == source_file:
            continue
        
        content = item['content']['text']
        score = item.get('score', 0.0)
        
        results.append({
            'title': filename.replace('.md', ''),
            'filename': filename,
            'start_line': 1,
            'end_line': content.count('\n') + 1,
            'content': content,
            'similarity': score
        })
        
        if len(results) >= 5:
            break
    
    return results

if __name__ == '__main__':
    mcp.run(transport="stdio")
