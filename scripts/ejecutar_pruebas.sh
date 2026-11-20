#!/usr/bin/env bash
# =============================================================================
# Ejecuta TODAS las pruebas del proyecto SGM-TB (Actividad 9) de forma reproducible.
#   1. pytest (caja blanca de la lógica pura) + cobertura  -> backups/coverage-*.xml, junit-*.xml
#   2. Suites Odoo (core + gps + calidad) en una BD NUEVA y desechable
#   3. Prueba de rendimiento (tag "rendimiento")
#   4. Pruebas de interfaz en navegador headless (tag "ui"), si hay Chromium en el contenedor
# Uso:  bash scripts/ejecutar_pruebas.sh [nombre_bd_pruebas]
# Requiere: contenedores levantados (docker compose up -d) y python3 con venv.
# =============================================================================
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BD="${1:-sgmtb_test}"
SALIDA="$RAIZ/backups"
mkdir -p "$SALIDA"

echo "== 1/4 pytest + cobertura"
if [ ! -x "$RAIZ/.venv/bin/python" ]; then
  python3 -m venv "$RAIZ/.venv" && "$RAIZ/.venv/bin/pip" -q install pytest pytest-cov requests
fi
for m in transporte_gps_traccar transporte_calidad; do
  (cd "$RAIZ/addons/$m/tests/pytest" && "$RAIZ/.venv/bin/python" -m pytest -q -p no:cacheprovider \
      --cov=../../lib --cov-branch --cov-report=term --cov-report=xml:"$SALIDA/coverage-$m.xml" \
      --junitxml="$SALIDA/junit-$m.xml")
done

ODOO="odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons \
  --db_host=\$HOST --db_user=\$USER --db_password=\$PASSWORD --http-port=8099 --stop-after-init"

echo "== 2/4 Suites Odoo en BD nueva '$BD'"
docker exec odoo16_db dropdb -U "${POSTGRES_USER:-odoo}" --if-exists --force "$BD"
docker exec odoo16_web bash -c "$ODOO -d $BD -i transporte_calidad --test-enable \
  --test-tags /transporte_core,/transporte_gps_traccar,/transporte_calidad" > "$SALIDA/odoo_tests.log" 2>&1 || true
grep -E "tests.stats|tests.result" "$SALIDA/odoo_tests.log"

echo "== 3/4 Rendimiento"
docker exec odoo16_web bash -c "$ODOO -d $BD -u transporte_calidad --test-enable \
  --test-tags rendimiento/transporte_calidad" > "$SALIDA/odoo_rendimiento.log" 2>&1 || true
grep -E "RENDIMIENTO|tests.result" "$SALIDA/odoo_rendimiento.log"

echo "== 4/4 Interfaz (navegador headless; requiere Chromium en el contenedor, ver docs/PLAN_PRUEBAS.md)"
if docker exec odoo16_web which chromium >/dev/null 2>&1; then
  docker exec odoo16_web bash -c "$ODOO -d $BD -u transporte_calidad --test-enable \
    --test-tags ui/transporte_calidad" > "$SALIDA/odoo_ui.log" 2>&1 || true
  grep -E "tests.result|FAIL|ERROR:" "$SALIDA/odoo_ui.log"
else
  echo "Chromium no instalado en odoo16_web: se omiten las pruebas de interfaz."
fi

if grep -q "0 failed, 0 error" "$SALIDA/odoo_tests.log"; then echo "RESULTADO: OK"; else echo "RESULTADO: HAY FALLOS (ver $SALIDA/odoo_tests.log)"; exit 1; fi
