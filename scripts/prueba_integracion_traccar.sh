#!/usr/bin/env bash
# =============================================================================
# Prueba de integración EN VIVO Traccar <-> Odoo (Actividades 3 y 9), sin mocks:
#   Traccar Client (protocolo OsmAnd) -> Traccar Server -> API REST -> Odoo -> geocercas -> exactitud.
#
# Levanta un Traccar EFÍMERO (contenedor nuevo, sin datos, sin puertos publicados) en la red de Docker
# Compose, crea un administrador de prueba con contraseña aleatoria, ejecuta la prueba
# transporte_calidad/tests/test_traccar_vivo.py en la BD desechable y elimina el contenedor al terminar.
# NO toca el Traccar del equipo (traccar_server) ni la BD de transporte.
#
# Uso:  bash scripts/prueba_integracion_traccar.sh [nombre_bd_pruebas]
# Requiere: contenedores levantados y la BD de pruebas creada por scripts/ejecutar_pruebas.sh.
# =============================================================================
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BD="${1:-sgmtb_test}"
SALIDA="$RAIZ/backups"
RED="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' odoo16_web | awk '{print $1}')"
NOMBRE=sgmtb_traccar_prueba
ALIAS=traccar-prueba
mkdir -p "$SALIDA"

docker rm -f "$NOMBRE" >/dev/null 2>&1 || true
trap 'docker rm -f "$NOMBRE" >/dev/null 2>&1 || true' EXIT
docker run -d --rm --name "$NOMBRE" --network "$RED" --network-alias "$ALIAS" traccar/traccar:latest >/dev/null
echo "== Traccar efímero en la red $RED (alias $ALIAS)"

PASS="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)"
USUARIO="prueba@sgmtb.local"
# Espera al servidor y registra el primer usuario (en un servidor nuevo queda como administrador)
docker exec -i -e PASS="$PASS" -e USUARIO="$USUARIO" odoo16_web python3 - <<'PY'
import os, sys, time, requests
url = 'http://traccar-prueba:8082'
for _ in range(90):
    try:
        if requests.get(url + '/api/server', timeout=3).status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    sys.exit('Traccar efímero no respondió')
r = requests.post(url + '/api/users', json={'name': 'Prueba SGM-TB', 'email': os.environ['USUARIO'],
                                            'password': os.environ['PASS']}, timeout=10)
r.raise_for_status()
print('administrador de prueba creado; Traccar', requests.get(url + '/api/server', timeout=5).json().get('version'))
PY

docker exec \
  -e TRACCAR_VIVO_URL="http://$ALIAS:8082" -e TRACCAR_VIVO_OSMAND="http://$ALIAS:5055" \
  -e TRACCAR_VIVO_USER="$USUARIO" -e TRACCAR_VIVO_PASSWORD="$PASS" \
  odoo16_web bash -c "odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons \
  --db_host=\$HOST --db_user=\$USER --db_password=\$PASSWORD --http-port=8099 --stop-after-init \
  -d $BD -u transporte_calidad --test-enable --test-tags traccar_vivo" > "$SALIDA/odoo_traccar_vivo.log" 2>&1 || true

grep -E "tests.result|FAIL:|ERROR:|skipped" "$SALIDA/odoo_traccar_vivo.log" || true
if grep -q " skipped " "$SALIDA/odoo_traccar_vivo.log" || ! grep -q "0 failed, 0 error(s) of 2 tests" "$SALIDA/odoo_traccar_vivo.log"; then
  echo "RESULTADO: FALLO (ver $SALIDA/odoo_traccar_vivo.log)"; exit 1
fi
echo "RESULTADO: OK (2 pruebas en vivo contra Traccar real)"
