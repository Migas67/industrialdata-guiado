"""Valida un perfil independiente sin modificar el catálogo PostgreSQL de la demo."""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import psutil
from fastavro import reader
from industrialdata.common import dump, root, sha
from industrialdata.run import current_snapshot

p = argparse.ArgumentParser()
p.add_argument('--minutes', type=int, required=True)
p.add_argument('--name', choices=['volume100k', 'volume1m'], required=True)
a = p.parse_args()
base = root(); folder = base/a.name
if (folder/'current.json').exists():
    raise RuntimeError('Este perfil ya tiene resultados. Conservarlos y elegir un DATA_ROOT nuevo.')
logs = base/'reports'; logs.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, DATA_ROOT=str(folder))
measurements = []
for phase, command in [
    ('generation', [sys.executable, '-m', 'industrialdata.generate', '--minutes', str(a.minutes), '--offline']),
    ('pipeline', [sys.executable, '-m', 'industrialdata.run', '--offline']),
]:
    start = time.perf_counter(); peak = 0
    with (logs/f'{a.name}_{phase}.log').open('w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        monitor = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                peak = max(peak, sum(x.memory_info().rss for x in [monitor]+monitor.children(recursive=True)))
            except psutil.Error:
                pass
            time.sleep(.05)
        code = process.wait()
    measurements.append(dict(phase=phase, seconds=time.perf_counter()-start, peak_rss_bytes=peak, exit_code=code))
    if code:
        dump(logs/f'{a.name}_failure.json', dict(measurements=measurements))
        raise RuntimeError(f'{phase} falló: consultar el log')
snap = current_snapshot(folder)
stats = json.loads((snap/'report.json').read_text())
telemetry = pd.read_parquet(snap/'silver/telemetry.parquet')
expected_count = 22*(a.minutes+1)-11
assert len(telemetry) == stats['canonical_rows'] == expected_count
assert not telemetry.duplicated(['sensor_id', 'timestamp_utc']).any()
episodes = pd.read_parquet(snap/'gold/episodes.parquet')
expected = json.loads((folder/'escenarios_esperados.json').read_text())
assert len(episodes) == len(expected) == 6
for e in expected:
    match = episodes[(episodes.machine_id == e['machine_id']) & (episodes.rule == e['rule'])]
    assert len(match) == 1
    assert match.iloc[0].start_utc == e['start_utc'] and match.iloc[0].end_utc == e['end_utc']
for item in json.loads((folder/'manifest.json').read_text())['files']:
    assert sha(folder/item['path']) == item['sha256']
avros = list(snap.rglob('*.avro'))
assert avros
with avros[0].open('rb') as f:
    assert len(list(reader(f))) == 6
out = dict(profile=a.name, minutes=a.minutes, mode='Catálogo JSON offline aislado',
           environment=dict(system=platform.system(), python=platform.python_version(), docker=Path('/.dockerenv').exists()),
           passed=True, canonical_rows=len(telemetry), expected_rows=expected_count, episodes=6,
           measurements=measurements, pipeline=stats,
           checks=['Conteo exacto', 'Unicidad sensor/instante', 'Seis episodios y límites temporales',
                   'Fuentes originales SHA256 intactas', 'Avro legible con seis episodios'],
           snapshot_bytes=sum(x.stat().st_size for x in snap.rglob('*') if x.is_file()),
           caveat='RSS del proceso y descendientes muestreada cada 50 ms; no incluye motor Docker ni caché de disco. Sin vaciar caché. Procesamiento completo en memoria.')
dump(logs/f'{a.name}.json', out)
print(json.dumps(out, indent=2))
