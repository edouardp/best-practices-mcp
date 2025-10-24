#!/bin/bash

# Fix common markdown issues in docs directory

echo "Fixing markdown issues in docs/"

for file in docs/*.md; do
    echo "Processing $file..."
    
    # Remove trailing spaces (MD009)
    sed -i '' 's/[[:space:]]*$//' "$file"
    
    # Add blank lines before headers (MD022)
    sed -i '' '/^#/ {
        x
        /^$/ !{
            x
            i\

            b
        }
        x
    }' "$file"
    
    # Add blank lines after headers (MD022)
    sed -i '' '/^#.*/ {
        N
        /\n[^#]/ {
            s/\n/\n\n/
        }
    }' "$file"
    
    # Add blank lines around fenced code blocks (MD031)
    sed -i '' '/^```/ {
        x
        /^$/ !{
            x
            i\

            b
        }
        x
    }' "$file"
    
    # Add blank lines around lists (MD032)
    sed -i '' '/^[[:space:]]*[-*+]/ {
        x
        /^$/ !{
            x
            i\

            b
        }
        x
    }' "$file"
    
done

echo "Basic fixes applied. Running mado to check remaining issues..."
mado check docs/
