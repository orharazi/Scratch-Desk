#!/bin/bash
# Git Repository Corruption Fix Script

echo "=========================================="
echo "Git Repository Corruption Fix"
echo "=========================================="
echo ""

# Step 1: Find and remove all empty/corrupted object files
echo "Step 1: Finding corrupted objects..."
corrupted=$(find .git/objects -type f -size 0 2>/dev/null)
count=$(echo "$corrupted" | grep -v '^$' | wc -l)

if [ $count -eq 0 ]; then
    echo "✓ No corrupted objects found!"
else
    echo "Found $count corrupted object(s):"
    echo "$corrupted" | while read file; do
        if [ -n "$file" ]; then
            echo "  - $file"
        fi
    done

    echo ""
    echo "Step 2: Removing corrupted objects..."
    find .git/objects -type f -size 0 -delete
    echo "✓ Removed $count corrupted object(s)"
fi

echo ""
echo "Step 3: Verifying remote connection..."
if git remote -v | grep -q origin; then
    echo "✓ Remote 'origin' found"

    echo ""
    echo "Step 4: Fetching from remote to restore objects..."
    git fetch origin --prune 2>&1 | head -20

    echo ""
    echo "Step 5: Running git fsck to verify..."
    echo ""
    git fsck --full 2>&1 | head -20

    echo ""
    echo "=========================================="
    echo "Fix attempt complete!"
    echo "=========================================="
    echo ""
    echo "If you still see errors above, try:"
    echo "  git reset --hard origin/main"
    echo "  (This will discard local changes)"
else
    echo "✗ No remote found"
    echo ""
    echo "Manual fix required:"
    echo "1. Backup your working directory"
    echo "2. Re-clone the repository"
fi
