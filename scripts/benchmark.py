"""Tres repeticiones por formato. Mide RSS en un proceso hijo independiente."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import pandas as pd
import psutil
from industrialdata.common import root,dump
from industrialdata.run import current_snapshot

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',choices=['csv','parquet']);p.add_argument('--path');p.add_argument('--result')
    a=p.parse_args()
    if a.worker:
        t=time.perf_counter();df=pd.read_csv(a.path) if a.worker=='csv' else pd.read_parquet(a.path)
        result=df.groupby(['machine_id','variable']).value.agg(['mean','count']).reset_index().sort_values(['machine_id','variable'])
        dump(a.result,dict(seconds=time.perf_counter()-t,rows=len(df),records=result.to_dict('records')));return
    folder=root();snap=current_snapshot(folder)
    if not snap:raise RuntimeError('Ejecute el pipeline')
    source=snap/'silver/telemetry.parquet';csv=folder/'reports/benchmark_telemetry.csv';csv.parent.mkdir(exist_ok=True)
    pd.read_parquet(source).to_csv(csv,index=False)
    runs=[];reference=None
    with tempfile.TemporaryDirectory(prefix='benchmark_', dir=folder/'reports') as tmp:
        for fmt,path in [('csv',csv),('parquet',source)]:
            for repeat in range(3):
                output=Path(tmp)/f'{fmt}_{repeat}.json'
                child=subprocess.Popen([sys.executable,__file__,'--worker',fmt,'--path',str(path),'--result',str(output)])
                process=psutil.Process(child.pid);peak=0
                while child.poll() is None:
                    try:peak=max(peak,process.memory_info().rss)
                    except psutil.Error:pass
                    time.sleep(.02)
                if child.returncode:raise RuntimeError('Falló el benchmark')
                r=json.loads(output.read_text());actual=pd.DataFrame(r.pop('records'))
                if reference is None:reference=actual
                else:pd.testing.assert_frame_equal(reference,actual,check_dtype=False,atol=1e-9,rtol=1e-9)
                runs.append(dict(format=fmt,repeat=repeat+1,bytes=path.stat().st_size,peak_rss_bytes=peak,**r))
    medians=pd.DataFrame(runs).groupby('format')[['seconds','peak_rss_bytes','bytes']].median().reset_index().to_dict('records')
    out=dict(runs=runs,medians=medians,method='Subproceso nuevo por repetición; RSS muestreada cada 20ms; caché de sistema no vaciada; tiempo lectura+agregación excluye importaciones. RSS incluye Python y bibliotecas.',python=sys.version)
    dump(folder/'reports/format_benchmark.json',out);print(json.dumps(out,indent=2))

if __name__=='__main__':main()
