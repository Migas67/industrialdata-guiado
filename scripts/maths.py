"""Evidencia RA1a: conjuntos, relaciones y complejidad con preparación incluida."""
import json
import statistics
import time
from industrialdata.common import root,dump

def scan_list(values):
    seen=[];duplicates=set()
    for v in values:
        if v in seen:duplicates.add(v)
        else:seen.append(v)
    return duplicates

def scan_set(values):
    seen=set();duplicates=set()
    for v in values:
        if v in seen:duplicates.add(v)
        else:seen.add(v)
    return duplicates

rows=[]
for n in [1000,5000,10000]:
    data=list(range(n))+list(range(n//10))
    assert scan_list(data)==scan_set(data)==set(range(n//10))
    for name,fn in [('list',scan_list),('set',scan_set)]:
        times=[]
        for _ in range(3):
            t=time.perf_counter();fn(data);times.append(time.perf_counter()-t)
        rows.append(dict(method=name,n=len(data),seconds=times,median_s=statistics.median(times)))
out=dict(results=rows,interpretation='PENDIENTE: explica complejidad temporal y espacial y límites de las mediciones.')
dump(root()/'reports/complexity.json',out);print(json.dumps(out,indent=2))
