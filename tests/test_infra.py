import json
from pathlib import Path
import pytest
from industrialdata.generate import generate
from industrialdata.common import sha
from industrialdata.catalog import connection

pytestmark=pytest.mark.infra

def test_generator_reproducible(tmp_path):
    for name in ['a','b']:generate(tmp_path/name,minutes=420,offline=True)
    for name in ['raw/telemetry_001.jsonl','raw/production.csv','raw/maintenance.csv','manifest.json']:
        assert sha(tmp_path/'a'/name)==sha(tmp_path/'b'/name)

def test_catalog_and_scenarios(tmp_path):
    generate(tmp_path,minutes=420,offline=True)
    catalog=json.loads((tmp_path/'catalog.json').read_text())
    assert len(catalog['machines'])==6
    assert len(catalog['sensors'])==22
    assert len(json.loads((tmp_path/'escenarios_esperados.json').read_text()))==6

def test_postgres():
    with connection() as conn:
        assert conn.execute('SELECT 1').fetchone()[0]==1
        assert conn.execute("SELECT to_regclass('machines')").fetchone()[0]=='machines'

def test_empty_dashboard(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('DATA_ROOT',str(tmp_path))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py')).run(timeout=30)
    assert not at.exception
    assert 'Todavía no hay resultados' in at.info[0].value
