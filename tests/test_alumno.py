from datetime import timedelta
import pytest
import pandas as pd
from industrialdata import alumno as a
from industrialdata.common import timestamp
from industrialdata.experimentos import pandas_agregar
pytestmark=pytest.mark.alumno

def sample():
    sensor=dict(machine_id='M01',variable='temperature',unit='°C',expected_period_s=60,physical_min=-40,physical_max=200)
    catalog=dict(start='2026-01-01T00:00:00Z',end='2026-01-01T01:00:00Z')
    row=dict(machine_id='M01',variable='temperature',unit='°C',timestamp_utc='2026-01-01T01:01:00+01:00',ingested_at_utc='2026-01-01T00:02:00Z',value=90)
    return row,sensor,catalog

def test_A1_valid_high_temperature():
    row,s,c=sample();original=row.copy();out=a.normalizar(row,s,c)
    assert out['timestamp_utc']=='2026-01-01T00:01:00Z'
    assert out['value']==90 and row==original

@pytest.mark.parametrize('change',[{'unit':'K'},{'machine_id':'M999'},{'value':True},{'value':float('nan')},{'timestamp_utc':'2026-01-01T00:00:30Z'}])
def test_A1_invalid(change):
    row,s,c=sample()
    with pytest.raises(ValueError):a.normalizar(row|change,s,c)

def test_A2_duplicates_and_conflicts():
    row,_,_=sample()
    assert a.clasificar(row,None)=='new'
    assert a.clasificar(row,row.copy())=='duplicate'
    with pytest.raises(ValueError,match='conflicting_value'):a.clasificar(row,row|{'value':80})
    with pytest.raises(ValueError,match='event_id_collision'):a.clasificar(row,None,True)

def test_A3_threshold():
    assert a.superaciones([79,80,81],80)==[False,False,True]

def test_A4_unknown_is_not_stop():
    flags=a.estados([False,True,True,True],[0,2,0,.1],[False,False,True,False],.1)
    assert flags=={'idle_consumption':[False,True,False,False],
                   'planned_stop':[False,False,True,False],
                   'unplanned_stop':[False,False,False,True]}

def test_A5_constant_and_gap():
    start=timestamp('2026-01-01T00:00:00Z'); times=[start+timedelta(minutes=i) for i in range(6)]
    assert a.energia(times,[6]*6,start,times[-1])==pytest.approx((.5,300))
    assert a.energia([times[0],times[3]],[6,6],start,times[-1])==(0,0)
    assert a.energia([start],[6],start,times[-1])==(0,0)

@pytest.mark.parametrize('args,expected',[((.5,10,1,1,False),.05),((.5,0,1,1,False),None),((.5,10,.5,1,False),None),((.5,10,1,.5,False),None),((.5,10,1,1,True),None)])
def test_A6_denominators(args,expected):
    assert a.intensidad(*args)==expected

def test_A7_pandas():
    df=pd.DataFrame([dict(machine_id='M01',timestamp_utc='2026-01-01T00:00:00Z',variable='power',value=2),dict(machine_id='M01',timestamp_utc='2026-01-01T00:01:00Z',variable='power',value=4),dict(machine_id='M01',timestamp_utc='2026-01-01T00:02:00Z',variable='temperature',value=90)])
    assert pandas_agregar(df).to_dict('records')==[dict(machine_id='M01',hour='2026-01-01 00:00:00',mean_power=3.0,n=2)]
