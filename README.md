# Assignment I - Smart Energy Grid Analytics

Group members:
- Thierry SEBAKUNZI (101394)
- Kwezi James (101502)
- Nishyirimbere Yves (101388)

## What is in this folder

- `code/` - Python scripts and env_report.sh
- `sql/` - PostgreSQL + TimescaleDB SQL files
- `grafana/` - datasource and 2 dashboards (Raw + Aggregate)
- `logs/` - captured output of each step
- `outputs/` - figures and json results
- `screenshots/` - screenshots embedded in the report
- `REPORT.pdf` - the submitted report

`code/smart_meter_simulator.py` is the generator file provided by the instructor, unchanged.

## Requirements

- Docker Desktop
- Python 3.11+
- Postgres credentials used throughout: user `auca`, password `gishushu`, db `energy_grid`
- Host port 5433 is mapped to the container's 5432

## Step by step

Start the containers (TimescaleDB and EMQX from Week 1):

```
docker start auca_timescaledb auca_emqx
```

Create the Python environment:

```
python3 -m venv .venv
source .venv/bin/activate
pip install psycopg2-binary paho-mqtt matplotlib pandas numpy scikit-learn
```

Run in this order:

```
# 1.1 - environment and database
docker exec -i auca_timescaledb psql -U auca -d postgres < sql/01_env_setup.sql
bash code/env_report.sh

# 1.2 - create 3 tables + load 4000 meters
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/02_schema.sql
python code/02_load_meters.py

# 1.3 - pilot MQTT (open 2 terminals)
python code/03_pilot_subscriber.py   # terminal 1
python code/03_pilot_publisher.py    # terminal 2
# press Ctrl+C in terminal 1 when done

# 2.1 - full historical load (10.7M rows)
python code/04_full_load.py

# 2.2 and 2.3 - quality and cleaning
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/05_data_quality.sql
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/06_clean.sql

# 3 - chunk comparisons
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/07_build_chunk_tables.sql
python code/08_benchmark_queries.py
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/09_explain_plans.sql

# 4 - compression
python code/10_build_compressed.py
python code/10b_compress_old_chunks.py
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/11_storage_comparison.sql
python code/12_benchmark_compressed.py

# 5 - analysis
python code/13_section5_analysis.py

# 6 - continuous aggregates and freshness test
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/14_cont_aggregates.sql
docker exec -i auca_timescaledb psql -U auca -d energy_grid < sql/15_freshness_test.sql

# 7 - dashboards
# start Grafana if not already
# http://localhost:3001/d/raw-dash/raw
# http://localhost:3001/d/agg-dash/aggregate
python code/14_dashboard_verify_and_time.py

# 8 - forecast
python code/15_forecast.py
```

## Verifying the pilot

After running the pilot (`03_pilot_subscriber.py` + `03_pilot_publisher.py`),
check all four counts are 2000:

```
docker exec -i auca_timescaledb psql -U auca -d energy_grid -c "SELECT COUNT(*) FROM energy_live"
```

The publisher prints `generator_dicts = 2000`, `publish_queued = 2000`, `broker_acked = 2000`,
and the row count above should be 2000.
