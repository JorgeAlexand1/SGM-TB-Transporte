#!/usr/bin/env bash
# =============================================================================
# Ejecuta TODAS las pruebas del proyecto SGM-TB (Actividad 9) de forma reproducible.
#   1. pytest (caja blanca de la lógica pura) + cobertura  -> backups/coverage-*.xml, junit-*.xml
#   2. Suites Odoo (core + gps + calidad) en una BD NUEVA y desechable
#   3. Prueba de rendimiento (tag "rendimiento")
#   4. Pruebas de interfaz en navegador headless (tag "ui"); fallan si se saltan
#   5. Integración en vivo con un Traccar efímero (scripts/prueba_integracion_traccar.sh)
# Uso:  bash scripts/ejecutar_pruebas.sh [nombre_bd_pruebas]
# Requiere: contenedores levantados (docker compose up -d) y python3 con venv.
# =============================================================================
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BD="${1:-sgmtb_test}"
SALIDA="$RAIZ/backups"
mkdir -p "$SALIDA"

echo "== 1/5 pytest + cobertura"
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

echo "== 2/5 Suites Odoo en BD nueva '$BD'"
docker exec odoo16_db dropdb -U "${POSTGRES_USER:-odoo}" --if-exists --force "$BD"
docker exec odoo16_web bash -c "$ODOO -d $BD -i transporte_ui --test-enable \
  --test-tags /transporte_core,/transporte_gps_traccar,/transporte_calidad,/transporte_ui" > "$SALIDA/odoo_tests.log" 2>&1 || true
grep -E "tests.stats|tests.result" "$SALIDA/odoo_tests.log"

echo "== 3/5 Rendimiento"
docker exec odoo16_web bash -c "$ODOO -d $BD -u transporte_calidad --test-enable \
  --test-tags rendimiento/transporte_calidad" > "$SALIDA/odoo_rendimiento.log" 2>&1 || true
grep -E "RENDIMIENTO|tests.result" "$SALIDA/odoo_rendimiento.log"

echo "== 4/5 Interfaz (navegador headless; requiere Chromium en el contenedor, ver docs/PLAN_PRUEBAS.md)"
UI_OK=1
if docker exec odoo16_web which chromium >/dev/null 2>&1 \
   && docker exec odoo16_web python3 -c "import websocket" >/dev/null 2>&1; then
  docker exec odoo16_web bash -c "$ODOO -d $BD -u transporte_calidad --test-enable \
    --test-tags ui/transporte_calidad,ui/transporte_ui" > "$SALIDA/odoo_ui.log" 2>&1 || true
  grep -E "tests.result|FAIL|ERROR:" "$SALIDA/odoo_ui.log"
  # Odoo marca como «saltada» (no fallida) una prueba de navegador sin Chromium/websocket: se trata como fallo.
  if grep -q " skipped " "$SALIDA/odoo_ui.log" || ! grep -q "0 failed, 0 error" "$SALIDA/odoo_ui.log"; then
    grep " skipped " "$SALIDA/odoo_ui.log" || true
    UI_OK=0
  fi
else
  echo "Falta Chromium o python3-websocket en odoo16_web (ver docs/PLAN_PRUEBAS.md): interfaz NO ejecutada."
  UI_OK=0
fi

echo "== 5/5 Integración en vivo con un Traccar efímero (OsmAnd -> Traccar -> Odoo -> exactitud)"
VIVO_OK=1
bash "$RAIZ/scripts/prueba_integracion_traccar.sh" "$BD" || VIVO_OK=0

if ! grep -q "0 failed, 0 error" "$SALIDA/odoo_tests.log"; then echo "RESULTADO: HAY FALLOS (ver $SALIDA/odoo_tests.log)"; exit 1; fi
if [ "$VIVO_OK" != 1 ]; then echo "RESULTADO: INTEGRACIÓN EN VIVO CON TRACCAR FALLIDA (ver $SALIDA/odoo_traccar_vivo.log)"; exit 1; fi
if [ "$UI_OK" != 1 ]; then echo "RESULTADO: INTERFAZ CON FALLOS U OMITIDA (ver $SALIDA/odoo_ui.log)"; exit 1; fi
echo "RESULTADO: OK"
