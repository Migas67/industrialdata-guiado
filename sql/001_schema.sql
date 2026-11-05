CREATE TABLE IF NOT EXISTS machines (
 machine_id text PRIMARY KEY, machine_type text NOT NULL, location text NOT NULL);
CREATE TABLE IF NOT EXISTS sensors (
 sensor_id text PRIMARY KEY, machine_id text NOT NULL REFERENCES machines,
 variable text NOT NULL, unit text NOT NULL, expected_period_s integer NOT NULL CHECK(expected_period_s>0),
 operational_min double precision NOT NULL, operational_max double precision NOT NULL,
 physical_min double precision NOT NULL, physical_max double precision NOT NULL,
 UNIQUE(machine_id,variable));
CREATE TABLE IF NOT EXISTS catalog_settings (key text PRIMARY KEY, value jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
 run_id text PRIMARY KEY, started_at timestamptz NOT NULL, finished_at timestamptz,
 status text NOT NULL, summary jsonb, error text);
-- Reaplicar este fichero es idempotente; no requiere eliminar pgdata.
