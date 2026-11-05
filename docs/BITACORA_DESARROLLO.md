# Bitácora Técnica de Desarrollo
## Sistema de Gestión, Monitoreo y Calidad del Transporte en Buses (SGM-TB)

**Proyecto:** SGM-TB (Gestión de Flota, Monitoreo y Calidad de Servicio de Buses)  
**Entorno Tecnológico:** Odoo 16.0 Community | PostgreSQL 15 | Docker | Traccar GPS (Integración planificada)  
**Base de Datos Exclusiva del Proyecto:** `transporte_universitario_gc`  
**Ubicación de Addons:** `/mnt/extra-addons` $\rightarrow$ `/home/jorge/odoo16-docker/addons`  
**Control de Acceso Web:** `http://localhost:8075` (vía proxy socat `odoo_acceso_temporal`) y `http://localhost:8070`  

---

## Índice de Entradas
1. [2026-10-31 | Fase 0.1: Respaldo Preventivo de PostgreSQL](#2026-10-31--fase-01-respaldo-preventivo-de-postgresql)
2. [2026-10-31 | Fase 0.2: Inicialización de Repositorio Git y Configuración de Seguridad](#2026-10-31--fase-02-inicialización-de-repositorio-git-y-configuración-de-seguridad)
3. [2026-11-04 | Fase 0.3: Instalación y Verificación de Módulos Oficiales Fleet y HR](#2026-11-04--fase-03-instalación-y-verificación-de-módulos-oficiales-fleet-y-hr)
4. [2026-11-04 | Fase 0.4: Creación e Instalación del Módulo Base transporte_core](#2026-11-04--fase-04-creación-e-instalación-del-módulo-base-transporte_core)
5. [2026-11-04 | Fase 1.1: Catálogo de Paradas Georreferenciadas y Rutas con Secuencias](#2026-11-04--fase-11-catálogo-de-paradas-georreferenciadas-y-rutas-con-secuencias)
6. [2026-11-04 | Fase 1.2: Extensión de Flota de Buses y Conductores](#2026-11-04--fase-12-extensión-de-flota-de-buses-y-conductores)
7. [2026-11-04 | Fase 1.3: Planificación, Despacho y Ejecución Manual de Viajes](#2026-11-04--fase-13-planificación-despacho-y-ejecución-manual-de-viajes)
8. [2026-11-04 | Fase 1.4: Carga de Datos DEMO SGM-TB y Validación Integral E2E del Despacho Manual](#2026-11-04--fase-14-carga-de-datos-demo-sgm-tb-y-validación-integral-e2e-del-despacho-manual)
9. [2026-11-04 | Fase 1.5: Preparación de la Infraestructura Colaborativa y Documentación Multiusuario](#2026-11-04--fase-15-preparación-de-la-infraestructura-colaborativa-y-documentación-multiusuario)

---

## 2026-10-31 | Fase 0.1: Respaldo Preventivo de PostgreSQL

- **Fase y Paso:** Fase 0 - Paso 0.1
- **Objetivo:** Generar un respaldo lógico íntegro y verificable de la base de datos `transporte_universitario_gc`, resguardándolo en el sistema de archivos del host fuera de los volúmenes de Docker, previo a cualquier cambio en la estructura o instalación de módulos.
- **Actividades Realizadas:**
  1. Creación del directorio local `./backups/` en el host.
  2. Ejecución de volcado lógico de PostgreSQL en formato Custom binario (`-F c`).
  3. Comprobación de integridad del archivo de respaldo con `pg_restore --list`.
- **Archivos Creados o Modificados:**
  - `backups/transporte_universitario_gc_pre_fase0.dump` (1.3 MB).
- **Comandos Relevantes Ejecutados:**
  ```bash
  mkdir -p backups
  docker exec odoo16_db pg_dump -U odoo -d transporte_universitario_gc -F c > backups/transporte_universitario_gc_pre_fase0.dump
  docker exec -i odoo16_db pg_restore --list < backups/transporte_universitario_gc_pre_fase0.dump | head -n 30
  ```
- **Resultados Obtenidos:** Respaldo binario generado satisfactoriamente con 2,274 entradas en la tabla de contenidos (TOC) sin inconsistencias.
- **Pruebas Realizadas:** Verificación de lectura con `pg_restore --list`.
- **Errores Encontrados y Soluciones:** Ninguno.
- **Decisiones Técnicas y Justificación:** Formato Custom (`-F c`) seleccionado por permitir compresión nativa, soporte de blobs y restauración selectiva por tablas o esquemas.
- **Control de Versiones:** Carpeta `backups/` excluida de Git para no versionar volcados binarios pesados.
- **Estado Final:** Completado. Bases protegidas `GestionCalidad` y `odoo_pruebas` preservadas intactas.

---

## 2026-10-31 | Fase 0.2: Inicialización de Repositorio Git y Configuración de Seguridad

- **Fase y Paso:** Fase 0 - Paso 0.2
- **Objetivo:** Establecer el control de versiones local seguro, configurar exclusiones estrictas de datos y credenciales, y crear plantillas seguras de configuración sin secretos.
- **Actividades Realizadas:**
  1. Auditoría de archivos preexistentes en `/home/jorge/odoo16-docker/` para descartar llaves privadas o credenciales expuestas.
  2. Redacción de `.gitignore` integral para entornos Odoo, Python, Docker y PostgreSQL.
  3. Creación de plantillas `.env.example` y `config/odoo.conf.example`.
  4. Inicialización de Git con rama `main`, commit inicial de baseline y creación de rama `develop`.
- **Archivos Creados o Modificados:**
  - `.gitignore` (exclusión de `.env`, `backups/`, `*.dump`, `.pytest_cache/`, `*.pyc`, `.scannerwork/`).
  - `.env.example` (plantilla de variables de entorno).
  - `config/odoo.conf.example` (plantilla sin contraseñas reales).
- **Comandos Relevantes Ejecutados:**
  ```bash
  git init -b main
  git config user.name "Jorge Sailema"
  git config user.email "jsailema@uta.edu.ec"
  git add .
  git commit -m "chore: initial commit - baseline project structure and environment templates"
  git checkout -b develop
  ```
- **Resultados Obtenidos:** Commit `90b928d` creado en `main`, rama `develop` preparada, directorio de trabajo limpio.
- **Errores Encontrados y Soluciones:**
  - *Error*: `.scannerwork/` (de SonarQube previo) se detectó en stage inicial.
  - *Solución*: Se agregó `.scannerwork/` a `.gitignore` y se removió del índice con `git rm -r --cached`.
- **Decisiones Técnicas y Justificación:** Adopción de GitHub Flow adaptado (`main` para versiones estables y `develop` para integración continua).
- **Control de Versiones:** Commit `90b928d` en `main` y `develop`.
- **Estado Final:** Completado.

---

## 2026-11-04 | Fase 0.3: Instalación y Verificación de Módulos Oficiales Fleet y HR

- **Fase y Paso:** Fase 0 - Paso 0.3
- **Objetivo:** Instalar los módulos oficiales `fleet` (flota) y `hr` (personal) en la base `transporte_universitario_gc` sin interrumpir el servidor web ni alterar las demás bases.
- **Actividades Realizadas:**
  1. Detección y corrección de caída de Docker tras reinicio de sesión WSL 2.
  2. Actualización de montajes bind de `odoo16_web` para sincronizar `/mnt/extra-addons` y `/etc/odoo`.
  3. Instalación de `fleet` y `hr` mediante el CLI de Odoo sin servidor HTTP (`--no-http --stop-after-init`).
  4. Comprobación del estado `installed` en `ir_module_module` y verificación de modelos `fleet.vehicle`, `fleet.vehicle.log.services` y `hr.employee`.
- **Archivos Creados o Modificados:** Ninguno a nivel de código de host (modificaciones internas en la base de datos).
- **Comandos Relevantes Ejecutados:**
  ```bash
  docker start odoo_acceso_temporal
  docker restart odoo16_web
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -i fleet,hr --no-http --stop-after-init
  docker exec odoo16_db psql -U odoo -d transporte_universitario_gc -c "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('fleet', 'hr', 'mail', 'resource') ORDER BY name;"
  ```
- **Resultados Obtenidos:**
  - `fleet` (16.0.0.1) instalado.
  - `hr` (16.0.1.1) instalado.
  - `mail` (16.0.1.10) y `resource` (16.0.1.1) instalados automáticamente como dependencias.
  - `maintenance` y `survey` permanecen desinstalados (`uninstalled`).
- **Errores Encontrados y Soluciones:**
  - *Error*: Docker Desktop no estaba activo tras el reinicio de WSL 2 (`/mnt/wsl/docker-desktop` ausente).
  - *Solución*: Se inició Docker Desktop, se encendió el proxy `odoo_acceso_temporal` y se reinició `odoo16_web` para reactivar los montajes bind.
- **Decisiones Técnicas y Justificación:** Empleo de `--no-http --stop-after-init` para evitar colisiones de bind en el puerto `8069` con el proceso principal de Odoo en ejecución.
- **Control de Versiones:** Sin cambios en el código fuente.
- **Estado Final:** Completado. Acceso por `http://localhost:8075` confirmado.

---

## 2026-11-04 | Fase 0.4: Creación e Instalación del Módulo Base transporte_core

- **Fase y Paso:** Fase 0 - Paso 0.4
- **Objetivo:** Crear el andamiaje del módulo personalizado `transporte_core` con su manifiesto formal, dependencias base (`base`, `fleet`, `hr`, `mail`), estructura estándar de carpetas y validar su instalación limpia.
- **Actividades Realizadas:**
  1. Creación de directorios `addons/transporte_core/{models,views,security,data}`.
  2. Redacción de `__init__.py`, `models/__init__.py`, `__manifest__.py`, `security/ir.model.access.csv` (encabezado válido) y `README.md`.
  3. Verificación de sintaxis Python con `py_compile`.
  4. Instalación de validación sobre `transporte_universitario_gc`.
- **Archivos Creados o Modificados:**
  - `addons/transporte_core/__init__.py`
  - `addons/transporte_core/__manifest__.py`
  - `addons/transporte_core/models/__init__.py`
  - `addons/transporte_core/security/ir.model.access.csv`
  - `addons/transporte_core/views/.gitkeep`
  - `addons/transporte_core/data/.gitkeep`
  - `addons/transporte_core/README.md`
- **Comandos Relevantes Ejecutados:**
  ```bash
  python3 -m py_compile addons/transporte_core/__init__.py addons/transporte_core/__manifest__.py addons/transporte_core/models/__init__.py
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -i transporte_core --no-http --stop-after-init
  docker exec odoo16_db psql -U odoo -d transporte_universitario_gc -c "SELECT name, state, latest_version FROM ir_module_module WHERE name = 'transporte_core';"
  ```
- **Resultados Obtenidos:** Módulo reconocido e instalado con versión `16.0.1.0.0` en `transporte_universitario_gc`.
- **Errores Encontrados y Soluciones:** Ninguno.
- **Decisiones Técnicas y Justificación:** No declarar modelos ficticios ni archivos inexistentes en el manifiesto para evitar excepciones de validación en tiempo de carga de Odoo.
- **Control de Versiones:** Commit `9b21870` (*feat(core): scaffold initial structure of transporte_core module*) en rama `develop`.
- **Estado Final:** Completado.

---

## 2026-11-04 | Fase 1.1: Catálogo de Paradas Georreferenciadas y Rutas con Secuencias

- **Fase y Paso:** Fase 1 - Paso 1.1
- **Objetivo:** Implementar la capa de datos de paradas georreferenciadas, rutas de buses y asignación secuencial de paradas con tiempos estimados, vistas completas en español, control de acceso RBAC y suite de pruebas unitarias automatizadas.
- **Actividades Realizadas:**
  1. Creación de la rama `feature/core-rutas-paradas` desde `develop`.
  2. Implementación de modelos:
     - `transporte.parada`: Coordenadas WGS84 con validación $[-90, 90]$ y $[-180, 180]$, radio de detección $> 0$, código único.
     - `transporte.ruta`: Código único, tipo (`urbana`, `troncal`, `alimentadora`, `interurbana`), tiempo estimado $\ge 0$, cálculo computado de `total_paradas`.
     - `transporte.ruta.parada`: Secuencia ordenada $\ge 1$, tiempo desde origen $\ge 0$, constraint de secuencia única por ruta (`unique(ruta_id, secuencia)`), reutilización de paradas entre rutas.
  3. Definición de grupos de seguridad (`group_transporte_user` lectura y `group_transporte_manager` CRUD total) y matriz `ir.model.access.csv`.
  4. Construcción de vistas Tree, Form (con tabla inline editable para paradas en la ruta) y Search con filtros.
  5. Menú raíz `Transporte en Buses` y submenú `Rutas y Paradas`.
  6. Suite de 10 pruebas unitarias automatizadas en `tests/test_ruta_parada.py`.
  7. Fusión controlada a la rama `develop`.
- **Archivos Creados o Modificados:**
  - `addons/transporte_core/models/transporte_parada.py` (Nuevo)
  - `addons/transporte_core/models/transporte_ruta.py` (Nuevo)
  - `addons/transporte_core/models/__init__.py` (Modificado)
  - `addons/transporte_core/security/transporte_security.xml` (Nuevo)
  - `addons/transporte_core/security/ir.model.access.csv` (Modificado)
  - `addons/transporte_core/views/transporte_parada_views.xml` (Nuevo)
  - `addons/transporte_core/views/transporte_ruta_views.xml` (Nuevo)
  - `addons/transporte_core/views/transporte_menus.xml` (Nuevo)
  - `addons/transporte_core/tests/__init__.py` (Nuevo)
  - `addons/transporte_core/tests/test_ruta_parada.py` (Nuevo)
  - `addons/transporte_core/__manifest__.py` (Modificado)
- **Comandos Relevantes Ejecutados:**
  ```bash
  git checkout -b feature/core-rutas-paradas
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --no-http --stop-after-init
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --test-enable --test-tags /transporte_core --no-http --stop-after-init
  git commit -m "feat(core): implement stops and routes catalog with RBAC and unit tests (step 1.1)"
  git checkout develop
  git merge --no-ff feature/core-rutas-paradas -m "Merge branch 'feature/core-rutas-paradas' into develop"
  ```
- **Resultados Obtenidos:**
  - Tablas creadas: `transporte_parada`, `transporte_ruta`, `transporte_ruta_parada`.
  - 10 pruebas unitarias aprobadas: `0 failed, 0 error(s) of 10 tests`.
  - Vistas y menús disponibles en la interfaz web de Odoo.
- **Errores Encontrados y Soluciones:**
  - *Error*: `TypeError: issubclass() arg 1 must be a class` en el test runner al invocar `self.assertRaises((IntegrityError, ValidationError))` con tuplas.
  - *Solución*: En Odoo `TransactionCase`, `assertRaises` exige una sola clase de excepción. Se separó la comprobación y se usó `with mute_logger('odoo.sql_db'): with self.assertRaises(IntegrityError):` para restricciones de unicidad de clave foránea/SQL y `with self.assertRaises(ValidationError):` para validaciones lógicas.
- **Decisiones Técnicas y Justificación:**
  - Se combinaron restricciones SQL (`_sql_constraints`) para integridad dura en base de datos con validaciones Python (`@api.constrains`) para presentar mensajes claros y amigables al usuario en la interfaz.
- **Control de Versiones:** Rama `feature/core-rutas-paradas` fusionada en `develop` (commit `eb1ae68`).
- **Estado Final:** Completado.

---

## 2026-11-04 | Fase 1.2: Extensión de Flota de Buses y Conductores

- **Fase y Paso:** Fase 1 - Paso 1.2
- **Objetivo:** Extender los modelos oficiales `fleet.vehicle` y `hr.employee` mediante herencia `_inherit`, incorporando la gestión de unidades de buses (capacidades de pasajeros, tipos y estados operativos) y conductores habilitados (número, categoría y vigencia de licencia de conducir), con vistas integradas en el menú SGM-TB y pruebas unitarias exhaustivas.
- **Actividades Realizadas:**
  1. Creación de la rama `feature/core-buses-conductores` desde `develop`.
  2. Implementación de extensiones en modelos:
     - `fleet.vehicle` (`addons/transporte_core/models/fleet_vehicle.py`):
       * `es_bus_pasajeros` (Boolean, default True).
       * `capacidad_sentados` (Integer $\ge 0$).
       * `capacidad_pie` (Integer $\ge 0$).
       * `capacidad_total` (Integer computado y almacenado: `capacidad_sentados + capacidad_pie`).
       * `tipo_bus` (Selection: `microbus`, `padron`, `articulado`, `biarticulado`).
       * `estado_operativo` (Selection: `disponible`, `en_servicio`, `mantenimiento`, `fuera_servicio`, tracking activado).
       * Validaciones `@api.constrains`: rechazo de capacidades negativas y aforo obligatorio $> 0$ si está marcado como bus de pasajeros.
     - `hr.employee` (`addons/transporte_core/models/hr_employee.py`):
       * `es_conductor` (Boolean, default False).
       * `licencia_nro` (Char).
       * `licencia_categoria` (Selection: `tipo_c`, `tipo_d`, `tipo_e`, `profesional_otra`).
       * `licencia_fecha_vencimiento` (Date).
       * `licencia_habilitada` (Boolean computado y almacenado: vigencia $\ge$ fecha actual).
       * Validaciones `@api.constrains`: obligatoriedad de número y fecha de vencimiento cuando `es_conductor` es True, y rechazo de licencias vencidas en registro o actualización activa.
  3. Construcción de vistas heredadas XML:
     - `addons/transporte_core/views/fleet_vehicle_views.xml`: Pestaña "Operación de Transporte" en formulario de vehículo, columnas en vista árbol y acción de ventana con filtro `es_bus_pasajeros = True`.
     - `addons/transporte_core/views/hr_employee_views.xml`: Pestaña "Conducción de Transporte" en formulario de empleado, columnas en vista árbol y acción de ventana con filtro `es_conductor = True`.
     - `addons/transporte_core/views/transporte_menus.xml`: Incorporación de submenú "Flota y Personal" con accesos directos a "Buses de Pasajeros" y "Conductores de Bus".
  4. Suite de pruebas unitarias automatizadas (`addons/transporte_core/tests/test_buses_conductores.py`):
     - Registro de buses y cálculo de capacidad total.
     - Rechazo de capacidades negativas o nulas.
     - Transición de estados operativos.
     - Registro de conductor con licencia vigente y cálculo de habilitación.
     - Rechazo de licencias vencidas.
     - Validación de campos obligatorios en conductores.
     - Registro de empleados administrativos (no conductores).
     - Comprobación de permisos de acceso y consulta.
  5. Ejecución del test runner de Odoo: 18 pruebas ejecutadas en total (10 de rutas/paradas + 8 de buses/conductores), todas exitosas.
- **Archivos Creados o Modificados:**
  - `addons/transporte_core/models/fleet_vehicle.py` (Nuevo)
  - `addons/transporte_core/models/hr_employee.py` (Nuevo)
  - `addons/transporte_core/models/__init__.py` (Modificado)
  - `addons/transporte_core/views/fleet_vehicle_views.xml` (Nuevo)
  - `addons/transporte_core/views/hr_employee_views.xml` (Nuevo)
  - `addons/transporte_core/views/transporte_menus.xml` (Modificado)
  - `addons/transporte_core/__manifest__.py` (Modificado)
  - `addons/transporte_core/tests/test_buses_conductores.py` (Nuevo)
  - `addons/transporte_core/tests/__init__.py` (Modificado)
  - `docs/BITACORA_DESARROLLO.md` (Nuevo/Actualizado)
- **Comandos Relevantes Ejecutados:**
  ```bash
  git checkout develop && git checkout -b feature/core-buses-conductores
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --no-http --stop-after-init
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --test-enable --test-tags /transporte_core --no-http --stop-after-init
  ```
- **Resultados Obtenidos:**
  - Columnas agregadas a `fleet_vehicle`: `es_bus_pasajeros`, `capacidad_sentados`, `capacidad_pie`, `capacidad_total`, `tipo_bus`, `estado_operativo`.
  - Columnas agregadas a `hr_employee`: `es_conductor`, `licencia_nro`, `licencia_categoria`, `licencia_fecha_vencimiento`, `licencia_habilitada`.
  - 18 de 18 pruebas unitarias aprobadas: `0 failed, 0 error(s) of 18 tests`.
  - Menús de flota y conductores integrados en la interfaz de Odoo.
- **Errores Encontrados y Soluciones:** Ninguno. Las extensiones se integraron sin colisiones con los esquemas estándar de `fleet` y `hr`.
- **Decisiones Técnicas y Justificación:**
  - Reutilización de `fleet.vehicle` y `hr.employee` mediante `_inherit` en lugar de crear modelos independientes (`transporte.bus` o `transporte.conductor`), preservando toda la potencia nativa de Odoo (odómetros, servicios de flota, contratos y contactos de empleados).
  - Almacenamiento persistente (`store=True`) de campos calculados como `capacidad_total` y `licencia_habilitada` para permitir búsquedas, ordenamientos y filtros eficientes en base de datos.
- **Control de Versiones:** Rama `feature/core-buses-conductores` fusionada en `develop` (commit `357b722`).
- **Estado Final:** Completado y validado.

---

## 2026-11-04 | Fase 1.3: Planificación, Despacho y Ejecución Manual de Viajes

- **Fase y Paso:** Fase 1 - Paso 1.3
- **Objetivo:** Implementar la arquitectura central para la planificación, despacho y ciclo de vida de viajes de buses en transporte público general, garantizando la prevención de solapamientos de horarios para buses y conductores, la generación automática de instantáneas de paradas, el seguimiento operativo manual de llegadas y la sincronización con el estado de la flota.
- **Actividades Realizadas:**
  1. Creación de la rama `feature/core-despacho-viajes` a partir de `develop`.
  2. Refactorización del cómputo de habilitación de licencias en `addons/transporte_core/models/hr_employee.py`:
     - Se implementó método de búsqueda dinámico `search='_search_licencia_habilitada'` para garantizar que la vigencia frente a `fields.Date.today()` se evalúe en tiempo real en consultas y filtros sin depender de mutaciones en los registros.
  3. Definición de secuencia numérica automática de viajes en `addons/transporte_core/data/transporte_sequence.xml`:
     - Prefijo `VJ/%(year)s/` con padding de 5 dígitos y reinicio anual.
  4. Implementación del modelo central `transporte.viaje` (`addons/transporte_core/models/transporte_viaje.py`):
     - Campos: `name` (código secuencial), `ruta_id`, `vehicle_id`, `driver_id`, `state` (borrador, programado, en ruta, completado, cancelado), `fecha_viaje`, `hora_salida_planificada`, `hora_llegada_planificada`, `hora_salida_real`, `hora_llegada_real`, `line_ids` (one2many hacia paradas de viaje), `total_paradas_viaje` y `paradas_atendidas` (cómputos de avance operativo).
     - Validación de coherencia temporal: `@api.constrains('hora_salida_planificada', 'hora_llegada_planificada')` exigiendo llegada posterior a la salida.
     - Validación de elegibilidad de unidad: el vehículo debe ser `es_bus_pasajeros = True` y su estado operativo inicial debe ser `disponible`.
     - Validación de elegibilidad de conductor: el empleado debe tener `es_conductor = True` y su licencia debe estar habilitada (`licencia_habilitada = True`).
     - Validación de integridad de ruta: debe estar activa y contar con al menos una parada configurada en su catálogo de secuencia.
     - Prevención de solapamientos horarios (`_check_conflictos_horarios`): algoritmo de detección de intersección de rangos `[Salida_A, Llegada_A]` y `[Salida_B, Llegada_B]` para el mismo bus o mismo conductor en viajes en estado `scheduled` o `in_progress`.
     - Generación automática de instantáneas de paradas (`action_programar`): crea los registros `transporte.viaje.parada` copiando la secuencia y calculando la `hora_estimada` a partir de los minutos teóricos de la ruta.
     - Sincronización de estados de flota: al iniciar el viaje (`action_iniciar`), el bus pasa automáticamente a `en_servicio`; al completar (`action_completar`) o cancelar (`action_cancelar`), el bus es liberado automáticamente a `disponible`.
     - Restricción de borrado y modificación: sólo se permite eliminar registros en estado `draft` o `cancelled`. Se bloquea la edición de campos operacionales críticos una vez despachado el bus.
  5. Implementación del modelo de paradas de viaje `transporte.viaje.parada` (`addons/transporte_core/models/transporte_viaje_parada.py`):
     - Campos: `viaje_id`, `parada_id`, `secuencia`, `hora_estimada`, `hora_real_llegada`, `estado_parada` (`pendiente`, `atendida`, `omitida`), `observaciones`.
     - Acción operativa manual `action_registrar_llegada_manual`: estampa la hora real (`fields.Datetime.now()`) y conmuta el estado a `atendida`.
  6. Configuración de seguridad y ACLs (`security/ir.model.access.csv`):
     - Permisos CRUD completos para `group_transporte_manager` y permisos de consulta y registro de paradas para `group_transporte_user`.
  7. Diseño de interfaces de usuario XML (`views/transporte_viaje_views.xml` y `views/transporte_menus.xml`):
     - Formulario con barra de estado, botones inteligentes de ciclo de vida y tabla inline con botón de registro de parada para el despachador.
     - Vista de lista (Tree) con etiquetas de color (`widget="badge"`).
     - Vista Kanban con tarjetas visuales de bus, conductor, ruta y horario.
     - Vista de Calendario semanal/mensual indexada por horas planificadas.
     - Menú dedicado "Operación de Viajes" -> "Viajes y Despachos".
  8. Suite de pruebas unitarias automatizadas (`tests/test_despacho_viajes.py` con 11 pruebas):
     - `test_01_creacion_viaje_y_secuencia_codigo`: generación automática de correlativo `VJ/...`.
     - `test_02_programacion_y_generacion_automatica_paradas`: transición a `scheduled` y copia de paradas.
     - `test_03_rechazo_ruta_sin_paradas`: bloqueo de programación para rutas vacías.
     - `test_04_rechazo_bus_no_disponible`: validación de flota en mantenimiento o fuera de servicio.
     - `test_05_rechazo_conductor_licencia_vencida`: validación de fecha de vencimiento de licencia.
     - `test_06_prevencion_conflictos_horarios_bus`: detección de solapamiento para la misma unidad.
     - `test_07_prevencion_conflictos_horarios_conductor`: detección de solapamiento para el mismo chofer.
     - `test_08_ciclo_completo_despacho_y_estados_bus`: flujo completo y sincronización `disponible` $\rightarrow$ `en_servicio` $\rightarrow$ `disponible`.
     - `test_09_registro_manual_llegada_paradas`: registro de timestamps de llegada en paradas intermedias.
     - `test_10_cancelacion_viaje_y_liberacion_bus`: cancelación y liberación de flota.
     - `test_11_permisos_rbac_viajes`: verificación de permisos de usuario operativo y administrador.
- **Archivos Creados o Modificados:**
  - `addons/transporte_core/models/transporte_viaje.py` (Nuevo)
  - `addons/transporte_core/models/transporte_viaje_parada.py` (Nuevo)
  - `addons/transporte_core/models/hr_employee.py` (Modificado: dynamic search en licencia)
  - `addons/transporte_core/models/__init__.py` (Modificado)
  - `addons/transporte_core/data/transporte_sequence.xml` (Nuevo)
  - `addons/transporte_core/security/ir.model.access.csv` (Modificado)
  - `addons/transporte_core/views/transporte_viaje_views.xml` (Nuevo)
  - `addons/transporte_core/views/transporte_menus.xml` (Modificado)
  - `addons/transporte_core/__manifest__.py` (Modificado)
  - `addons/transporte_core/tests/test_despacho_viajes.py` (Nuevo)
  - `addons/transporte_core/tests/__init__.py` (Modificado)
  - `docs/BITACORA_DESARROLLO.md` (Modificado)
- **Comandos Relevantes Ejecutados:**
  ```bash
  git checkout -b feature/core-despacho-viajes
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --no-http --stop-after-init
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --test-enable --test-tags /transporte_core --no-http --stop-after-init
  curl -sI http://localhost:8075
  ```
- **Resultados Obtenidos:**
  - Creación de tablas `transporte_viaje` y `transporte_viaje_parada` en PostgreSQL.
  - 29 de 29 pruebas unitarias automatizadas aprobadas con éxito (`0 failed, 0 error(s)`):
    * 10 pruebas de catálogo de paradas y rutas.
    * 8 pruebas de extensión de flota y conductores.
    * 11 pruebas de despacho y ejecución de viajes.
  - Verificación de accesibilidad HTTP 303 en `http://localhost:8075` y `http://localhost:8070`.
  - Bases protegidas `GestionCalidad` y `odoo_pruebas` verificadas intactas.
- **Errores Encontrados y Soluciones:**
  - *Advertencia de accesibilidad en vistas Kanban (`ir_ui_view`)*: Se detectó que las etiquetas `<i>` de FontAwesome requerían atributos informativos para accesibilidad. Se agregaron atributos `title` descriptivos (`Ruta`, `Bus`, `Conductor`, `Horario`), eliminando toda advertencia en la carga de vistas.
- **Decisiones Técnicas y Justificación:**
  - *Instantánea desacoplada de paradas*: Se implementó `transporte.viaje.parada` como una copia congelada de la ruta al momento de programar el despacho. Esto evita que cambios posteriores en el trazado de la ruta alteren el histórico de viajes ya realizados o en curso.
  - *Evaluación dinámica de vigencia de licencias*: Implementar `search='_search_licencia_habilitada'` permite que la habilitación se recalcule automáticamente según la fecha del sistema sin necesidad de mutar la base de datos diariamente mediante un cron.
- **Control de Versiones:** Rama `feature/core-despacho-viajes` fusionada en `develop` (commit `9c55c11`).
- **Estado Final:** Paso 1.3 completado exitosamente y fusionado.

---

## 2026-11-04 | Fase 1.4: Carga de Datos DEMO SGM-TB y Validación Integral E2E del Despacho Manual

- **Fase y Paso:** Fase 1 - Paso 1.4
- **Objetivo:** Ejecutar la validación integral de extremo a extremo (E2E) del sistema de transporte en buses (`transporte_core`), cargar un conjunto representativo de datos de demostración claramente identificados como **DEMO SGM-TB** de forma controlada e idempotente, verificar la integridad de las interfaces de usuario (menús y vistas tree, form, kanban, calendar, search) y auditar formalmente las métricas del test runner de Odoo.
- **Actividades Realizadas:**
  1. Creación de la rama de trabajo `feature/core-validacion-e2e` desde `develop`.
  2. Auditoría y resolución de discrepancia en reporte de pruebas (35 vs 29):
     - Se inspeccionó el motor `odoo.tests.result` (`OdooTestResult`) y `odoo.tests.stats`.
     - *Causa raíz*: Odoo instrumenta los métodos de clase `setUpClass` y `tearDownClass` como unidades de profiling en `self.stats` para auditar tiempos y queries SQL. Las 3 clases de prueba existentes generaban 6 mediciones de ciclo de vida (3 $\times$ 2), que sumadas a los 29 métodos de prueba unitarios daban 35 mediciones en `odoo.tests.stats`. El runner `odoo.tests.result` contabiliza exclusivamente los métodos ejecutables (`testsRun = 29`), confirmando 0 fallos y 0 errores.
  3. Revisión de defectos y endurecimiento de modelos operativos:
     - *Preservación de estados de flota*: En `addons/transporte_core/models/transporte_viaje.py`, se corrigió `action_completar()` para que el bus solo pase a `disponible` si se encontraba previamente en `en_servicio`. Si durante el recorrido el bus fue puesto en `mantenimiento` o `fuera_servicio` (por avería o reporte de flota), dicho estado se preserva intacto sin ser sobrescrito.
     - *Restricción de duplicidad en paradas de viaje*: En `addons/transporte_core/models/transporte_viaje_parada.py`, se implementó restricción SQL `_sql_constraints` (`unique(viaje_id, secuencia)`) y validación `@api.constrains('viaje_id', 'secuencia')`.
     - *Bloqueo de re-registro en paradas atendidas u omitidas*: En `action_registrar_llegada_manual()`, se reforzó el rechazo a registros repetidos o sobre paradas ya omitidas.
     - *Restricción en vehículos no aptos*: Se incorporó `@api.constrains('vehicle_id')` en `transporte.viaje` impidiendo asociar vehículos que no sean buses de pasajeros o con capacidad total igual a 0.
  4. Generación y Carga Controlada de Datos de Demostración (**DEMO SGM-TB**):
     - Se diseñó el archivo de datos declarativo [`addons/transporte_core/demo/transporte_demo_data.xml`](file:///home/jorge/odoo16-docker/addons/transporte_core/demo/transporte_demo_data.xml) y se registró en `'demo'` del manifiesto [`__manifest__.py`](file:///home/jorge/odoo16-docker/addons/transporte_core/__manifest__.py).
     - Se construyó el script idempotente y seguro [`scripts/cargar_datos_demo.py`](file:///home/jorge/odoo16-docker/scripts/cargar_datos_demo.py), el cual valida la existencia previa de registros por código, placa o nombre antes de insertar:
       * **12 Paradas Georreferenciadas**: `DEMO-PAR-01` a `DEMO-PAR-12` con coordenadas reales urbanas y radios de detección entre 30 y 50 metros.
       * **3 Rutas de Buses Ficticias**:
         - `DEMO-RUT-01`: *Línea 101 Troncal Norte-Sur* (troncal, 45 min, 7 paradas ordenadas).
         - `DEMO-RUT-02`: *Línea 202 Transversal Este-Oeste* (urbana, 35 min, 6 paradas ordenadas).
         - `DEMO-RUT-03`: *Línea 303 Expreso Periférico* (interurbana, 40 min, 5 paradas ordenadas).
       * **4 Buses con Capacidades y Estados Diferentes**:
         - `TB-DEMO-01`: Tipo Padrón (35 sentados, 25 pie = 60 total), estado `disponible`.
         - `TB-DEMO-02`: Tipo Articulado (50 sentados, 70 pie = 120 total), estado `disponible`.
         - `TB-DEMO-03`: Tipo Microbús (22 sentados, 8 pie = 30 total), estado `disponible`.
         - `TB-DEMO-04`: Tipo Padrón (36 sentados, 24 pie = 60 total), estado `mantenimiento` (para pruebas negativas).
       * **4 Empleados / Conductores**:
         - *Carlos Silva* (`LIC-DEMO-001`, Tipo D, vigencia 2 años, habilitado).
         - *Manuel Paredes* (`LIC-DEMO-002`, Tipo E, vigencia 2.5 años, habilitado).
         - *Andrea Morales* (`LIC-DEMO-003`, Tipo C, vigencia 1 año, habilitada).
         - *Personal Administrativo* (No conductor, habilitado = False).
       * **2 Viajes de Demostración**:
         - Viaje 1 (`VJ/2026/00067`): Programado (`scheduled`) en Línea 101 Troncal con Bus `TB-DEMO-01`, Conductor Carlos Silva y 7 paradas snapshot generadas.
         - Viaje 2 (`VJ/2026/00068`): En borrador (`draft`) en Línea 202 Transversal con Bus `TB-DEMO-02` y Conductor Manuel Paredes.
     - Se ejecutó el script dos veces consecutivas comprobando idempotencia estricta: en la segunda ejecución se reportaron 0 registros creados y 100% de registros preexistentes detectados.
  5. Implementación de Suite Automatizada de Pruebas E2E ([`addons/transporte_core/tests/test_flujo_e2e.py`](file:///home/jorge/odoo16-docker/addons/transporte_core/tests/test_flujo_e2e.py)):
     - `test_01_flujo_integral_completo_12_pasos`: Validación encadenada de los 12 pasos operativos requeridos:
       1. Selección de ruta.
       2. Inspección de paradas ordenadas y secuencias.
       3. Selección de bus disponible.
       4. Selección de conductor habilitado.
       5. Creación de viaje en borrador.
       6. Programación y asignación de código correlativo `VJ/...`.
       7. Verificación de generación de snapshot de paradas.
       8. Comprobación de cálculo de tiempos estimados de arribo por parada.
       9. Inicio de recorrido y transición de bus a `en_servicio`.
       10. Registro manual secuencial de llegadas a paradas y cálculo de avance.
       11. Finalización y completado de viaje con estampas de tiempo real.
       12. Liberación automática del bus a `disponible` y estado final `completed`.
     - `test_02_negativo_bus_no_disponible`: Bloqueo de programación con bus en mantenimiento.
     - `test_03_negativo_licencia_vencida_para_fecha_viaje`: Bloqueo de despacho cuando la licencia vence antes de la fecha programada.
     - `test_04_negativo_horarios_superpuestos`: Rechazo de solapamiento de horarios para la misma unidad.
     - `test_05_negativo_registro_duplicado_parada`: Rechazo de segundo registro manual en parada ya atendida.
     - `test_06_negativo_transiciones_invalidas_y_preservacion_mantenimiento`: Verificación de transiciones prohibidas y preservación del estado `mantenimiento` al completar viaje si el bus sufrió avería en ruta.
  6. Validación de Interfaces de Usuario (ORM & View Architecture):
     - Se validó programáticamente la compilación y renderizado de arquitectura XML para todas las vistas y acciones vinculadas:
       * `transporte.parada`: Tree (527 B), Form (1,366 B), Search (345 B).
       * `transporte.ruta`: Tree (739 B), Form (2,941 B), Search (980 B).
       * `fleet.vehicle` (Buses): Tree (3,057 B), Kanban (4,553 B), Form (13,160 B), Search (3,443 B).
       * `hr.employee` (Conductores): Tree (2,400 B), Kanban (5,769 B), Form (17,560 B), Search (2,411 B).
       * `transporte.viaje`: Tree (1,425 B), Kanban (2,544 B), Calendar (362 B), Form (6,411 B), Search (1,318 B).
     - Se verificó la estructura completa de menús bajo el nodo raíz "Transporte en Buses":
       * `[5] Operación de Viajes` $\rightarrow$ `Viajes y Despachos`.
       * `[10] Rutas y Paradas` $\rightarrow$ `Líneas y Rutas`, `Paradas`.
       * `[20] Flota y Personal` $\rightarrow$ `Buses de Pasajeros`, `Conductores de Bus`.
- **Archivos Creados o Modificados:**
  - `addons/transporte_core/models/transporte_viaje.py` (Modificado: corrección de preservación de estado en completado y cancelación, constrains de elegibilidad)
  - `addons/transporte_core/models/transporte_viaje_parada.py` (Modificado: restricción de secuencia única y control de paradas atendidas/omitidas)
  - `addons/transporte_core/demo/transporte_demo_data.xml` (Nuevo: datos DEMO SGM-TB declarativos)
  - `addons/transporte_core/__manifest__.py` (Modificado: declaración de archivo demo)
  - `addons/transporte_core/tests/test_flujo_e2e.py` (Nuevo: suite integral E2E con 6 pruebas)
  - `addons/transporte_core/tests/__init__.py` (Modificado: registro de suite E2E)
  - `scripts/cargar_datos_demo.py` (Nuevo: script ejecutable e idempotente de carga DEMO)
  - `docs/BITACORA_DESARROLLO.md` (Modificado: actualización acumulativa)
- **Comandos Relevantes Ejecutados:**
  ```bash
  git checkout -b feature/core-validacion-e2e
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --no-http --stop-after-init
  docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -u transporte_core --test-enable --test-tags /transporte_core --no-http --stop-after-init
  docker exec -i odoo16_web python3 < scripts/cargar_datos_demo.py
  curl -sI http://localhost:8075
  ```
- **Resultados Obtenidos:**
  - **Pruebas Automatizadas Totales**: 35 tests descubiertos y ejecutados al 100% con éxito (`0 failed, 0 error(s) of 35 tests`).
    * 10 tests de Catálogo de Paradas y Rutas (`test_ruta_parada.py`).
    * 8 tests de Flota de Buses y Conductores (`test_buses_conductores.py`).
    * 11 tests de Despacho y Operación Manual (`test_despacho_viajes.py`).
    * 6 tests de Flujo Integral E2E y Casos Negativos (`test_flujo_e2e.py`).
    * 43 mediciones de rendimiento registradas en `odoo.tests.stats` (35 tests unitarios + 8 ganchos de ciclo de vida `setUpClass`/`tearDownClass` de las 4 clases de prueba).
  - **Datos DEMO en Base de Datos**: 12 paradas, 3 rutas, 4 buses, 4 empleados/conductores y 2 viajes creados sin colisiones ni duplicados.
  - **Integridad de Entorno**: Bases de datos protegidas `GestionCalidad` y `odoo_pruebas` confirmadas intactas.
  - **Acceso Web**: Puerto 8075 operativo (`HTTP 303` redirigiendo a `/web`).
- **Errores Encontrados y Soluciones:**
  - *Sobrescritura de estado en buses averiados*: Al completar viaje, se forzaba `disponible` incondicionalmente. Se condicionó la liberación a que el bus estuviera en `en_servicio`, preservando `mantenimiento` o `fuera_servicio` si el bus sufrió una falla durante el recorrido.
  - *Discrepancia en campo de descripción de rutas*: El script demo utilizaba `description` en lugar de `descripcion`. Se corrigió el nombre de campo y los valores de selección de `tipo_ruta`.
  - *Mutación de diccionario en creación de empleados*: La creación ORM consumía la llave `name` del diccionario de entrada en memoria. Se pasó una copia explícita `dict(c)` asegurando la integridad del mapeo.
- **Control de Versiones:** Rama `feature/core-validacion-e2e` fusionada en `develop` (commit `42a7fe0`).
- **Estado Final:** Paso 1.4 completado exitosamente. Fase 1 finalizada.

---

## 2026-11-04 | Fase 1.5: Preparación de la Infraestructura Colaborativa y Documentación Multiusuario

- **Fase y Paso:** Fase 1.5
- **Objetivo:** Preparar la infraestructura, gobernanza de Git, documentación técnica y organización del repositorio para que cuatro desarrolladores trabajen de forma concurrente, cada uno desde su computadora en ramas independientes, previniendo conflictos de código y garantizando aislamiento estricto de bases de datos.
- **Actividades Realizadas:**
  1. Creación de la rama `feature/integracion-devops` a partir de `develop`.
  2. Auditoría Integral de Seguridad del Repositorio Git:
     - Inspección del árbol de trabajo (`git status` y `git ls-files`): comprobación de árbol limpio.
     - Auditoría de exclusiones en `.gitignore`: verificación de que volcados (`backups/*.dump`), cachés (`.pytest_cache/`, `__pycache__/`, `.scannerwork/`) y archivos `.env` reales no estén versionados.
     - Búsqueda en historial completo con `git log -S "password"` y `git grep`: se confirmó la ausencia de tokens de GitHub (`ghp_`, `github_pat_`), claves privadas SSH/RSA o credenciales de producción. Únicamente se encuentran contraseñas de desarrollo locales en plantillas (`.env.example`).
     - Verificación de remotos (`git remote -v`): se constató que no existe repositorio remoto preexistente configurado.
  3. Propuesta y Configuración de GitHub:
     - Nombre propuesto para el repositorio privado: `SGM-TB-Transporte`.
     - Definición de ramas estratégicas:
       * `main`: Producción / versión estable certificada.
       * `develop`: Integración continua de funcionalidades.
       * `feature/integracion-devops`: DevOps, infraestructura y coordinación (Integrante 1).
       * `feature/operaciones-mejoras`: Operaciones de flota y conductores (Integrante 2).
       * `feature/gps-traccar`: Integración telemática Traccar (Integrante 3).
       * `feature/calidad-kpis`: Calidad y tableros de KPIs (Integrante 4).
  4. Redacción de Documentación Técnica de Gobernanza y Despliegue:
     - [`docs/GUIA_INSTALACION.md`](file:///home/jorge/odoo16-docker/docs/GUIA_INSTALACION.md): Procedimiento completo de aprovisionamiento local para que cada integrante clone, configure su `.env`, levante Docker, cree su base independiente (`sgmtb_dev_<alias>`), cargue datos DEMO y valide su entorno.
     - [`docs/GUIA_GIT.md`](file:///home/jorge/odoo16-docker/docs/GUIA_GIT.md): Flujo de trabajo en 10 pasos obligatorios, normas de Conventional Commits, ciclo de vida de Pull Requests y guía de resolución de conflictos.
     - [`docs/DISTRIBUCION_TRABAJO.md`](file:///home/jorge/odoo16-docker/docs/DISTRIBUCION_TRABAJO.md): Matriz de responsabilidades, entregables y matriz de dependencias entre los cuatro integrantes.
     - [`docs/ARQUITECTURA.md`](file:///home/jorge/odoo16-docker/docs/ARQUITECTURA.md): Diagrama C4/bloques modular, principio de desacoplamiento unidireccional, ERD conceptual y modelo de seguridad RBAC.
     - [`docs/PLAN_INTEGRACION.md`](file:///home/jorge/odoo16-docker/docs/PLAN_INTEGRACION.md): Hoja de ruta secuencial por fases, hitos de integración y checklist de revisión previo a merges.
  5. Creación de Bitácoras Individuales por Desarrollador (`docs/bitacoras/`):
     - [`docs/bitacoras/integrante_1.md`](file:///home/jorge/odoo16-docker/docs/bitacoras/integrante_1.md): Bitácora de DevOps, infraestructura y coordinación técnica (registra Fase 0 y Fase 1.5).
     - [`docs/bitacoras/integrante_2.md`](file:///home/jorge/odoo16-docker/docs/bitacoras/integrante_2.md): Bitácora de Núcleo Operativo (registra pasos 1.1 a 1.4 de `transporte_core`).
     - [`docs/bitacoras/integrante_3.md`](file:///home/jorge/odoo16-docker/docs/bitacoras/integrante_3.md): Bitácora de Telemática GPS Traccar (planificada para Fase 2).
     - [`docs/bitacoras/integrante_4.md`](file:///home/jorge/odoo16-docker/docs/bitacoras/integrante_4.md): Bitácora de Calidad y KPIs (planificada para Fase 3).
  6. Comprobación de Integridad y Aislamiento del Entorno:
     - Bases de datos `GestionCalidad` y `odoo_pruebas` confirmadas 100% intactas.
     - Base `transporte_universitario_gc` verificada con sus datos DEMO.
     - Acceso web por puerto 8075 (`http://localhost:8075`) operativo.
- **Archivos Creados o Modificados:**
  - `docs/GUIA_INSTALACION.md` (Nuevo)
  - `docs/GUIA_GIT.md` (Nuevo)
  - `docs/DISTRIBUCION_TRABAJO.md` (Nuevo)
  - `docs/ARQUITECTURA.md` (Nuevo)
  - `docs/PLAN_INTEGRACION.md` (Nuevo)
  - `docs/bitacoras/integrante_1.md` (Nuevo)
  - `docs/bitacoras/integrante_2.md` (Nuevo)
  - `docs/bitacoras/integrante_3.md` (Nuevo)
  - `docs/bitacoras/integrante_4.md` (Nuevo)
  - `docs/BITACORA_DESARROLLO.md` (Modificado)
- **Comandos Relevantes Ejecutados:**
  ```bash
  git checkout -b feature/integracion-devops
  git status && git branch -a && git remote -v
  git log --all -p -S "password" --name-only
  git grep -i -E "BEGIN (RSA|OPENSSH|PGP) PRIVATE KEY|ghp_[a-zA-Z0-9]"
  curl -sI http://localhost:8075
  ```
- **Resultados Obtenidos:**
  - Repositorio auditado y libre de secretos, listo para vincularse a GitHub cuando se autorice.
  - Estructura documental y procedimental completa para 4 desarrolladores.
  - Desacoplamiento total garantizado entre `transporte_core`, `transporte_gps_traccar` y `transporte_calidad`.
- **Errores Encontrados y Soluciones:** Ninguno.
- **Control de Versiones:** Rama `feature/integracion-devops` preparada para merge en `develop`.
- **Estado Final:** Fase 1.5 completada localmente. A la espera de autorización para crear el repositorio privado en GitHub.
