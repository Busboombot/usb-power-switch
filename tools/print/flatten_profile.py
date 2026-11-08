"""Merge a Bambu Studio system profile with all the profiles it inherits from.

Usage: python flatten_profile.py <profiles/BBL dir> <category: machine|process|filament> <profile name> <out.json>
"""
import json, os, sys

root, cat, name, out = sys.argv[1:5]
index = {}
for dirpath, _, files in os.walk(os.path.join(root, cat)):
    for f in files:
        if f.endswith('.json'):
            try:
                d = json.load(open(os.path.join(dirpath, f)))
            except Exception:
                continue
            if isinstance(d, dict) and 'name' in d:
                index[d['name']] = d

chain = []
n = name
while n:
    d = index[n]
    chain.append(d)
    n = d.get('inherits', '')
merged = {}
for d in reversed(chain):
    merged.update(d)
merged['name'] = name
merged['inherits'] = ''
merged['from'] = 'system'
merged.pop('instantiation', None)
json.dump(merged, open(out, 'w'), indent=1)
print(out, 'from', ' <- '.join(c['name'] for c in chain))
