#!/bin/bash

echo "=== Remaining markdown errors summary ==="
echo

# Count errors by type
mado check docs/ 2>&1 | grep -E "MD[0-9]+" | cut -d: -f3 | sort | uniq -c | sort -nr

echo
echo "=== Total error count ==="
mado check docs/ 2>&1 | tail -1
