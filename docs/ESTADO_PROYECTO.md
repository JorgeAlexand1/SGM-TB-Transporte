# Estado del proyecto SGM-TB — punto de retorno

**Léelo primero si retomas el proyecto** (persona del equipo o una sesión nueva de Claude Code). Resume qué es,
qué está hecho, cómo está montado, cómo se prueba y qué falta. Última actualización: **22/11/2026**.

> Este repositorio es **público**: aquí no hay contraseñas. Están en la PC del servidor, en
> `config/traccar_credenciales.local` y `config/odoo_credenciales.local` (ignorados por git), y en el paquete
> privado del equipo `Documents\SGM-TB_paquete_equipo\CREDENCIALES.txt`.

---

## 1. Qué es

Proyecto final de **Gestión de Calidad de Software** (UTA, 7.º semestre). Enunciado:
`C:\Users\USUARIO\Documents\7mo\GestionCalidad\proyectoFinal_GC.pdf` (actividades A1–A10 + defensa).

**SGM-TB** = Sistema de Gestión y Monitoreo del Transporte en Buses universitario: Odoo 16 Community + Traccar
(GPS desde teléfonos con Traccar Client) + túnel de Cloudflare. Evalúa automáticamente si cada recorrido cumple
horario y ruta, genera incidencias, calcula KPIs de transporte y de calidad del software, y lo muestra en un
dashboard. Se aplican ISO/IEC 25010, SonarQube, Ishikawa, Pareto y tres ciclos PDCA.

## 2. Dónde está cada cosa

| Qué | Dónde |
| :-- | :-- |
| Repositorio | GitHub `JorgeAlexand1/SGM-TB-Transporte`, rama por defecto **`develop`** |
| Copia de trabajo que usan los contenedores | WSL Ubuntu `/home/jorge/odoo16-docker` (`\\wsl.localhost\Ubuntu\home\jorge\odoo16-docker`) |
| Odoo | `http://localhost:8070`, BD **`transporte_universitario_gc`** (idioma es_EC) |
| Traccar | `http://localhost:8082` (web/API) y `5055` (protocolo OsmAnd de los teléfonos) |
| Contenedores | `odoo16_web`, `odoo16_db` (postgres 15), `traccar_server`; túneles `cloudflared-gps`/`cloudflared-odoo` (perfil `tunel`), `cloudflared-fijo` (perfil `tunel-fijo`) |
| Respaldos de BD | `backups/` (ignorado por git). Último: `transporte_universitario_gc_pre_en_vivo_20261121_1158.dump` |
| Paquete para el equipo (BD + filestore + credenciales) | `C:\Users\USUARIO\Documents\SGM-TB_paquete_equipo\` — se restaura con `docs/DESPLIEGUE_EQUIPO.md` |

Otros módulos y BD de la misma carpeta (`math_operations`, `taller2_gc`, `techstore_sonarqube`,
`practicaUnidad4`, `tarea1/`, BD `GestionCalidad`) son **de otras materias: no tocarlos**.

## 3. Módulos (se instala solo `transporte_ui`; arrastra a los otros tres)

```
transporte_core  →  transporte_gps_traccar  →  transporte_calidad  →  transporte_ui
 (qué debería pasar)   (qué está pasando)        (¿se cumplió?)        (cómo se ve)
