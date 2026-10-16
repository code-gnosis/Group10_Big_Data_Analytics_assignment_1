#!/bin/bash
# Section 1.1 - print the environment info
echo "AUCA Assignment I - environment check"
echo "Date: $(TZ=Africa/Kigali date)"
echo
echo "Host:"
echo "  CPU: $(sysctl -n machdep.cpu.brand_string)"
echo "  Cores: $(sysctl -n hw.physicalcpu) physical / $(sysctl -n hw.logicalcpu) logical"
echo "  RAM: $(echo $(sysctl -n hw.memsize) / 1073741824 | bc) GB"
echo "  OS: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "  Free disk: $(df -h / | awk 'NR==2 {print $4}')"
echo
echo "Software:"
echo "  Python: $(python3 --version)"
echo "  Docker: $(docker --version | awk '{print $3}' | tr -d ,)"
echo "  EMQX: 5.7.2 (Docker)"

docker exec -i auca_timescaledb psql -U auca -d energy_grid -c \
  "SELECT split_part(version(), ' ', 2) AS postgres_version;"

docker exec -i auca_timescaledb psql -U auca -d energy_grid -c \
  "SELECT extversion AS timescaledb_version FROM pg_extension WHERE extname='timescaledb';"

echo
echo "Postgres settings:"
docker exec -i auca_timescaledb psql -U auca -d energy_grid -c \
  "SELECT name, setting, unit FROM pg_settings
   WHERE name IN ('shared_buffers','work_mem','max_parallel_workers_per_gather','jit');"

echo "Database check:"
docker exec -i auca_timescaledb psql -U auca -d energy_grid -c \
  "SELECT current_database(), current_setting('TimeZone'), now();"

echo "EMQX broker:"
docker exec auca_emqx /opt/emqx/bin/emqx ctl status
