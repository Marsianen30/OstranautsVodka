#!/usr/bin/env python3
"""Apply only unambiguous Russian placeholder cleanups to complete/.

This is deliberately conservative. Larger context-dependent rewrites are left
for the agent chunks.
"""
from pathlib import Path

ROOT = Path('/home/user/wspace/complete')
REPLACEMENTS = {
    # Keep [is] so the DLL can conjugate it; remove only the literal Russian
    # duplicate. Example: [us] [is] является частью -> [us] [is] частью.
    '[is] является': '[is]',
    # These two sentences already contain a Russian finite verb, so the
    # English copula is redundant.
    '[us] [is] сидит': '[us] сидит',
    '[us] [is] надежно сидит': '[us] надежно сидит',
}

changed_files = 0
counts = {k: 0 for k in REPLACEMENTS}
for path in sorted(ROOT.rglob('*.json')):
    text = path.read_text(encoding='utf-8')
    new = text
    for old, replacement in REPLACEMENTS.items():
        n = new.count(old)
        if n:
            counts[old] += n
            new = new.replace(old, replacement)
    if new != text:
        path.write_text(new, encoding='utf-8')
        changed_files += 1

print('changed_files:', changed_files)
for old, n in counts.items():
    print(f'{old} -> {REPLACEMENTS[old]}: {n}')
