# Bitácora Individual de Desarrollo
## Integrante 2 — Operaciones de Buses y Conductores

**Rol:** Integrante 2  
**Responsabilidades:** Mantenimiento y evolución de la capa funcional operativa en `transporte_core` (rutas, paradas, secuencias, buses, capacidades, licencias de choferes, viajes, prevención de solapamientos y ejecución manual de despachos).  
**Rama Asignada:** `feature/operaciones-mejoras`.  

---

## Registro de Actividades

### 2026-11-04 | Fase 1.1: Catálogo de Paradas Georreferenciadas y Rutas con Secuencias
- **Actividad:** Creación de los modelos `transporte.parada`, `transporte.ruta` y `transporte.ruta.parada`, vistas árbol y formulario editable, y menú principal "Transporte en Buses".
- **Objetivo:** Permitir la administración de paradas con coordenadas GPS válidas y rutas con secuencias ordenadas y tiempos de viaje.
- **Archivos Modificados:**
  - `addons/transporte_core/models/transporte_parada.py`
  - `addons/transporte_core/models/transporte_ruta.py`
  - `addons/transporte_core/views/transporte_parada_views.xml`
  - `addons/transporte_core/views/transporte_ruta_views.xml`
  - `addons/transporte_core/views/transporte_menus.xml`
  - `addons/transporte_core/tests/test_ruta_parada.py`
- **Pruebas:** 10 de 10 pruebas unitarias aprobadas (`0 failed, 0 error(s)`).
- **Errores y Soluciones:** Manejo de excepciones de unicidad en tests mediante `mute_logger('odoo.sql_db')` para `IntegrityError` de PostgreSQL.
- **Commit:** `8f47f79` fusionado en `develop` con commit `eb1ae68`.
- **Estado:** Completado.

---

### 2026-11-04 | Fase 1.2: Extensión de Flota de Buses y Conductores
- **Actividad:** Extensión no invasiva de `fleet.vehicle` (aforo sentados/pie, tipo de bus, estado operativo) y `hr.employee` (número de licencia, categoría y vigencia).
- **Objetivo:** Habilitar el parque de buses y la nómina de conductores profesionales de bus en Odoo.
- **Archivos Modificados:**
  - `addons/transporte_core/models/fleet_vehicle.py`
  - `addons/transporte_core/models/hr_employee.py`
  - `addons/transporte_core/views/fleet_vehicle_views.xml`
  - `addons/transporte_core/views/hr_employee_views.xml`
  - `addons/transporte_core/tests/test_buses_conductores.py`
- **Pruebas:** 18 de 18 pruebas unitarias aprobadas (10 rutas + 8 flota/conductores).
- **Errores y Soluciones:** Ninguno. Se utilizó `_inherit` para conservar odómetros y contratos nativos.
- **Commit:** `9e56eec` fusionado en `develop` con commit `357b722`.
- **Estado:** Completado.

---

### 2026-11-04 | Fase 1.3: Planificación, Despacho y Ejecución Manual de Viajes
- **Actividad:** Implementación del modelo central `transporte.viaje` y `transporte.viaje.parada`, máquina de estados, secuencia correlativa `VJ/...`, algoritmo de prevención de conflictos de horario y botón de registro manual de arribo.
- **Objetivo:** Permitir la planificación y seguimiento operativo de viajes sin depender de GPS.
- **Archivos Modificados:**
  - `addons/transporte_core/models/transporte_viaje.py`
  - `addons/transporte_core/models/transporte_viaje_parada.py`
  - `addons/transporte_core/data/transporte_sequence.xml`
  - `addons/transporte_core/views/transporte_viaje_views.xml`
  - `addons/transporte_core/tests/test_despacho_viajes.py`
- **Pruebas:** 29 de 29 pruebas unitarias aprobadas (10 rutas + 8 flota + 11 despachos).
- **Errores y Soluciones:**
  - *Advertencia de accesibilidad*: Se agregaron títulos descriptivos en tags `<i>` FontAwesome de la vista Kanban.
- **Commit:** `8168acd` fusionado en `develop` con commit `9c55c11`.
- **Estado:** Completado.

---

### 2026-11-04 | Fase 1.4: Carga de Datos DEMO SGM-TB y Validación Integral E2E
- **Actividad:** Corrección de preservación de estado de flota en buses averiados, unicidad de paradas de viaje, generación de archivo `transporte_demo_data.xml`, script `cargar_datos_demo.py` y suite integral E2E.
- **Objetivo:** Verificar el flujo completo de 12 pasos y los casos negativos de negocio.
- **Archivos Modificados:**
  - `addons/transporte_core/demo/transporte_demo_data.xml`
  - `addons/transporte_core/tests/test_flujo_e2e.py`
  - `scripts/cargar_datos_demo.py`
- **Pruebas:** 35 de 35 pruebas automatizadas aprobadas (`0 failed, 0 error(s)`).
- **Errores y Soluciones:**
  - *Sobrescritura de estado*: Se condicionó la liberación del bus al completar o cancelar para preservar `mantenimiento` o `fuera_servicio`.
- **Commit:** `6cb2d92` fusionado en `develop` con commit `42a7fe0`.
- **Estado:** Completado.

---

## Próximas Tareas Pendientes
- [ ] Incorporar filtros avanzados en la vista de viajes (por conductor, por rango horario, por estado de ruta).
- [ ] Diseñar reporte impreso/PDF de Hoja de Ruta para el despachador.
- [ ] Optimizar la actualización de contadores de paradas atendidas mediante SQL directo si aumenta el volumen.
- [ ] Coordinar con el Integrante 3 los campos telemáticos adicionales que se requieran en `transporte.viaje.parada`.
