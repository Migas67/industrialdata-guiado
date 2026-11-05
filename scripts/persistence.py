"""Capturar antes/después de reiniciar Docker, sin escribir en PostgreSQL."""
import argparse
import json
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq
from industrialdata.common import root, dump, sha
from industrialdata.catalog import connection
from industrialdata.run import current_snapshot

p = argparse.ArgumentParser(); p.add_argument('phase', choices=['before', 'after']); a = p.parse_args()
folder = root(); snap = current_snapshot(folder)
if snap is None: raise RuntimeError('Falta la demo publicada')
files = []
profiles = {}
for label, dataset in [('demo', folder), ('volume100k', folder/'volume100k'), ('volume1m', folder/'volume1m')]:
    visible = current_snapshot(dataset)
    if visible is None:
        if label == 'demo': raise RuntimeError('Falta la demo')
        continue
    files += [dataset/name for name in ['current.json', 'catalog.json', 'manifest.json', 'escenarios_esperados.json'] if (dataset/name).exists()]
    files += [f for d in ['raw', 'late', 'snapshots'] for f in (dataset/d).rglob('*') if f.is_file()]
    profiles[label] = dict(canonical_rows=pq.ParquetFile(visible/'silver/telemetry.parquet').metadata.num_rows,
                           episodes=pq.ParquetFile(visible/'gold/episodes.parquet').metadata.num_rows)
state = dict(files={f.relative_to(folder).as_posix(): sha(f) for f in sorted(files)}, tables={})
state['profiles'] = profiles
with connection() as conn:
    for table in ['machines', 'sensors', 'catalog_settings', 'runs']:
        records = conn.execute('SELECT row_to_json(t)::text FROM '+table+' t').fetchall()
        state['tables'][table] = sorted(json.dumps(json.loads(r[0]), sort_keys=True) for r in records)
state['canonical_rows'] = len(pd.read_parquet(snap/'silver/telemetry.parquet'))
state['episodes'] = len(pd.read_parquet(snap/'gold/episodes.parquet'))
capture = dict(captured_at=datetime.now(timezone.utc).isoformat(), state=state)
dump(folder/f'reports/persistence_{a.phase}.json', capture)
if a.phase == 'after':
    before = json.loads((folder/'reports/persistence_before.json').read_text())
    assert before['state'] == state, 'El inventario cambió tras el reinicio'
    dump(folder/'reports/persistence.json', dict(passed=True, before=before['captured_at'], after=capture['captured_at'],
         canonical_rows=state['canonical_rows'], episodes=state['episodes'], files_verified=len(state['files']),
         profiles=profiles,
         table_counts={k:len(v) for k,v in state['tables'].items()},
         checks='Igualdad exacta de SHA256 de fuentes, instantáneas y puntero; contenido de cuatro tablas PostgreSQL idéntico.',
         restart='Comparación de estado. Documenta en tu informe si reiniciaste servicios, recreaste contenedores o reiniciaste Docker Desktop; este script no lo demuestra por sí solo.'))
print(json.dumps(dict(phase=a.phase, canonical_rows=state['canonical_rows'], files=len(state['files']), table_counts={k:len(v) for k,v in state['tables'].items()})))
