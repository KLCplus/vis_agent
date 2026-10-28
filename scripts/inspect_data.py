"""Inspect every semantic MC1 archive file; no assumed counts or schema."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
REPORTS = ROOT / 'data/reports'


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def inventory():
    return [{'file': str(p.relative_to(RAW)), 'bytes': p.stat().st_size,
             'format': p.suffix, 'metadata_only': '__MACOSX' in p.parts or p.name == '.DS_Store'}
            for p in sorted(RAW.rglob('*')) if p.is_file() and p.name != '.gitkeep']


def inspect():
    fields = defaultdict(lambda: {'types': Counter(), 'present': 0, 'null': 0})
    datasets = []
    def walk(value, path='$'):
        f = fields[path]; f['types'][type(value).__name__] += 1; f['present'] += 1
        f['null'] += value is None
        if isinstance(value, dict):
            for k, v in value.items(): walk(v, path + '.' + k)
        elif isinstance(value, list):
            for v in value: walk(v, path + '[]')
    for p in sorted(RAW.rglob('*.json')):
        if '__MACOSX' in p.parts: continue
        obj = json.loads(p.read_text(encoding='utf-8')); walk(obj)
        datasets.append({'file': str(p.relative_to(RAW)), 'top_level': list(obj) if isinstance(obj,dict) else type(obj).__name__, 'rounds':len(obj.get('rounds',[]))})
    if not datasets: raise FileNotFoundError('No official JSON. Run python scripts/download_data.py first.')
    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS/'data_dictionary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['json_path','types','occurrences','null_count'],lineterminator='\n');w.writeheader()
        for p,v in sorted(fields.items()): w.writerow({'json_path':p,'types':json.dumps(v['types']),'occurrences':v['present'],'null_count':v['null']})
    result={'files':inventory(),'datasets':datasets,'field_paths':len(fields)}
    dump(REPORTS/'data_profile.json', result)
    return result

if __name__ == '__main__':
    print(json.dumps(inspect(),ensure_ascii=False,indent=2))
