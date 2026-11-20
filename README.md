# SGM-TB — Monitoreo y Evaluación de Rutas de Transporte Universitario

Odoo 16 Community + Traccar + Cloudflare Tunnel · Proyecto final de Gestión de Calidad del Software (UTA).

| Módulo | Función |
| :--- | :--- |
| `addons/transporte_core` | Buses, conductores, rutas (origen, destino, distancia), paradas, horarios y despacho de viajes |
| `addons/transporte_gps_traccar` | Integración Traccar: posiciones sin duplicados, webhook, geocercas por tramo, señal, mapa |
| `addons/transporte_calidad` | Detección automática de incumplimientos, incidencias, KPIs, dashboard, informe PDF, simulación |

El repositorio solo versiona estos tres módulos. Otros addons que existan en la carpeta local `addons/`
(talleres de otras asignaturas) están excluidos en `.gitignore`.

## Inicio rápido
```bash
cp .env.example .env                      # definir contraseñas locales
docker compose up -d                      # Odoo :8070, Traccar :8082/:5055
docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc \
  -i transporte_calidad --no-http --stop-after-init && docker restart odoo16_web
docker compose --profile tunel up -d      # túnel Cloudflare para Traccar Client (datos móviles)
bash scripts/ejecutar_pruebas.sh          # todas las pruebas
```

## Documentación (entregables)
| # | Entregable | Documento |
| :-: | :--- | :--- |
| 1 | Análisis y requisitos | `docs/REQUISITOS.md` |
| 2 | Arquitectura y modelo de datos | `docs/ARQUITECTURA.md` |
| 3–4 | Integración Traccar y conectividad externa | `docs/GUIA_TRACCAR.md`, `docs/GUIA_CLOUDFLARE.md` |
| 5–7 | Reglas, indicadores y dashboard | `docs/METRICAS.md` |
| 8 | Matriz y evidencias de pruebas | `docs/PLAN_PRUEBAS.md`, `docs/evidencias/` |
| 9 | ISO/IEC 25010 y SonarQube | `docs/CALIDAD_SOFTWARE.md`, `sonar-project.properties` |
| 10 | Mejora continua (Ishikawa, Pareto, PDCA) | `docs/MEJORA_CONTINUA.md` |
| — | Guion de la defensa | `docs/GUIA_DEMOSTRACION.md` |
| — | Instalación y flujo Git | `docs/GUIA_INSTALACION.md`, `docs/GUIA_GIT.md` |
