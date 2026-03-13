#!/bin/bash
# Wait for file to be released
sleep 2

# Remove the problematic file
rm -f "src/components/chat/MarkdownRenderer.jsx"

# Rename the fixed version
mv "src/components/chat/MarkdownRenderer_fixed.jsx" "src/components/chat/MarkdownRenderer.jsx"

echo "MarkdownRenderer.jsx fixed!"
