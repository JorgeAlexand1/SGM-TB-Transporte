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
`transporte_calidad`, `scripts`) y excluye los addons de otras asignaturas. La cobertura se importa desde los
XML que genera `scripts/ejecutar_pruebas.sh`.

```bash
# 1. Levantar SonarQube (si no está corriendo)
docker run -d --name sonarqube -p 9000:9000 sonarqube:lts-community
# 2. http://localhost:9000 -> My Account -> Security -> Generate Token
# 3. Generar cobertura y analizar (desde la raíz del repositorio)
bash scripts/ejecutar_pruebas.sh
docker run --rm --network host -e SONAR_HOST_URL=http://localhost:9000 -e SONAR_TOKEN=<token> \
  -v "$PWD:/usr/src" sonarsource/sonar-scanner-cli
```

### Registro de resultados (completar con el informe del servidor)

| Métrica SonarQube | Valor | Interpretación / acción |
| :--- | :--- | :--- |
| Quality Gate | | |
| Bugs / Reliability rating | | |
| Vulnerabilities / Security rating | | |
| Security Hotspots revisados | | Esperado: `hmac.compare_digest`, `requests` sin `verify=False`, `sudo()` justificados |
| Code Smells / Maintainability rating | | |
| Cobertura (`lib/`) | 97–99 % según pytest-cov | |
| Duplicaciones | | |

Hotspots conocidos que deben revisarse y justificarse en el informe:
- `controllers/main.py` usa `auth='none'` + `csrf=False`: es un webhook servidor a servidor protegido con Bearer.
- Uso de `sudo()` en sincronización y dashboard: escritura de posiciones/logs/mediciones por procesos del sistema.
- `wizard/simulacion.py` ejecuta SQL directo (`SELECT LEAST(MIN(...))`): consulta fija, sin parámetros del usuario.
