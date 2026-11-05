"""Generador determinista. Nunca sobrescribe un fichero original diferente."""
import argparse
import csv
import json
import random
import shutil
from datetime import timedelta
from pathlib import Path
from .common import root, timestamp, iso, dump, sha, identity
from .catalog import save_catalog


def generate(folder, seed=42, machines=6, minutes=1440, offline=False):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    if machines<6 or minutes<420:
        raise ValueError('El escenario de referencia requiere al menos 6 máquinas y 420 minutos')
    start=timestamp('2026-01-12T00:00:00Z'); end=start+timedelta(minutes=minutes)
    at=lambda m: iso(start+timedelta(minutes=m))
    machine_rows=[]; sensors=[]
    for i in range(1,machines+1):
        mid=f'M{i:02}'; kind=['motor','bomba','compresor'][(i-1)//2%3]
        machine_rows.append(dict(machine_id=mid,machine_type=kind,location=f'L{(i-1)//6+1:02}'))
        definitions=[('temperature','°C',0,80,-40,200),('vibration','mm/s',0,5,0,100),('power','kW',0,10,0,100)]
        if kind!='motor': definitions.append(('pressure','bar',1,9,0,50))
        for v,u,lo,hi,pl,ph in definitions:
            sensors.append(dict(sensor_id=f'{mid}_{v}',machine_id=mid,variable=v,unit=u,expected_period_s=60,operational_min=lo,operational_max=hi,physical_min=pl,physical_max=ph))
    catalog=dict(machines=machine_rows,sensors=sensors,version='1.0',start=at(0),end=at(minutes),idle_kw=0.1,
                 windows=[dict(machine_id=m['machine_id'],start_utc=at(0),end_utc=at(minutes)) for m in machine_rows])
    save_catalog(catalog,folder,offline)
    stage=folder/'generation_tmp'
    if stage.exists():
        raise ValueError('generation_tmp ya existe; revise la generación interrumpida antes de reintentar')
    stage.mkdir(); raw=stage/'raw';raw.mkdir();late=stage/'late';late.mkdir()
    rng=random.Random(seed)
    first=None
    with (raw/'telemetry_001.jsonl').open('w',encoding='utf-8',newline='\n') as f, (late/'telemetry_002.jsonl').open('w',encoding='utf-8',newline='\n') as lf:
        for minute in range(minutes+1):
            for s in sensors:
                mid=s['machine_id'];v=s['variable']
                value={'temperature':50,'vibration':2,'power':2,'pressure':5}[v]+rng.uniform(-0.05,0.05)
                if mid=='M01' and v=='temperature' and 60<=minute<65: value=90
                if mid=='M02' and v=='vibration' and 120<=minute<123: value=8
                if v=='power' and ((mid=='M05' and 300<=minute<310) or (mid=='M06' and 360<=minute<370)): value=0
                if mid=='M03' and v=='temperature' and 180<=minute<190: continue
                row=dict(event_id=identity(seed,s['sensor_id'],minute),sensor_id=s['sensor_id'],machine_id=mid,timestamp_utc=at(minute),variable=v,value=round(value,4),unit=s['unit'],ingested_at_utc=at(minute+1))
                if first is None:first=row.copy()
                if mid=='M01' and v=='temperature' and minute==30:
                    row['ingested_at_utc']=at(minutes+60)
                    lf.write(json.dumps(row,ensure_ascii=False)+'\n')
                else:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        # S01: duplicado; S08: misma clave con un valor contradictorio.
        f.write(json.dumps(first,ensure_ascii=False)+'\n')
        bad=first|dict(event_id='conflict_001',value=70)
        f.write(json.dumps(bad,ensure_ascii=False)+'\n')
        for changes in [dict(event_id='bad_date',timestamp_utc='fecha inválida'),dict(event_id='bad_unit',unit='unknown'),dict(event_id='bad_machine',machine_id='M999')]:
            f.write(json.dumps(first|changes,ensure_ascii=False)+'\n')
        f.write('{broken json\n')
    with (raw/'production.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['production_id','machine_id','start_utc','end_utc','product_id','units_ok','units_rejected'])
        for m in machine_rows:
            mid=m['machine_id']
            for minute in range(minutes):
                zero=(mid=='M04' and 240<=minute<250) or (mid=='M05' and 300<=minute<310) or (mid=='M06' and 360<=minute<370)
                w.writerow([f'{mid}_{minute}',mid,at(minute),at(minute+1),'P01',0 if zero else 2,0 if zero else int(minute%100==0)])
    with (raw/'maintenance.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['maintenance_id','machine_id','start_utc','end_utc','planned','intervention_type'])
        w.writerow(['MT01','M05',at(300),at(310),'true','inspeccion_programada'])
        w.writerow(['MT02','M06',at(370),at(380),'false','revision_posterior'])
    expected=[dict(machine_id=m,rule=r,start_utc=at(a),end_utc=at(b)) for m,r,a,b in [
        ('M03','missing_temperature',180,190),('M01','temperature_high',60,65),('M02','vibration_high',120,123),
        ('M04','idle_consumption',240,250),('M05','planned_stop',300,310),('M06','unplanned_stop',360,370)]]
    dump(stage/'escenarios_esperados.json',expected)
    manifest=dict(seed=seed,machines=machines,minutes=minutes,start=at(0),end=at(minutes),schema_version='1.0',files=[])
    for p in sorted(stage.rglob('*')):
        if p.is_file():
            with p.open(encoding='utf-8') as f:n=sum(1 for _ in f)
            manifest['files'].append(dict(path=p.relative_to(stage).as_posix(),sha256=sha(p),physical_lines=n))
    dump(stage/'manifest.json',manifest)
    # Publicación conservadora: mismo contenido permitido; diferente contenido rechazado.
    for p in stage.rglob('*'):
        if p.is_file():
            dst=folder/p.relative_to(stage)
            if dst.exists() and sha(dst)!=sha(p):
                raise ValueError(f'No se sobrescribe {dst}; use otro DATA_ROOT')
    for p in stage.rglob('*'):
        if p.is_file():
            dst=folder/p.relative_to(stage);dst.parent.mkdir(parents=True,exist_ok=True)
            if not dst.exists():shutil.copyfile(p,dst)
    # Solo se limpia el directorio temporal creado por esta función.
    shutil.rmtree(stage)
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=42);p.add_argument('--scenario',choices=['demo'],default='demo')
    p.add_argument('--machines',type=int,default=6);p.add_argument('--minutes',type=int,default=1440);p.add_argument('--offline',action='store_true')
    p.add_argument('--output',type=Path,default=None)
    a=p.parse_args();print(json.dumps(generate(a.output or root(),a.seed,a.machines,a.minutes,a.offline),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
