# Evaluación de Calidad del Software — ISO/IEC 25010 y SonarQube (Actividad 9)

## 1. Relación con ISO/IEC 25010

| Característica | Subcaracterística | Evidencia en SGM-TB | Resultado |
| :--- | :--- | :--- | :--- |
| **Adecuación funcional** | Completitud | 22 RF trazados a pruebas (`REQUISITOS.md`) | 19 casos de la matriz aprobados |
| | Corrección | Fórmulas de KPIs verificadas contra registros (CP-11) y ejemplo del enunciado 08:15→08:23 (CP-05) | Correcto |
| | Pertinencia | Dashboard responde las 10 preguntas del enunciado (`GUIA_DEMOSTRACION.md`) | Sí |
| **Eficiencia de desempeño** | Comportamiento temporal | Dashboard ≤ 48 ms extremo a extremo; reevaluar 60 viajes 347 ms (CP-16) | Cumple RNF-03 (< 3 s) |
| | Utilización de recursos | Campos almacenados para agregaciones; consultas indexadas por fecha/bus/viaje | — |
| **Compatibilidad** | Interoperabilidad | Traccar API REST + forward JSON; Traccar Client por OsmAnd sobre HTTPS (túnel) | Verificado con Traccar real (contenedor) |
| **Usabilidad** | Reconocibilidad / protección frente a errores | Datos simulados con cinta e insignia; filtros reales/simulados; validaciones con mensajes en español | CP-17 |
| **Fiabilidad** | Madurez | 0 fallos en 89 pruebas Odoo + 128 pytest | — |
| | Tolerancia a fallos | Traccar caído → log con error; carrera cron/webhook con savepoint | tests GPS |
| | Integridad de datos (*exactitud*) | UNIQUE de posiciones, integridad GPS 100 %, verificación de exactitud contra Traccar | CP-14, CP-19 |
| **Seguridad** | Confidencialidad | RBAC (Consulta / Administrador); defecto D-02 corregido | CP-18 |
| | Autenticidad | Webhook con Bearer en tiempo constante; 401 sin token | tests GPS |
| | Responsabilidad | Chatter con seguimiento en viajes e incidencias; incidencias automáticas no borrables | CP-15 |
| **Mantenibilidad** | Modularidad | 3 módulos con dependencias unidireccionales; lógica pura en `lib/` | — |
| | Capacidad de prueba | Cobertura `lib/` 97–99 % (ramas); `scripts/ejecutar_pruebas.sh` | — |
| | Analizabilidad / modificabilidad | SonarQube (§2); tolerancias parametrizadas sin tocar código | — |
| **Portabilidad** | Instalabilidad | Docker Compose; perfiles `tunel` y `tunel-fijo` | `GUIA_INSTALACION.md` |

## 2. SonarQube

`sonar-project.properties` limita el análisis al código propio (`transporte_core`, `transporte_gps_traccar`,
`transporte_calidad`, `transporte_ui`, `scripts`), excluye los addons de otras asignaturas y la librería incluida
`static/lib` (Leaflet). La cobertura se importa desde los XML que genera `scripts/ejecutar_pruebas.sh`.

```bash
# 1. Servidor efímero (no reutiliza volúmenes de otros proyectos)
docker network create sgmtb_sonar
docker run -d --rm --name sgmtb_sonarqube --network sgmtb_sonar -p 127.0.0.1:9000:9000   -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true sonarqube:community
# 2. http://localhost:9000 (admin/admin, obliga a cambiarla) -> My Account -> Security -> Generate Token
# 3. Cobertura + análisis. El repo se monta en SU MISMA RUTA: los XML de cobertura traen rutas absolutas
#    y con "-v $PWD:/usr/src" SonarQube no los resuelve (cobertura 0 %). La URL usa la IP del contenedor
#    porque Java rechaza nombres de host con "_".
bash scripts/ejecutar_pruebas.sh
IP=$(docker inspect -f '{{(index .NetworkSettings.Networks "sgmtb_sonar").IPAddress}}' sgmtb_sonarqube)
docker run --rm --network sgmtb_sonar -e SONAR_HOST_URL=http://$IP:9000 -e SONAR_TOKEN=<token>   -v "$PWD:$PWD" -w "$PWD" sonarsource/sonar-scanner-cli -Dsonar.projectBaseDir="$PWD"
```

