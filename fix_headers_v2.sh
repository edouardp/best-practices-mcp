#!/bin/bash

# Fix MD022 - Headers should be surrounded by blank lines (comprehensive)

echo "Fixing header spacing comprehensively..."

for file in docs/*.md; do
    echo "Processing $file..."
    
    # Use awk for better control
    awk '
    BEGIN { prev_empty = 1 }
    /^#+/ {
        if (!prev_empty && NR > 1) print ""
        print $0
        next
    }
    {
        print $0
        prev_empty = (length($0) == 0)
    }
    ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
done

echo "Header spacing fixed comprehensively."