```

| Módulo | Contenido |
| :-- | :-- |
| `transporte_core` | Buses (sobre `fleet`), conductores, paradas, rutas, horarios, viajes y control de paradas |
| `transporte_gps_traccar` | Sincronización con Traccar cada minuto sin duplicados, geocercas por tramo, estado de señal, mapa de buses, webhook |
| `transporte_calidad` | Reglas de incumplimiento, incidencias, 8 KPIs de transporte + 4 de software, dashboard por pestañas, mapa de rutas, informe PDF, simulador de recorridos (marcados SIMULADO) |
| `transporte_ui` | Login e identidad propios, **Inicio** (4 KPIs, franja de estado, 6 accesos) y **En vivo** (estilo Moovit: líneas con color, vista tipo metro, cuenta regresiva, confianza del dato) |

Documentación clave en `docs/`: `REQUISITOS`, `ARQUITECTURA`, `PLAN_PRUEBAS` (CP-01…CP-27), `METRICAS`,
`CALIDAD_SOFTWARE` (ISO 25010 + SonarQube), `MEJORA_CONTINUA` (Ishikawa, Pareto, 3 PDCA), `GUIA_DEMOSTRACION`
(guion de la defensa), `DESPLIEGUE_EQUIPO`, `GUIA_TRABAJO_CAMPO`, **`PASOS_TRACCAR`** (checklist del teléfono),
`DISTRIBUCION_TRABAJO`, `BITACORA_DESARROLLO`.

## 4. Cronología de lo hecho

| Fecha | Hito |
| :-- | :-- |
| hasta 19/11 | Core, integración Traccar, calidad/KPIs, dashboard, simulador, pruebas, documentación A1–A10 (PR #1–#5) |
| 20/11 | Interfaz propia (Inicio, login), mapa de rutas, idioma es_EC, 2.º PDCA (pruebas UI que se saltaban, complejidad), prueba en vivo contra Traccar, SonarQube (gate OK, 0 bugs, 0 vulnerabilidades), refactor del simulador (PR #6–#8) |
| 20/11 | Historial de git reescrito para quitar la coautoría de Claude (respaldo `backups/repo_pre_reescritura_*.bundle`) |
| 20/11 | Traccar del equipo configurado: admin + `sgmtb-bus01` (id 1 → `TB-DEMO-01`) y `sgmtb-bus02` (id 2 → `TB-DEMO-02`); Odoo conectado (`http://traccar:8082`), cron OK; túnel rápido probado desde Internet (PR #9) |
| 20/11 | Reparada la BD `GestionCalidad` (assets perdidos → pantalla en blanco). Nueva contraseña del admin de la BD real. Guía de despliegue para el equipo + paquete privado (PR #10) |
| 21/11 | Rediseño: dashboard en 5 pestañas, fórmulas bajo demanda, Inicio compacto (PR #11) |
| 21/11 | Pantalla **En vivo** inspirada en Moovit + animaciones; 3.º PDCA (benchmarking); CP-27 (PR #12) |
| 22/11 | `docs/PASOS_TRACCAR.md` y este documento |

### Pull requests
| PR | Estado al 22/11 | Nota |
| :-- | :-- | :-- |
| #1–#10 | Integrados en `develop` | — |
| **#11** rediseño visual | **Abierto** | Integrar primero |
| **#12** En vivo (Moovit) | **Abierto**, apilado sobre #11 | Integrar después de #11 |
| PR de este documento | Abierto | Solo documentación |

⚠️ La copia de trabajo de WSL está en la rama **`feature/en-vivo`** y la BD real ya tiene esos módulos
actualizados: no cambiar a `develop` antes de integrar #11 y #12, o Odoo cargará código más viejo que la BD.
Después de integrarlos: `git checkout develop && git pull`, y listo (no hace falta `-u`).

## 5. Cómo se prueba

```bash
cd ~/odoo16-docker
bash scripts/ejecutar_pruebas.sh      # crea y usa la BD desechable sgmtb_test (admin/admin); no toca la real
```

Resultado al 21/11: **pytest 128/128** (cobertura 97–99 %), **Odoo 102/102**, rendimiento OK, **interfaz 7/7**
(Chromium headless), **Traccar en vivo 2/2** → `RESULTADO: OK`. Requiere Chromium y `python3-websocket` dentro de
`odoo16_web` (instalados a mano; se pierden si el contenedor se recrea, y entonces las pruebas de interfaz se
reportan como fallo, no como saltadas).

## 6. Qué falta (por prioridad para la nota)

| # | Pendiente | Actividad / criterio | Cómo |
| :-: | :-- | :-- | :-- |
| 1 | **Datos GPS reales desde el teléfono por datos móviles** (hoy: 0 posiciones reales) | A2, A3, A5, defensa (~35 pts) | `docs/PASOS_TRACCAR.md` |
| 2 | **3 rutas reales** cerca de la UTA con 4 paradas medidas en sitio (hoy son `DEMO-RUT-*` / ficticias) | A4 | `GUIA_TRABAJO_CAMPO.md` §5 |
| 3 | **≥ 10 recorridos documentados**, normales y con incumplimientos (hoy: 10 simulados + 2 manuales) | A5, A6 | `GUIA_TRABAJO_CAMPO.md` §6–§7 |
| 4 | Exactitud Traccar ↔ Odoo medida con datos reales (hoy el KPI muestra «—») | A7/A8 | Botón *Verificar exactitud Traccar* |
| 5 | Capturas de evidencia (infraestructura, integración, cada recorrido, dashboard «Solo reales», SonarQube en `http://localhost:9000` si sigue el contenedor `sgmtb_sonarqube`) | A2, A3, A5, A8 | `GUIA_TRABAJO_CAMPO.md` §8 |
| 6 | Actualizar `METRICAS.md §3` con valores reales y cerrar el PDCA con datos de campo | A7, A10 | `GUIA_TRABAJO_CAMPO.md` §9 |
| 7 | Reemplazar las capturas de la presentación por las reales y ensayar la defensa | Defensa | `docs/presentacion/`, `GUIA_DEMOSTRACION.md` |
| 8 | Integrar PR #11, #12 y el de este documento | — | GitHub |

Ideas opcionales ya conversadas: matriz de trazabilidad requisitos ↔ casos de prueba; pruebas de rendimiento con
más volúmenes; más casos de valores límite.

## 7. Reglas de trabajo (acordadas con el usuario)

- **Nunca** subir contraseñas al repositorio (es público).
- **Respaldar la BD** (`pg_dump -Fc` en `backups/`) antes de cualquier `-u` o cambio en `transporte_universitario_gc`.
- **No inyectar posiciones GPS falsas en la BD real.** El enunciado prohíbe datos ficticios presentados como
  reales; lo simulado se genera solo con el asistente y queda marcado SIMULADO.
- Commits y PR **sin** coautoría ni pie de Claude («Co-Authored-By», «Generated with Claude Code»).
- Integrar (merge) PRs lo hace el usuario en GitHub. Verificar el estado de un PR con la API, no suponerlo.
- Trabajo en ramas `feature/*` o `docs/*` desde `develop`; mensajes de commit en inglés, documentación en español.
- Comandos: se ejecutan en WSL (`wsl -e bash -lc '…'`); en Windows no hay python ni gh. Para la API de GitHub se
  usa el token de Git Credential Manager desde Git Bash de Windows (`git credential fill`), no desde WSL.
- `CLAUDE.md` pide llevar el progreso inmediato en `.claude_progreso.md` (ignorado por git).

## 8. Problemas conocidos y su arreglo

| Síntoma | Arreglo |
| :-- | :-- |
| Odoo en blanco o sin módulos tras reiniciar Windows | Abrir Docker Desktop; `docker restart odoo16_web` |
| `/web` en blanco solo en una BD | Assets dañados: respaldar y borrar los `ir_attachment` de `/web/assets/%`; Odoo los regenera (así se arregló `GestionCalidad`) |
| Pruebas de interfaz «saltadas» | Falta `python3-websocket` o Chromium en `odoo16_web` |
| `git credential fill` se cuelga en WSL | Usarlo desde Git Bash de Windows |
| La URL del túnel dejó de funcionar | Se reinició el túnel: obtener la nueva (`PASOS_TRACCAR.md` C) y cambiarla en los teléfonos |
