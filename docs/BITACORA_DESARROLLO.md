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
- **Control de Versiones:** Rama `feature/core-buses-conductores`.
- **Estado Final:** Completado. Listo para merge e inicio del Paso 1.3 (Viajes y Despachos).
