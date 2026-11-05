# Experimentos guiados de UT1

En este bloque estudiarás formatos, complejidad y procesamiento con distintos motores y volúmenes. Empieza cuando A1–A6 funcionen y completa aquí A7. Guarda resultados reales y versiones. No ejecutes perfiles grandes a la vez. Los scripts no presuponen que Spark sea más rápido.

## Complejidad, CSV/Parquet y Avro

```console
docker compose run --rm pipeline python scripts/maths.py
docker compose run --rm pipeline python scripts/benchmark.py
```

El primer script compara lista y conjunto; explica coste temporal, espacio auxiliar y límites del experimento. El segundo compara lectura y agregación equivalentes, tres repeticiones y memoria de procesos. La caché del sistema no se vacía: anótalo. Comprueba el roundtrip Avro/Parquet con `pytest -m integracion -k avro` y explica las diferencias de esquema y representación. Completa tablas y conclusiones en el notebook.

## A7 · pandas y Spark

En `src/industrialdata/experimentos.py`, implementa la misma operación: filtrar `variable == 'power'`, agrupar por máquina y hora UTC y obtener potencia media y número de observaciones. Salida pandas con columnas `machine_id, hour, mean_power, n`, ordenada y sin índice antiguo. La media es de muestras, no una energía ni una media temporal ponderada.

```console
docker compose run --rm pipeline python -m pytest tests/test_alumno.py -q -k A7
docker compose --profile spark build spark
docker compose --profile spark run --rm spark python scripts/spark_smoke.py
docker compose --profile spark run --rm spark
```

Spark es **local[2]**, con límite de 3 GB y 2 CPU en Compose. El smoke solo cuenta tres filas y puede ejecutarse desde el principio. El experimento requiere A7 y una publicación válida: comprueba equivalencia con tolerancia `rtol=atol=1e-9`, registra arranque por separado y realiza tres repeticiones.

Si utilizas Colab, instala las versiones del proyecto, carga una copia pequeña de `silver/telemetry.parquet` y ejecuta tus funciones equivalentes. Conserva el notebook ejecutado con versiones, tamaño, equivalencia y tiempos; no compares tiempos de ordenadores distintos como si fueran el mismo entorno.

## 100.000 y un millón de observaciones

```console
docker compose run --rm pipeline python scripts/validate_volume.py --minutes 4600 --name volume100k
docker compose run --rm pipeline python scripts/validate_volume.py --minutes 46000 --name volume1m
```

Se generan perfiles independientes bajo `data/volume100k` y `data/volume1m`, de más de 100.000 y un millón de observaciones respectivamente. No se inflan duplicando registros. Se usa un catálogo JSON explícito para aislar los experimentos y no modificar el PostgreSQL de la demo: esta excepción no sustituye la integración SQL obligatoria del recorrido principal.

Consulta `data/reports/volume*.json`: tiempos, memoria muestreada, integridad de fuentes, unicidad, episodios y formatos. Si ya existe una publicación de ese perfil, el script se detiene; conserva las evidencias y usa otro DATA_ROOT, no borres resultados para aparentar una repetición limpia.

Puedes comparar motores en cada perfil con:

```console
docker compose --profile spark run --rm -e DATA_ROOT=/data/volume100k spark
docker compose --profile spark run --rm -e DATA_ROOT=/data/volume1m spark
```

Mide recursos disponibles y registra problemas de memoria. Los datos se procesan en memoria; un millón de filas no demuestra escalabilidad distribuida. Estima también almacenamiento, coste aproximado y límites para una posible implantación real (RA1g), identificando supuestos y fuentes.