### Resultados (20/11/2026 · SonarQube Community 26.8 · evidencia `docs/evidencias/sonarqube_20261120.json`)

| Métrica SonarQube | Valor | Interpretación / acción |
| :--- | :--- | :--- |
| Quality Gate | **Aprobado** (Sonar way: cobertura nueva 100 % ≥ 80, duplicación nueva 0 % ≤ 3, 0 incidencias nuevas) | — |
| Bugs / Reliability rating | **0 / A** | 1.ª pasada: 3 (`python:S1244`, igualdad de floats). Corregidos: exactitud Traccar ↔ Odoo compara conteos enteros (`iguales == verificadas`) y el punto nulo GPS (0, 0) usa tolerancia `CERO_GPS`. |
| Vulnerabilities / Security rating | **0 / A** | 1.ª pasada: 3 `xml:S2068` en la vista de ajustes Traccar. **Falsos positivos**: `password="True"` solo enmascara el campo; los valores se guardan en `ir.config_parameter`. Excluidos de forma explícita y justificada en `sonar-project.properties`. |
| Security Hotspots | **0** (rating A) | SonarQube no marcó el webhook (`auth='none'`, `csrf=False`), los `sudo()` ni el SQL fijo; se justifican igualmente abajo. |
| Code Smells / Maintainability rating | **66 / A** · deuda 369 min (**0,2 %**) | Ver desglose. |
| Cobertura (`lib/`, lógica pura) | **97,2 %** | pytest-cov con ramas; modelos/vistas se validan con el runner de Odoo (95 pruebas + 5 de interfaz). |
| Duplicaciones | **0,3 %** de líneas | — |
| Tamaño | 6 699 líneas de código, 89 archivos, complejidad ciclomática 824 | — |

**Desglose de los 66 code smells y decisión:**

| Regla | N | Decisión |
| :--- | :-: | :--- |
| `python:S9073` aserciones compuestas en tests pytest | 21 | Se mantienen: comparan tuplas de resultado en una sola aserción, con mensaje de diferencia completo de pytest. |
| `python:S117` nombres de variables locales | 18 | Se mantienen: convención de Odoo (`Viaje = self.env['transporte.viaje']` para modelos). |
| `python:S1192` literal repetido (nombres de modelo) | 11 | Se mantienen: `self.env['modelo']` es el idioma de Odoo; una constante por modelo reduciría la legibilidad. |
| `python:S3776` complejidad cognitiva > 15 | 6 | **Deuda priorizada**: `reglas.evaluar_viaje` (46) y `simulador.generar_recorrido` (31) son candidatos a dividir por regla; están cubiertos al 96–98 % por pytest, lo que permite refactorizar sin riesgo. |
| `javascript:S3358` / `S6661` (ternarios anidados, `Object.assign`) | 5 | Corregidos en el código nuevo (Inicio, mapa de rutas); quedan en `dashboard.js` (estilo, sin impacto). |
| Otros (`pytz`, import, `parseInt`, encadenamiento opcional, test de excepción) | 5 | `pytz` lo usa Odoo 16 para zonas horarias. El import «sin uso» de `branding.js` es intencional: obliga a registrar el menú de usuario antes de quitarle los enlaces a odoo.com. Resto menor. |

Puntos de seguridad revisados manualmente (aunque SonarQube no los marcó):
- `controllers/main.py` usa `auth='none'` + `csrf=False`: es un webhook servidor a servidor protegido con Bearer
  (`hmac.compare_digest`).
- Uso de `sudo()` en sincronización y dashboard: escritura de posiciones/logs/mediciones por procesos del sistema.
- `wizard/simulacion.py` ejecuta SQL directo (`SELECT LEAST(MIN(...))`): consulta fija, sin parámetros del usuario.
- Popups de los mapas: nombres de rutas/paradas escapados (`escape`) para evitar XSS almacenado.
