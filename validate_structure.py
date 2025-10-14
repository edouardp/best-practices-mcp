#!/usr/bin/env python3
import os
import ast

def validate_files():
    """Validate that all required files exist and have correct structure."""
    
    required_files = [
        'Dockerfile',
        'docker-compose.yml', 
        'requirements.txt',
        'build_index.py',
        'server.py',
        'README.md'
    ]
    
    print("=== Validating file structure ===")
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            return False
    
    print("\n=== Validating Python syntax ===")
    python_files = ['build_index.py', 'server.py']
    
    for file in python_files:
        try:
            with open(file, 'r') as f:
                content = f.read()
            ast.parse(content)
            print(f"✓ {file} syntax valid")
        except SyntaxError as e:
            print(f"✗ {file} syntax error: {e}")
            return False
        except Exception as e:
            print(f"✗ {file} error: {e}")
            return False
    
    print("\n=== Validating server.py structure ===")
    with open('server.py', 'r') as f:
        server_content = f.read()
    
    required_functions = ['search_documentation', 'read_documentation', 'recommend']
    for func in required_functions:
        if f"def {func}" in server_content:
            print(f"✓ {func} function found")
        else:
            print(f"✗ {func} function missing")
            return False
    
    print("\n=== Validating build_index.py structure ===")
    with open('build_index.py', 'r') as f:
        build_content = f.read()
    
    required_imports = ['duckdb', 'sentence_transformers']
    for imp in required_imports:
        if imp in build_content:
            print(f"✓ {imp} import found")
        else:
            print(f"✗ {imp} import missing")
            return False
    
    print("\n=== Validating Dockerfile ===")
    with open('Dockerfile', 'r') as f:
        dockerfile_content = f.read()
    
    if 'RUN python build_index.py' in dockerfile_content:
        print("✓ Build step found in Dockerfile")
    else:
        print("✗ Build step missing in Dockerfile")
        return False
    
    if 'CMD ["python", "server.py"]' in dockerfile_content:
        print("✓ Server command found in Dockerfile")
    else:
        print("✗ Server command missing in Dockerfile")
        return False
    
    print("\n=== Creating docs directory if missing ===")
    if not os.path.exists('docs'):
        os.makedirs('docs')
        print("✓ Created docs directory")
    else:
        print("✓ docs directory exists")
    
    print("\n=== All validations passed! ===")
    print("\nTo test the system:")
    print("1. Install Docker")
    print("2. Run: docker-compose up --build")
    print("3. Test MCP communication via stdio")
    
    return True

if __name__ == "__main__":
    import sys
    success = validate_files()
    sys.exit(0 if success else 1)
