from industrialdata.catalog import connection
from industrialdata.common import root
with connection() as conn:
    assert conn.execute('SELECT 1').fetchone()[0]==1
    assert conn.execute("SELECT to_regclass('machines')").fetchone()[0]=='machines'
root().mkdir(parents=True,exist_ok=True)
print('Infraestructura SQL disponible. Ejecuta el simulador y completa las actividades.')
