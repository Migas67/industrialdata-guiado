# Requisitos y evidencias de aprendizaje

Esta tabla indica qué componentes recibes preparados, qué actividades debes completar y qué evidencias debes aportar para explicar y comprobar tu trabajo individual.

| Requisito | Componentes y actividades | Evidencia individual |
|---|---|---|
| Contexto industrial y cuatro fuentes | Generador y SQL proporcionados | Modelo y explicación de claves, unidades y relaciones |
| Seis máquinas, parámetros y manifiesto | Proporcionado; semilla, duración y máquinas configurables | Ejecutar y explicar reproducibilidad y hashes |
| S01 duplicados y S08 conflictos | A1–A2; almacenamiento de rechazos proporcionado | Casos propios, reconciliación y repetición |
| S02 sensor ausente | Detección de huecos proporcionada | Probar cobertura y explicar ausencia ≠ parada |
| S03 temperatura y S04 vibración | Umbrales A3; agrupación temporal proporcionada | Probar secuencias, límites y huecos |
| S05 consumo improductivo y S06 paradas | A4; integración temporal proporcionada | Tabla de verdad, prueba de desconocidos y clasificación |
| S07 entradas inválidas | A1; lector y cuarentena proporcionados | Rechazos con motivo y procedencia |
| Raw, Silver, Gold y cuarentena | Escritura y estructura proporcionadas | Explicar y verificar trazabilidad de una incidencia |
| Energía y denominadores | A5–A6; agregación por hora proporcionada | Casos de huecos, cero producción e intensidad no evaluable |
| Publicación consistente y fallo controlado | Orquestador proporcionado | P11 y conservación del último resultado válido |
| Llegadas tardías e idempotencia | Estado y recarga proporcionados; A2 decide | P02/P06 y cambio verificable de cobertura |
| Docker, SQL y persistencia | Configuración y verificadores proporcionados | Arranque, explicación, P09 y evidencia del tipo de reinicio |
| Panel de tres vistas | Panel completo proporcionado | Resultados generados por A1–A6 e interpretación |
| Formatos, Avro y Parquet | Herramientas de lectura/escritura y medición proporcionadas | Ejecutar, verificar equivalencia y comparar |
| Lista/conjunto y complejidad | Experimento proporcionado | Interpretación, costes y límites |
| pandas/PySpark | Sesión y medidor proporcionados; A7 pendiente | Agregación equivalente, versiones y conclusiones |
| 100.000 y un millón de observaciones | Generación y medición proporcionadas | Ejecución, consumo de recursos y límites |
| RA1g coste/calidad y alternativas | Preguntas guiadas | Estimación razonada, supuestos y decisiones |
| GitHub, informe, notebook, vídeo y defensa | Individual; plantillas proporcionadas | Autoría declarada y explicación del flujo completo |

## Pruebas de aceptación P01–P11

| Caso | Cómo se comprueba |
|---|---|
| P01 arranque | `pytest -m infra`, simulador y pipeline terminado |
| P02 repetición | `test_idempotence_and_late` y segunda carga real |
| P03 reconciliación | `test_quality_counts` e informe de carga |
| P04 integración | `test_join_totals_and_rejections` y explicación del modelo |
| P05 escenarios | `test_expected_episodes` y observación en panel |
| P06 datos tardíos | `test_idempotence_and_late` y comandos del README |
| P07 energía | A5 y `test_constant_power_and_gap` |
| P08 denominadores | A6 y `test_zero_and_missing_production` |
| P09 persistencia | Capturas before/after sin regenerar, con reinicio documentado |
| P10 formatos y motores | Roundtrip, benchmark y A7; perfiles de volumen |
| P11 fallo controlado | `test_failed_run_keeps_pointer` |

## Evaluación justa

Los criterios a–g del RA1 y sus pesos se indican en el enunciado. El profesor evalúa el código que has desarrollado, las pruebas añadidas, la interpretación y la defensa. Ejecutar código proporcionado no acredita su diseño autónomo. Los descriptores de la rúbrica se aplican con esta distinción: no se exige reescribir las piezas entregadas para alcanzar un nivel alto, pero sí demostrar comprensión y comprobar sus límites. La evaluación combina un 80 % de evidencias del proyecto individual y un 20 % de comprobación oral/práctica, según lo establecido en el enunciado y sujeto a los acuerdos del módulo.

La dedicación orientativa a las actividades principales es de 12–14 horas. Las sesiones experimentales se integran en UT1. Consulta en Moodle el calendario y las fechas de entrega.
