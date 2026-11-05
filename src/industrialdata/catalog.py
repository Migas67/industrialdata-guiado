import json
import os
from pathlib import Path
from .common import dump, now


def connection():
    import psycopg
    return psycopg.connect(connect_timeout=10)


def initialize():
    with connection() as conn:
        conn.execute((Path(__file__).resolve().parents[2]/'sql/001_schema.sql').read_text())


def save_catalog(data, folder, offline=False):
    # El JSON es una instantánea explícita para tests sin PostgreSQL.
    p = folder/'catalog.json'
    if p.exists() and json.loads(p.read_text(encoding='utf-8')) != data:
        raise ValueError('El catálogo existente difiere; utilice otro DATA_ROOT para un experimento nuevo')
    if not offline:
        from psycopg.types.json import Jsonb
        with connection() as conn:
            for m in data['machines']:
                conn.execute('INSERT INTO machines VALUES (%s,%s,%s) ON CONFLICT(machine_id) DO UPDATE SET machine_type=excluded.machine_type, location=excluded.location', tuple(m.values()))
            for s in data['sensors']:
                conn.execute('INSERT INTO sensors VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(sensor_id) DO UPDATE SET expected_period_s=excluded.expected_period_s,operational_min=excluded.operational_min,operational_max=excluded.operational_max', tuple(s.values()))
            for k in ['version','start','end','windows','idle_kw']:
                conn.execute('INSERT INTO catalog_settings VALUES (%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (k,Jsonb(data[k])))
    if not p.exists():
        dump(p,data)


def load_catalog(folder, offline=False):
    if offline:
        return json.loads((folder/'catalog.json').read_text(encoding='utf-8'))
    from psycopg.rows import dict_row
    with connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            machines = cur.execute('SELECT * FROM machines ORDER BY machine_id').fetchall()
            sensors = cur.execute('SELECT * FROM sensors ORDER BY sensor_id').fetchall()
            settings = cur.execute('SELECT * FROM catalog_settings').fetchall()
    return dict(machines=machines,sensors=sensors,**{r['key']:r['value'] for r in settings})


def log_run(run_id, started, status, summary=None, error=None, offline=False):
    if offline:
        return
    from psycopg.types.json import Jsonb
    with connection() as conn:
        conn.execute('INSERT INTO runs VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(run_id) DO UPDATE SET finished_at=excluded.finished_at,status=excluded.status,summary=excluded.summary,error=excluded.error',
                     (run_id,started,None if status=='running' else now(),status,Jsonb(summary) if summary else None,error))
