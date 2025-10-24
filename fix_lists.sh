#!/bin/bash

# Fix MD032 - Lists should be surrounded by blank lines

echo "Adding blank lines around lists..."

for file in docs/*.md; do
    echo "Processing $file..."
    
    temp_file=$(mktemp)
    prev_line=""
    in_list=false
    
    while IFS= read -r line; do
        # Check if current line is a list item
        if [[ $line =~ ^[[:space:]]*[-*+][[:space:]] ]]; then
            # Starting a list - add blank line before if previous line is not empty
            if [[ $in_list == false ]] && [[ -n $prev_line ]]; then
                echo "" >> "$temp_file"
            fi
            in_list=true
        else
            # Not a list item
            if [[ $in_list == true ]] && [[ -n $line ]]; then
                # Ending a list - add blank line after
                echo "" >> "$temp_file"
            fi
            in_list=false
        fi
        
        echo "$line" >> "$temp_file"
        prev_line="$line"
    done < "$file"
    
    mv "$temp_file" "$file"
done

echo "List spacing fixed."
