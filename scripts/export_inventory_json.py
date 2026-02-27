#!/usr/bin/env python3
import runpy, json

mod = runpy.run_path('docs/sensory_entry_points_inventory.py')
entries = mod.get('SENSORY_ENTRY_POINTS', [])
summary = mod.get('SUMMARY', {})

out = {
    'SENSORY_ENTRY_POINTS': entries,
    'SUMMARY': summary,
}

with open('docs/sensory_entry_points.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print('Wrote docs/sensory_entry_points.json', len(entries), 'entries')
