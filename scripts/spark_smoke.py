"""Solo arranque de Spark local. No resuelve la comparación con datos industriales."""
from pyspark.sql import SparkSession

spark = (SparkSession.builder.master('local[2]').appName('IndustrialData-arranque')
         .config('spark.ui.enabled', 'false').config('spark.sql.session.timeZone', 'UTC')
         .config('spark.sql.shuffle.partitions', '2').getOrCreate())
try:
    assert spark.range(3).count() == 3
    print(f'Spark {spark.version} local[2]: arranque OK. H5 pendiente: comparación equivalente con pandas.')
finally:
    spark.stop()
