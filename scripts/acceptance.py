"""Comprobación pública de escenarios del simulador sobre un DATA_ROOT nuevo."""
import json
import os
import shutil
from industrialdata.common import root,dump
from industrialdata.generate import generate
from industrialdata.run import execute,current_snapshot
import pandas as pd

folder=root()
if (folder/'current.json').exists():raise RuntimeError('Utilice un DATA_ROOT nuevo para esta prueba de aceptación')
offline=os.environ.get('OFFLINE_TEST')=='1'
generate(folder,offline=offline)
a=execute(folder,offline=offline);snap=current_snapshot(folder)
expected=json.loads((folder/'escenarios_esperados.json').read_text())
actual=pd.read_parquet(snap/'gold/episodes.parquet')
assert len(actual)==len(expected)==6
for e in expected:
    rows=actual[(actual.machine_id==e['machine_id'])&(actual.rule==e['rule'])]
    assert len(rows)==1 and rows.iloc[0].start_utc==e['start_utc'] and rows.iloc[0].end_utc==e['end_utc']
b=execute(folder,offline=offline)
assert b['accepted_new']==0 and b['canonical_rows']==a['canonical_rows']
shutil.copyfile(folder/'late/telemetry_002.jsonl',folder/'raw/telemetry_002.jsonl')
c=execute(folder,offline=offline)
assert c['accepted_new']==1
out=dict(initial=a,replay=b,late=c,expected_episodes=expected,checks='Escenarios, repetición y lote tardío superados')
dump(folder/'reports/acceptance.json',out);print(json.dumps(out,indent=2))
