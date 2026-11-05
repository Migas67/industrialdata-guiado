"""Reglas deterministas y agregados. Nunca importa los escenarios esperados."""
from datetime import timedelta
import pandas as pd
from .common import timestamp,iso,identity
from . import alumno

EPISODES=['episode_id','machine_id','sensor_id','rule','start_utc','end_utc','duration_s','samples','severity','evidence']


def episodes_from_flags(times, flags, cadence, machine, sensor, rule, minimum):
    episodes=[]; active=[]
    def close():
        if len(active)>=minimum:
            a=active[0];b=active[-1]+timedelta(seconds=cadence)
            episodes.append(dict(episode_id=identity(machine,sensor,rule,iso(a)),machine_id=machine,sensor_id=sensor,rule=rule,
                start_utc=iso(a),end_utc=iso(b),duration_s=(b-a).total_seconds(),samples=len(active),severity='didactica',evidence=f'{len(active)} muestras; cadencia {cadence}s'))
        active.clear()
    for dt,flag in zip(times,flags):
        if active and (dt-active[-1]).total_seconds()>1.5*cadence:close()
        if flag:active.append(dt)
        else:close()
    close()
    return episodes


def energy_segments(times, values, start, end, cadence=60):
    return alumno.energia(times,values,start,end,cadence)


def analyze(telemetry,production,maintenance,catalog):
    start=timestamp(catalog['start']);end=timestamp(catalog['end'])
    t=telemetry.copy();t['dt']=pd.to_datetime(t.timestamp_utc,utc=True)
    prod=production.copy();prod['a']=pd.to_datetime(prod.start_utc,utc=True);prod['b']=pd.to_datetime(prod.end_utc,utc=True)
    maint=maintenance.copy();maint['a']=pd.to_datetime(maint.start_utc,utc=True);maint['b']=pd.to_datetime(maint.end_utc,utc=True)
    sensor_map={s['sensor_id']:s for s in catalog['sensors']}
    groups={k:g.sort_values('dt') for k,g in t.groupby('sensor_id')}
    episodes=[];quality=[];metrics=[]
    for sid,s in sensor_map.items():
        g=groups.get(sid,t.iloc[:0]);period=s['expected_period_s']
        grid=pd.date_range(start,end,freq=f'{period}s',inclusive='left')
        present=set(g.loc[g.dt<end,'dt']);flags=[dt not in present for dt in grid]
        quality.append(dict(sensor_id=sid,machine_id=s['machine_id'],variable=s['variable'],expected=len(grid),present=len(present),missing=sum(flags),coverage=len(present)/len(grid)))
        episodes+=episodes_from_flags(grid,flags,period,s['machine_id'],sid,'missing_'+s['variable'],10)
        if s['variable'] in ['temperature','vibration']:
            valid=g[g.dt<end]
            episodes+=episodes_from_flags(list(valid.dt),alumno.superaciones(list(valid.value),s['operational_max']),period,s['machine_id'],sid,s['variable']+'_high',5 if s['variable']=='temperature' else 3)
    for m in catalog['machines']:
        mid=m['machine_id'];sid=mid+'_power';s=sensor_map[sid];cadence=s['expected_period_s']
        power=groups.get(sid,t.iloc[:0]);pg=prod[prod.machine_id==mid].sort_values('a');mg=maint[maint.machine_id==mid]
        # Por intervalos no solapados: searchsorted evita productos cartesianos.
        pstarts=list(pg.a);pends=list(pg.b);punits=list(pg.units_ok+pg.units_rejected)
        planned_intervals=[(r.a,r.b) for r in mg.itertuples() if r.planned]
        from bisect import bisect_right
        known_zero=[];planned=[];times=[];values=[]
        for dt,value in zip(power.dt,power.value):
            if dt>=end:continue
            j=bisect_right(pstarts,dt)-1
            # La producción debe cubrir toda la muestra, no solo su instante inicial.
            known=j>=0 and dt+timedelta(seconds=cadence)<=pends[j]
            zero=known and punits[j]==0
            plan=any(a<=dt and dt+timedelta(seconds=cadence)<=b for a,b in planned_intervals)
            known_zero.append(zero);planned.append(plan);times.append(dt);values.append(value)
        flags_by_rule=alumno.estados(known_zero,values,planned,catalog['idle_kw'])
        for rule,flags in flags_by_rule.items():
            episodes+=episodes_from_flags(times,flags,cadence,mid,sid,rule,10)
        for hour in pd.date_range(start,end,freq='h',inclusive='left'):
            stop=min(hour+timedelta(hours=1),end)
            # Muestras del intervalo + vecina anterior y posterior para integración.
            sub=power[(power.dt>=hour-timedelta(seconds=cadence*1.5)) & (power.dt<=stop+timedelta(seconds=cadence*1.5))]
            kwh,seconds=energy_segments(list(sub.dt),list(sub.value),hour,stop,cadence)
            p=pg[(pg.a>=hour)&(pg.b<=stop)]
            # No repartir unidades de un intervalo que cruza el límite sin evidencia.
            crossing=pg[(pg.a<stop)&(pg.b>hour)&~((pg.a>=hour)&(pg.b<=stop))]
            pcoverage=sum((r.b-r.a).total_seconds() for r in p.itertuples())/(stop-hour).total_seconds()
            units=int(p.units_ok.sum());rejected=int(p.units_rejected.sum());coverage=seconds/(stop-hour).total_seconds()
            evaluable=coverage>=.95 and pcoverage>=.999999 and crossing.empty and units>0
            metrics.append(dict(machine_id=mid,start_utc=iso(hour),end_utc=iso(stop),energy_kwh=kwh,energy_coverage=coverage,production_coverage=pcoverage,
                units_ok=units,units_rejected=rejected,kwh_per_good_unit=alumno.intensidad(kwh,units,coverage,pcoverage,not crossing.empty),reject_rate=rejected/(units+rejected) if units+rejected else None,
                evaluable=evaluable))
    return pd.DataFrame(episodes,columns=EPISODES),pd.DataFrame(quality),pd.DataFrame(metrics)
