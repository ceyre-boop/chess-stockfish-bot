#!/usr/bin/env python3
import runpy
from collections import Counter

mod = runpy.run_path('docs/sensory_entry_points_inventory.py')
entries = mod.get('SENSORY_ENTRY_POINTS', [])
print('Finalized SENSORY_ENTRY_POINTS count:', len(entries))
counts = Counter(e.get('classification','WRAP') for e in entries)
print('By classification:', dict(counts))
prov = {}
for e in entries:
    prov.setdefault(e.get('provider','unknown'), set()).add(e.get('module'))
print('Providers counts:')
for k, v in prov.items():
    print(f" - {k}: {len(v)} modules")
validate = mod.get('validate_inventory')
missing = []
if validate:
    try:
        missing = validate()
    except Exception as exc:
        print('Validation failed:', exc)
print('Validation missing count:', len(missing))
if missing:
    print('Missing samples:')
    for m in missing[:50]:
        print(' -', m)
