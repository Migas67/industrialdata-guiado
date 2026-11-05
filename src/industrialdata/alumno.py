"""TU TRABAJO. Los contratos completos y ejemplos están en docs/GUIA.md.
No importes soluciones externas ni leas escenarios_esperados.json desde el detector.
Las funciones deben trabajar con los argumentos recibidos, sin valores fijos de la demo.
"""
import math
from .common import timestamp, iso

def normalizar(row, sensor, catalog):
    """A1. Devuelve una COPIA validada y con fechas UTC, o lanza ValueError.
    Comprueba máquina/variable/unidad contra sensor; fechas con zona; ventana
    inclusiva del catálogo; valor numérico finito (no bool), rango FÍSICO y rejilla.
    Una superación del rango operativo se conserva. No modifiques row.
    """ 
    out = dict(row)                                   

    # 1-3. Coherencia con el catálogo del sensor
    if out.get('machine_id') != sensor['machine_id']:
        raise ValueError('invalid_machine_id')
    if out.get('variable') != sensor['variable']:
        raise ValueError('invalid_variable')
    if out.get('unit') != sensor['unit']:
        raise ValueError('invalid_unit')

    # 4. Fechas: timestamp() lanza ValueError si es ilegible o sin zona
    ts = timestamp(out['timestamp_utc'])
    out['timestamp_utc'] = iso(ts)
    if out.get('ingested_at_utc') is not None:
        out['ingested_at_utc'] = iso(timestamp(out['ingested_at_utc']))

    # 5. Ventana del catálogo (límites inclusivos)
    start = timestamp(catalog['start'])
    end = timestamp(catalog['end'])
    if not (start <= ts <= end):
        raise ValueError('outside_window')

    # 6. Valor numérico (bool es subclase de int: hay que excluirlo)
    v = out.get('value')
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError('numeric_value_required')

    # 7. Finito y dentro del rango FÍSICO (no el operativo)
    if not math.isfinite(v) or not (sensor['physical_min'] <= v <= sensor['physical_max']):
        raise ValueError('physical_range')

    # 8. Rejilla de la cadencia
    if (ts - start).total_seconds() % sensor['expected_period_s'] != 0:
        raise ValueError('off_grid')

    return out

def clasificar(row, previous, event_collision=False):
    """A2. Devuelve 'new' o 'duplicate'; conflicto -> ValueError.
    event_collision -> event_id_collision. Si previous existe, comparar
    machine_id, variable, unit y value; diferencia -> conflicting_value.
    Mismo contenido de negocio = duplicado aunque cambien event_id o recepción.
    """
    if event_collision:
          raise ValueError('event_id_collision')
    if previous is None:
        return 'new'
    for campo in ('machine_id', 'variable', 'unit', 'value'):
        if row[campo] != previous[campo]:
            raise ValueError('conflicting_value')
    return 'duplicate'

def superaciones(values, limit):
    """A3. Lista de bool: valor estrictamente mayor que limit.
    La agrupación temporal, 5/3 muestras y corte de huecos ya están proporcionados.
    """
    return [v > limit for v in values]

def estados(known_zero, values, planned, idle_kw):
    """A4. Dict con listas bool: idle_consumption, planned_stop, unplanned_stop.
    known_zero implica producción conocida y cero unidades (correctas+rechazadas).
    Consumo improductivo: cero producción y potencia > umbral.
    Parada: cero producción y potencia <= umbral; dividir según planned.
    No afirmar parada/consumo improductivo cuando producción es desconocida.
    """
    idle, plan_stop, unplan_stop = [], [], []
    for zero, kw, plan in zip(known_zero, values, planned):
        parada = zero and kw <= idle_kw
        idle.append(zero and kw > idle_kw)
        plan_stop.append(parada and plan)
        unplan_stop.append(parada and not plan)
    return {'idle_consumption': idle,
            'planned_stop': plan_stop,
            'unplanned_stop': unplan_stop}# Placeholder implementation - replace with actual logic

def energia(times, values, start, end, cadence=60):
    """A5. Devuelve (kWh, segundos cubiertos) para [start,end).
    Fechas ordenadas con zona. Retención del valor izquierdo entre muestras.
    Solo huecos positivos <= 1.5*cadence; recortar al periodo; no extrapolar.
    """
    kwh = 0.0
    cubiertos = 0.0
    max_hueco = 1.5 * cadence
    for i in range(len(times) - 1):
        t1, t2 = times[i], times[i + 1]
        hueco = (t2 - t1).total_seconds()
        if hueco <= 0 or hueco > max_hueco:
            continue                          # hueco largo: sin estimar
        ini = max(t1, start)                  # recortar a [start, end)
        fin = min(t2, end)
        segundos = (fin - ini).total_seconds()
        if segundos <= 0:
            continue                          # segmento fuera del periodo
        kwh += values[i] * segundos / 3600    # potencia de la IZQUIERDA
        cubiertos += segundos
    return kwh, cubiertos

def intensidad(kwh, units_ok, energy_coverage, production_coverage, crossing):
    """A6. kWh/pieza correcta o None si no es evaluable.
    Requiere cobertura energética >= .95, producción >= .999999,
    ausencia de intervalos cruzados y units_ok > 0. No inventar ceros.
    """
    if kwh is None or units_ok is None or units_ok <= 0:
        return None                       # sin denominador válido
    if energy_coverage is None or energy_coverage < 0.95:
        return None                       # energía incompleta
    if production_coverage is None or production_coverage < 0.999999:
        return None                       # producción incompleta
    if crossing:
        return None                       # no repartimos piezas de un intervalo cruzado
    return kwh / units_ok