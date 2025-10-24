#!/bin/bash

# Fix trailing spaces (MD009) in all markdown files

echo "Removing trailing spaces from markdown files..."

for file in docs/*.md; do
    echo "Processing $file..."
    # Remove trailing spaces and tabs
    sed -i '' 's/[[:space:]]*$//' "$file"
done

echo "Trailing spaces removed."
