# Actividades guiadas · un alumno, un proyecto

Los módulos proporcionados funcionan como soporte: no debes reescribir el simulador, los controladores de archivos, la integración temporal, el publicador o el panel. Lee sus llamadas para comprender el recorrido. Completa las siete actividades sin eliminar comprobaciones ni sustituir resultados por constantes de la demo.

## H1 · Entender antes de programar (orientación: 2 h)

Ejecuta el generador. Abre unas pocas líneas de las cuatro fuentes; no intentes abrir un millón de filas en el editor. Documenta claves, cardinalidades, unidades, periodo, catálogo y relación entre producción, mantenimiento y sensores. Dibuja el recorrido con los colores proporcionado/alumno.

Explica por qué JSON Lines, CSV y SQL representan fuentes distintas y por qué guardamos el original. Construye en el notebook los conjuntos de máquinas de cada fuente, sus intersecciones y diferencias; identifica claves huérfanas. Explica cuándo la relación máquina–sensor es una función en cada dirección. Consulta el catálogo con `docker compose exec db psql -U industrialdata -d industrialdata -c "SELECT * FROM machines;"` (adapta usuario/base si cambiaste `.env`).

## A1 · Validar y normalizar (H3)

Archivo `src/industrialdata/alumno.py`, función `normalizar(row,sensor,catalog)`.

Recibes una fila JSON ya decodificada, el sensor correspondiente y el catálogo. La lectura comprueba previamente objeto, identificador de evento y existencia del sensor. Tu función devuelve una **copia** con fechas UTC normalizadas mediante `timestamp()` e `iso()`, o lanza `ValueError` para que el soporte registre el rechazo con archivo, línea y hash.

| Comprobación | Motivo de rechazo esperado |
|---|---|
| machine_id, variable, unit diferentes de los del sensor | `invalid_machine_id`, `invalid_variable`, `invalid_unit` |
| Fecha ilegible o sin zona | `ValueError` de `timestamp` (conserva el motivo) |
| Observación fuera de start/end del catálogo (límites inclusivos) | `outside_window` |
| value no numérico o booleano | `numeric_value_required` |
| No finito o fuera de physical_min/physical_max (inclusivos) | `physical_range` |
| Segundos desde catalog.start no múltiplo de expected_period_s | `off_grid` |

No limites `ingested_at_utc` al periodo observado: un dato puede llegar después. Los límites **operativos** no son límites físicos: 90 °C es una incidencia válida para un sensor con máximo operativo 80 y físico 200. El punto final se permite como vecino para integrar energía; no cuenta como muestra esperada dentro del periodo semiabierto.

Prueba `pytest ... -k A1`. Añade casos para los límites físicos, fechas sin zona y recepción tardía. En `ingest.py` localiza dónde se añade la procedencia: esa parte está proporcionada.

## A2 · Duplicados, conflictos y reconciliación (H3)

`clasificar(row,previous,event_collision)` recibe una fila validada y la primera fila aceptada con la misma clave `(sensor_id,timestamp_utc)`, o `None`.

1. Una colisión del identificador de evento entre claves distintas provoca `ValueError('event_id_collision')`.
2. Sin fila previa, devuelve `'new'`.
3. Con fila previa, compara máquina, variable, unidad y valor. Una diferencia es `ValueError('conflicting_value')`.
4. Si coinciden, devuelve `'duplicate'`, aunque cambie el identificador o la hora de recepción.

Esta política conserva la primera observación aceptada; no reemplaza un valor silenciosamente. El soporte conserva el estado anterior, clasifica cada fila y comprueba `input = accepted_new + duplicates + rejected`. Explica esa ecuación y demuestra repetición y lote tardío. Añade una prueba propia de conflicto además de las públicas.

## A3 · Temperatura y vibración (H4)

`superaciones(values,limit)` devuelve una lista de booleanos: una igualdad al límite no lo supera. El agrupador proporcionado exige 5 muestras para temperatura y 3 para vibración y corta una secuencia si el hueco supera 1,5 cadencias. Las fechas de fin de los episodios son límites exclusivos de la última muestra más una cadencia; representan el intervalo detectado, no una certificación de recuperación física.

Comprueba una secuencia normal, una superación suficiente y una interrumpida. Explica por qué una medición anómala válida se conserva.

## A4 · Producción, mantenimiento y potencia (H4)

`estados(known_zero,values,planned,idle_kw)` devuelve exactamente tres listas con nombres `idle_consumption`, `planned_stop` y `unplanned_stop`, de la misma longitud que la entrada.

El soporte ya relaciona intervalos: `known_zero` solo es verdadero si la producción cubre toda la muestra y la suma de unidades correctas y rechazadas es cero. `planned` indica mantenimiento programado que cubre toda la muestra. Tu función aplica las reglas descritas en su docstring; la agrupación de 10 muestras consecutivas ya está hecha.

El escenario proporcionado mantiene operación planificada durante todo el intervalo del catálogo; no genera turnos externos. Explica esa limitación y por qué un dato ausente no equivale a cero. Si amplías las ventanas, adapta también la integración. La coincidencia temporal con mantenimiento no demuestra causalidad.

## A5 · Energía y cobertura (H4)

`energia(times,values,start,end,cadence)` devuelve `(kWh,segundos_cubiertos)`. Recorre pares de muestras consecutivas ordenadas. La potencia de la izquierda representa cada segmento. Usa únicamente intervalos positivos de hasta 1,5 cadencias, recórtalos a `[start,end)` y convierte segundos a horas. No extiendas la última muestra hacia el futuro.

Ejemplo de comprobación: 6 kW constantes durante 5 minutos equivalen a 0,5 kWh y 300 segundos cubiertos. Una única medición no permite estimar duración. Añade un caso con un segmento que cruce el límite horario.

## A6 · Indicador evaluable (H4)

`intensidad(kwh,units_ok,energy_coverage,production_coverage,crossing)` devuelve kWh/pieza correcta o `None`. Los requisitos están en el contrato de la función. No uses cero como sustituto de desconocido. El soporte calcula producción por intervalos completos; no reparte piezas de un intervalo cruzado sin información que lo justifique.

Con A1–A6 listas, ejecuta el pipeline y revisa las tres vistas. Contrasta un episodio con las filas originales y comprueba totales, unidades, cobertura y denominadores. Las tablas y gráficos del panel están preparados, pero sus resultados proceden de tus funciones.

## A7 · Comparación de motores (sesión de UT1)

Completa las dos funciones de `experimentos.py`. Consulta [EXPERIMENTOS.md](EXPERIMENTOS.md). El script comprueba claves, conteos y tolerancia numérica; no basta con que aparezcan tiempos.

## H5–H6 · Verificar y entregar

Ejecuta `pytest -m integracion`: los 16 casos verifican escenarios, conservación de datos, repetición, llegada tardía, intervalos, rechazos y formatos. No elimines pruebas para obtener una salida verde. Añade al menos tres casos propios de A1, A2 y A5 y explica qué error detectaría cada uno.

Comprueba persistencia con los comandos del README. Entrega tus conclusiones, al menos cuatro hallazgos con sus limitaciones, el notebook ejecutado, el informe y el vídeo según el enunciado. Documenta autoría y ayudas. Un historial grande de commits no sustituye una explicación correcta.

Las 12–14 horas propuestas son una orientación para el núcleo guiado, no una garantía para todos los experimentos. El profesor integrará las mediciones y su discusión en las sesiones de UT1 y confirmará calendario y carga real.
