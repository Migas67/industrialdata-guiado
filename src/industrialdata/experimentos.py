"""A7: completar la misma agregación en ambos motores. Leer docs/EXPERIMENTOS.md."""
def pandas_agregar(df):
    """Solo power; agrupar por machine_id y hora UTC.
    Devolver DataFrame: machine_id, hour (YYYY-MM-DD HH:00:00), mean_power, n.
    n cuenta observaciones. Ordenar machine_id/hour y reiniciar índice.
    """
    raise NotImplementedError('A7 pendiente: pandas_agregar')

def spark_agregar(df):
    """Mismo contrato que pandas_agregar. Recibe Spark DataFrame, devuelve pandas.
    Usar operaciones Spark antes de recoger la agregación con toPandas().
    """
    raise NotImplementedError('A7 pendiente: spark_agregar')
