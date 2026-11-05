"""Comparación pequeña y verificable; Spark local, no un clúster distribuido."""
import json
import os
import time
from pathlib import Path
import pandas as pd
from pyspark.sql import SparkSession,functions as F
from industrialdata.common import root,dump
from industrialdata.run import current_snapshot
from industrialdata.experimentos import pandas_agregar,spark_agregar

folder=root();snap=current_snapshot(folder)
if not snap:raise RuntimeError('Ejecute primero el pipeline')
path=snap/'silver/telemetry.parquet'
t=time.perf_counter();spark=SparkSession.builder.master('local[2]').appName('IndustrialData-Comparacion').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','4').config('spark.ui.enabled','false').getOrCreate();startup=time.perf_counter()-t
results=[]
try:
    for repeat in range(3):
        t=time.perf_counter()
        df=pd.read_parquet(path)
        expected=pandas_agregar(df)
        pandas_s=time.perf_counter()-t
        t=time.perf_counter()
        actual=spark_agregar(spark.read.parquet(str(path)))
        spark_s=time.perf_counter()-t
        pd.testing.assert_frame_equal(expected,actual,check_dtype=False,rtol=1e-9,atol=1e-9)
        results.append(dict(repeat=repeat+1,pandas_s=pandas_s,spark_s=spark_s,rows=len(df),groups=len(actual)))
    out=dict(mode='Spark local[2]',spark_version=spark.version,startup_s=startup,tolerance='rtol=atol=1e-9',equivalent=True,runs=results,
             caveat='Proceso único, lecturas repetidas sin vaciar caché del sistema; no inferir ventaja distribuida.')
    dump(folder/'reports/spark_comparison.json',out);print(json.dumps(out,indent=2))
finally:spark.stop()
