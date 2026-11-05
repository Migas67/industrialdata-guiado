import csv
import json
import math
from pathlib import Path
import pandas as pd
from .common import timestamp, iso, sha
from . import alumno

TELEMETRY=['event_id','sensor_id','machine_id','timestamp_utc','variable','value','unit','ingested_at_utc','source_file','source_line','source_sha256','first_run_id']


def ingest(raw,catalog,run_id,previous=None):
    """Primera observación aceptada prevalece. Estado anterior inmutable."""
    sensors={s['sensor_id']:s for s in catalog['sensors']}
    canonical={} if previous is None else {(r['sensor_id'],r['timestamp_utc']):r for r in previous.to_dict('records')}
    event_keys={r['event_id']:k for k,r in canonical.items()}
    stats=dict(input=0,accepted_new=0,duplicates=0,rejected=0)
    rejects=[];files=[]
    paths=sorted(Path(raw).glob('telemetry_*.jsonl'))
    if not paths:raise ValueError('No hay ficheros telemetry_*.jsonl')
    for p in paths:
        digest=sha(p);file_counts={k:0 for k in stats}
        with p.open(encoding='utf-8') as f:
            for line_no,line in enumerate(f,1):
                stats['input']+=1;file_counts['input']+=1
                try:
                    r=json.loads(line)
                    if not isinstance(r,dict):raise ValueError('object_required')
                    if not isinstance(r.get('event_id'),str) or not r['event_id']:raise ValueError('event_id_required')
                    s=sensors.get(r.get('sensor_id'))
                    if s is None:raise ValueError('unknown_sensor')
                    r=alumno.normalizar(r,s,catalog)
                    key=(r['sensor_id'],r['timestamp_utc'])
                    collision=r['event_id'] in event_keys and event_keys[r['event_id']]!=key
                    decision=alumno.clasificar(r,canonical.get(key),collision)
                    if decision not in ('new','duplicate'):raise ValueError('invalid_classification')
                    if decision=='duplicate':
                        stats['duplicates']+=1;file_counts['duplicates']+=1
                        continue
                    row={k:r[k] for k in TELEMETRY[:8]}
                    row.update(source_file=p.name,source_line=line_no,source_sha256=digest,first_run_id=run_id)
                    canonical[key]=row;event_keys[r['event_id']]=key
                    stats['accepted_new']+=1;file_counts['accepted_new']+=1
                except (ValueError,KeyError,TypeError,OverflowError) as ex:
                    stats['rejected']+=1;file_counts['rejected']+=1
                    rejects.append(dict(source_file=p.name,source_line=line_no,source_sha256=digest,reason=str(ex),raw=line.rstrip()))
        files.append(dict(source_file=p.name,sha256=digest,**file_counts))
    assert stats['input']==stats['accepted_new']+stats['duplicates']+stats['rejected']
    frame=pd.DataFrame(canonical.values(),columns=TELEMETRY).sort_values(['sensor_id','timestamp_utc']).reset_index(drop=True)
    return frame,stats,rejects,files


def business_tables(raw,catalog):
    """Los CSV empresariales inválidos abortan el lote; nunca se publica una mezcla parcial."""
    machines={m['machine_id'] for m in catalog['machines']}
    output=[]
    definitions=[('production.csv',['production_id','machine_id','start_utc','end_utc','product_id','units_ok','units_rejected']),
                 ('maintenance.csv',['maintenance_id','machine_id','start_utc','end_utc','planned','intervention_type'])]
    for name,cols in definitions:
        path=Path(raw)/name
        with path.open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=cols:raise ValueError(f'{name}: esquema incorrecto')
            rows=list(reader)
        ids=set(); digest=sha(path)
        for index,r in enumerate(rows,2):
            if r[cols[0]] in ids:raise ValueError(name+': duplicate_id')
            ids.add(r[cols[0]])
            if r['machine_id'] not in machines:raise ValueError(name+': unknown_machine')
            r['start_utc']=iso(timestamp(r['start_utc']))
            r['end_utc']=iso(timestamp(r['end_utc'])) if r['end_utc'] else catalog['end']
            if not catalog['start']<=r['start_utc']<r['end_utc']<=catalog['end']:raise ValueError(name+': invalid_interval')
            if name=='production.csv':
                for k in ['units_ok','units_rejected']:
                    r[k]=int(r[k])
                    if r[k]<0:raise ValueError('negative_units')
            else:
                if r['planned'] not in ['true','false']:raise ValueError('invalid_planned')
                r['planned']=r['planned']=='true'
            r.update(source_file=name,source_line=index,source_sha256=digest)
        df=pd.DataFrame(rows,columns=cols+['source_file','source_line','source_sha256'])
        if name=='production.csv':
            for _,group in df.sort_values('start_utc').groupby('machine_id'):
                if any(a>b for a,b in zip(group['end_utc'].iloc[:-1],group['start_utc'].iloc[1:])):raise ValueError('overlapping_production')
        output.append(df)
    return output
