import json
import pandas as pd
import streamlit as st
from industrialdata.common import root
from industrialdata.run import current_snapshot

st.set_page_config(page_title='IndustrialData guiado',layout='wide')
st.title('IndustrialData')
st.caption('Versión guiada · Panel proporcionado · Planta ficticia · Datos sintéticos · UTC')
folder=root();snapshot=current_snapshot(folder)
if snapshot is None:
    st.info('Todavía no hay resultados publicados. Ejecuta el simulador, completa alumno.py y ejecuta el pipeline. El panel está preparado; los indicadores dependen de tu trabajo.')
    st.stop()
report=json.loads((snapshot/'report.json').read_text())
st.caption(f"Última carga correcta: {report['finished_at']} · Ejecución {report['run_id']}")
metrics=pd.read_parquet(snapshot/'gold/metrics.parquet')
episodes=pd.read_parquet(snapshot/'gold/episodes.parquet')
quality=pd.read_parquet(snapshot/'gold/quality.parquet')
selected=st.multiselect('Máquinas',sorted(metrics.machine_id.unique()),default=sorted(metrics.machine_id.unique()))
hours=sorted(metrics.start_utc.unique())
period=st.select_slider('Periodo UTC por horas',options=hours,value=(hours[0],hours[-1]))
m=metrics[metrics.machine_id.isin(selected)&metrics.start_utc.between(*period)]
end=pd.Timestamp(period[1])+pd.Timedelta(hours=1)
ep=episodes[episodes.machine_id.isin(selected)&(episodes.end_utc>period[0])&(episodes.start_utc<end.isoformat().replace('+00:00','Z'))]
tabs=st.tabs(['Estado e incidencias','Producción y energía','Calidad y trazabilidad'])
with tabs[0]:
    st.metric('Episodios que intersectan el periodo',len(ep))
    st.dataframe(ep,use_container_width=True,hide_index=True)
    st.caption('Las duraciones corresponden al episodio completo, aunque el filtro corte parte de él. Los huecos de sensores no se clasifican como paradas.')
    if not ep.empty:
        chosen=st.selectbox('Evidencia del episodio',list(ep.episode_id))
        row=ep[ep.episode_id==chosen].iloc[0]
        st.write(row.to_dict())
        trace=pd.read_parquet(snapshot/'silver/telemetry.parquet',filters=[('sensor_id','=',row.sensor_id),('timestamp_utc','>=',row.start_utc),('timestamp_utc','<=',row.end_utc)])
        st.dataframe(trace,use_container_width=True,hide_index=True)
with tabs[1]:
    st.caption('Energía parcial con cobertura explícita. Intensidad no evaluable si cobertura <95 %, producción incompleta o cero unidades correctas.')
    st.dataframe(m,use_container_width=True,hide_index=True)
    if not m.empty:
        st.line_chart(m.pivot(index='start_utc',columns='machine_id',values='energy_kwh'),y_label='kWh observados')
        st.bar_chart(m.groupby('machine_id')[['units_ok','units_rejected']].sum())
with tabs[2]:
    st.caption('Cobertura del histórico completo por sensor; esta tabla no se recorta al filtro horario. Rechazos y reconciliación corresponden a la última carga completa.')
    st.dataframe(quality[quality.machine_id.isin(selected)],use_container_width=True,hide_index=True)
    st.json(report)
    st.dataframe(pd.DataFrame(json.loads((snapshot/'files.json').read_text())),use_container_width=True)
    st.dataframe(pd.DataFrame(json.loads((snapshot/'quarantine/rejections.json').read_text())),use_container_width=True)
    st.download_button('Descargar informe de la carga',json.dumps(report,indent=2),file_name='informe_carga.json')
