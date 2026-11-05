import argparse
import json
import os
import uuid
from pathlib import Path
from contextlib import contextmanager
import pandas as pd
from fastavro import writer,reader
from .common import root,now,dump,sha
from .catalog import load_catalog,log_run
from .ingest import ingest,business_tables
from .analyze import analyze

AVRO_SCHEMA={'type':'record','name':'Incident','fields':[
    {'name':k,'type':'string'} for k in ['episode_id','machine_id','sensor_id','rule','start_utc','end_utc']
]+[{'name':'duration_s','type':'double'},{'name':'note','type':['null','string'],'default':None}]}


@contextmanager
def lock(folder):
    path=folder/'pipeline.lock'
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Existe pipeline.lock; compruebe si hay una ejecución activa antes de retirarlo')
    try:
        with os.fdopen(fd,'w') as f:f.write(str(os.getpid()))
        yield
    finally:path.unlink()


def current_snapshot(folder):
    pointer=Path(folder)/'current.json'
    if not pointer.exists():return None
    return Path(folder)/json.loads(pointer.read_text())['snapshot']


def execute(folder,raw=None,offline=False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);raw=Path(raw or folder/'raw')
    with lock(folder):
        run_id=uuid.uuid4().hex;started=now();snapshot=folder/'snapshots'/run_id
        try:
            log_run(run_id,started,'running',offline=offline)
            catalog=load_catalog(folder,offline)
            prev=current_snapshot(folder)
            previous=pd.read_parquet(prev/'silver/telemetry.parquet') if prev else None
            if prev:
                previous_catalog=json.loads((prev/'catalog.json').read_text(encoding='utf-8'))
                if previous_catalog!=catalog:raise ValueError('El catálogo ha cambiado: use un DATA_ROOT nuevo para reprocesar con nueva versión')
            # Manifiestos anteriores impiden modificar silenciosamente las fuentes ya aceptadas.
            if prev:
                old=json.loads((prev/'sources.json').read_text())
                for name,digest in old.items():
                    if not (raw/name).exists() or sha(raw/name)!=digest:raise ValueError('Fuente original modificada o ausente: '+name)
            production,maintenance=business_tables(raw,catalog)
            telemetry,stats,rejects,files=ingest(raw,catalog,run_id,previous)
            if stats['accepted_new']==0 and previous is None:raise ValueError('No hay observaciones válidas')
            episodes,quality,metrics=analyze(telemetry,production,maintenance,catalog)
            for name,frame in [('silver/telemetry',telemetry),('silver/production',production),('silver/maintenance',maintenance),('gold/episodes',episodes),('gold/quality',quality),('gold/metrics',metrics)]:
                path=snapshot/(name+'.parquet');path.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(path,index=False)
                assert len(pd.read_parquet(path))==len(frame)
            dump(snapshot/'quarantine/rejections.json',rejects);dump(snapshot/'files.json',files);dump(snapshot/'catalog.json',catalog)
            sources={p.name:sha(p) for p in raw.iterdir() if p.is_file() and (p.name.startswith('telemetry_') or p.name in ['production.csv','maintenance.csv'])}
            dump(snapshot/'sources.json',sources)
            with (snapshot/'gold/episodes.avro').open('wb') as f:
                writer(f,AVRO_SCHEMA,[{**{k:r[k] for k in ['episode_id','machine_id','sensor_id','rule','start_utc','end_utc','duration_s']},'note':None} for r in episodes.to_dict('records')])
            with (snapshot/'gold/episodes.avro').open('rb') as f:assert len(list(reader(f)))==len(episodes)
            stats.update(run_id=run_id,started_at=started,finished_at=now(),canonical_rows=len(telemetry),episodes=len(episodes),catalog_source='JSON offline de pruebas' if offline else 'PostgreSQL',status='success')
            dump(snapshot/'report.json',stats)
            # La instantánea está completa. El puntero se sustituye atómicamente en el mismo volumen.
            # ready en SQL no equivale a visible: current.json es la autoridad para publicación.
            log_run(run_id,started,'ready',stats,offline=offline)
            pointer=folder/'current.next.json';dump(pointer,dict(snapshot=f'snapshots/{run_id}',run_id=run_id))
            os.replace(pointer,folder/'current.json')
            dump(folder/'reports'/(run_id+'.json'),stats)
            try:log_run(run_id,started,'success',stats,offline=offline)
            except Exception as ex:dump(folder/'reports'/(run_id+'_audit_warning.json'),dict(error=str(ex),published=True))
            return stats
        except Exception as ex:
            failure=dict(run_id=run_id,started_at=started,finished_at=now(),status='failed',error=str(ex))
            dump(folder/'reports'/(run_id+'.json'),failure)
            try:log_run(run_id,started,'failed',error=str(ex),offline=offline)
            except Exception:pass
            raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path);p.add_argument('--offline',action='store_true')
    a=p.parse_args()
    try: result=execute(root(),a.input,a.offline)
    except NotImplementedError as ex:
        p.exit(2, str(ex)+'\nConsulta docs/GUIA.md y completa src/industrialdata/alumno.py.\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
