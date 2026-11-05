import json
import shutil
from datetime import timedelta
from pathlib import Path
import pandas as pd
import pytest
from fastavro import reader
from industrialdata.common import timestamp,sha
from industrialdata.generate import generate
from industrialdata.run import execute,current_snapshot
from industrialdata.analyze import energy_segments,episodes_from_flags,analyze
from industrialdata.ingest import ingest,business_tables

pytestmark = pytest.mark.integracion


def test_generator_deterministic(tmp_path):
    for name in ['a','b']:generate(tmp_path/name,minutes=420,offline=True)
    for name in ['raw/telemetry_001.jsonl','raw/production.csv','raw/maintenance.csv','manifest.json']:
        assert sha(tmp_path/'a'/name)==sha(tmp_path/'b'/name)


def test_expected_episodes(demo):
    folder,_,snap=demo
    expected=json.loads((folder/'escenarios_esperados.json').read_text())
    actual=pd.read_parquet(snap/'gold/episodes.parquet').to_dict('records')
    assert len(actual)==6
    for e in expected:
        found=[a for a in actual if a['machine_id']==e['machine_id'] and a['rule']==e['rule']]
        assert len(found)==1
        assert found[0]['start_utc']==e['start_utc']
        assert found[0]['end_utc']==e['end_utc']


def test_quality_counts(demo):
    _,r,s=demo
    assert r['input']==r['accepted_new']+r['duplicates']+r['rejected']
    assert r['duplicates']==1 and r['rejected']==5
    assert r['canonical_rows']==22*421-11
    q=pd.read_parquet(s/'gold/quality.parquet').set_index('sensor_id')
    assert q.loc['M03_temperature','missing']==10
    assert q.loc['M01_temperature','missing']==1
    assert q.loc['M01_power','coverage']==1


def test_idempotence_and_late(tmp_path):
    generate(tmp_path,minutes=420,offline=True)
    r1=execute(tmp_path,offline=True);s1=current_snapshot(tmp_path)
    e1=pd.read_parquet(s1/'gold/episodes.parquet')
    r2=execute(tmp_path,offline=True)
    assert r2['accepted_new']==0 and r2['canonical_rows']==r1['canonical_rows']
    pd.testing.assert_frame_equal(e1,pd.read_parquet(current_snapshot(tmp_path)/'gold/episodes.parquet'))
    shutil.copyfile(tmp_path/'late/telemetry_002.jsonl',tmp_path/'raw/telemetry_002.jsonl')
    r3=execute(tmp_path,offline=True)
    assert r3['accepted_new']==1 and r3['canonical_rows']==r1['canonical_rows']+1
    q=pd.read_parquet(current_snapshot(tmp_path)/'gold/quality.parquet').set_index('sensor_id')
    assert q.loc['M01_temperature','missing']==0
    assert r3['episodes']==6


def test_constant_power_and_gap():
    a=timestamp('2026-01-01T00:00:00Z');times=[a+timedelta(minutes=i) for i in range(31)]
    assert energy_segments(times,[2]*31,a,times[-1])==pytest.approx((1,1800))
    kept=times[:10]+times[20:]
    assert energy_segments(kept,[2]*len(kept),a,times[-1])==pytest.approx((19/30,1140))


def test_gap_interrupts_consecutive():
    a=timestamp('2026-01-01T00:00:00Z');times=[a+timedelta(minutes=i) for i in [0,1,2,10,11]]
    assert not episodes_from_flags(times,[True]*5,60,'M','S','high',5)


def test_no_future_extrapolation():
    a=timestamp('2026-01-01T00:00:00Z')
    assert energy_segments([a],[100],a,a+timedelta(hours=1))==(0,0)


def test_failed_run_keeps_pointer(tmp_path):
    generate(tmp_path,minutes=420,offline=True);execute(tmp_path,offline=True)
    old=(tmp_path/'current.json').read_bytes()
    # Cambiar una fuente ya consolidada debe fallar antes de publicar.
    (tmp_path/'raw/production.csv').write_text('incorrecto\n',encoding='utf-8')
    with pytest.raises(ValueError,match='Fuente original'):execute(tmp_path,offline=True)
    assert (tmp_path/'current.json').read_bytes()==old
    assert any(json.loads(p.read_text())['status']=='failed' for p in (tmp_path/'reports').glob('*.json'))
    assert not (tmp_path/'pipeline.lock').exists()


def test_invalid_business_schema(tmp_path):
    generate(tmp_path,minutes=420,offline=True)
    (tmp_path/'raw/production.csv').write_text('invalid\n',encoding='utf-8')
    with pytest.raises(ValueError,match='esquema'):execute(tmp_path,offline=True)
    assert not (tmp_path/'current.json').exists()


def test_avro_parquet_roundtrip(demo):
    _,_,snap=demo
    with (snap/'gold/episodes.avro').open('rb') as f:rows=list(reader(f))
    parquet=pd.read_parquet(snap/'gold/episodes.parquet')
    assert {r['episode_id'] for r in rows}==set(parquet.episode_id)
    assert all(r['note'] is None for r in rows)


def test_join_totals_and_rejections(demo):
    _,_,snap=demo
    p=pd.read_parquet(snap/'silver/production.parquet');m=pd.read_parquet(snap/'gold/metrics.parquet')
    assert p.units_ok.sum()==m.units_ok.sum()
    assert p.units_rejected.sum()==m.units_rejected.sum()
    rej=json.loads((snap/'quarantine/rejections.json').read_text())
    assert any(r['reason']=='invalid_machine_id' for r in rej)
    assert any(r['reason']=='conflicting_value' for r in rej)


def test_zero_and_missing_production(demo):
    folder,_,snap=demo;c=json.loads((folder/'catalog.json').read_text())
    t=pd.read_parquet(snap/'silver/telemetry.parquet');p=pd.read_parquet(snap/'silver/production.parquet');mt=pd.read_parquet(snap/'silver/maintenance.parquet')
    p.loc[p.machine_id=='M04',['units_ok','units_rejected']]=0
    _,_,m=analyze(t,p,mt,c)
    assert m[m.machine_id=='M04'].kwh_per_good_unit.isna().all()
    p=p[p.machine_id!='M04']
    e,_,m=analyze(t,p,mt,c)
    assert not (e.machine_id=='M04').any()
    assert m[m.machine_id=='M04'].kwh_per_good_unit.isna().all()


def test_detector_independent_of_expected(demo):
    folder,_,snap=demo
    source=Path(__file__).resolve().parents[1]/'src/industrialdata/analyze.py'
    assert 'escenarios_esperados' not in source.read_text(encoding='utf-8')


def test_no_mutation_of_originals(demo):
    folder,_,_=demo
    manifest=json.loads((folder/'manifest.json').read_text())
    assert all(sha(folder/r['path'])==r['sha256'] for r in manifest['files'])


def test_timezone_required():
    with pytest.raises(ValueError,match='timezone'):timestamp('2026-01-01T00:00:00')


def test_conflicting_event_id(demo,tmp_path):
    folder,_,snap=demo;c=json.loads((folder/'catalog.json').read_text())
    previous=pd.read_parquet(snap/'silver/telemetry.parquet')
    row=previous.iloc[0].to_dict();row['timestamp_utc']='2026-01-12T06:59:00Z'
    (tmp_path/'telemetry_collision.jsonl').write_text(json.dumps(row)+'\n',encoding='utf-8')
    _,s,rejects,_=ingest(tmp_path,c,'test',previous)
    assert s['rejected']==1 and rejects[0]['reason']=='event_id_collision'
