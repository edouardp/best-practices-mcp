#!/bin/bash

# Fix MD022 - Headers should be surrounded by blank lines

echo "Adding blank lines around headers..."

for file in docs/*.md; do
    echo "Processing $file..."
    
    # Create temp file
    temp_file=$(mktemp)
    
    # Process file line by line
    prev_line=""
    while IFS= read -r line; do
        # If current line is a header and previous line is not empty
        if [[ $line =~ ^#+[[:space:]] ]] && [[ -n $prev_line ]]; then
            echo "" >> "$temp_file"
        fi
        echo "$line" >> "$temp_file"
        prev_line="$line"
    done < "$file"
    
    # Replace original file
    mv "$temp_file" "$file"
done

echo "Header spacing fixed."
