# Bitácora Individual de Desarrollo
## Integrante 4 — Calidad del Servicio y Tableros KPIs

**Integrante:** Colaborador (`@JaimXD`)  
**Rol:** Integrante 4  
**Responsabilidades:** Desarrollo del módulo analítico `transporte_calidad`, gestión de incidencias operativas, cálculo de métricas de calidad de servicio (OTP, cumplimiento de ruta, disponibilidad de flota, tasa de incidencias) y diseño de tableros ejecutivos.  
**Rama Asignada:** `feature/calidad-kpis`.  

---

## Registro de Actividades

### 2026-11-20 | Fase 3: Módulo `transporte_calidad` (A5–A10)
- **Actividad:** Implementación completa del módulo de calidad: 9 reglas de detección (retrasos, omisiones,
  incompletos, diferencia de tiempos, desvío por corredor, pérdida de señal), incidencias idempotentes, 8 KPIs de
  transporte y 4 de calidad del software, dashboard OWL, informe PDF, asistente de 10 recorridos simulados.
  Mejora PDCA en `transporte_gps_traccar` (geocerca por tramo). Origen/destino/distancia estimada en rutas (core).
- **Archivos:** `addons/transporte_calidad/**`, `transporte_gps_traccar/lib/geo_utils.py`,
  `transporte_gps_traccar/models/{transporte_viaje,fleet_vehicle,res_config_settings}.py`,
  `transporte_core/models/transporte_ruta.py`, `transporte_core/security/ir.model.access.csv`, `scripts/*`, `docs/*`.
- **Pruebas:** 128 pytest (cobertura `lib/` 97–99 %), 89 Odoo (0 fallos), rendimiento (máx. 347 ms), 3 de interfaz.
- **Errores y soluciones:** D-01 a D-06 (ver `docs/PLAN_PRUEBAS.md §5`).
- **Rama:** `feature/calidad-kpis`.
- **Estado:** Listo para PR hacia `develop`. Pendiente: recorridos reales con teléfono y análisis SonarQube.

### 2026-11-04 | Fase 1.5: Planificación de Indicadores de Calidad y Modelo de Incidencias
- **Actividad:** Análisis de los modelos de viajes y paradas de `transporte_core` para definir las fórmulas matemáticas de los KPIs de calidad del transporte.
- **Objetivo:** Garantizar que los indicadores puedan calcularse sobre los registros manuales de viajes de la Fase 1, sin requerir que la telemetría GPS esté finalizada.
- **Archivos Modificados:** `docs/bitacoras/integrante_4.md` (apertura de bitácora).
- **Pruebas:** Verificación del cálculo de paradas atendidas vs. programadas en datos DEMO existentes.
- **Errores y Soluciones:** Ninguno.
- **Commit:** N/A (fase preparatoria documental).
- **Estado:** Preparado para iniciar Fase 3.

---

## Plan de Trabajo para la Fase 3 (Hitos Secuenciales)

### Hito 3.1: Scaffolding de `transporte_calidad` y Gestión de Incidencias
- Crear `addons/transporte_calidad/` con manifiesto que dependa de `transporte_core`.
- Desarrollar modelo `transporte.incidencia`:
  - Tipificación: falla mecánica, desvío de ruta, congestión severa, incidente de seguridad, queja de usuario.
  - Severidad: baja, media, alta, crítica.
  - Relación opcional con `transporte.viaje`, `fleet.vehicle` y `transporte.parada`.
  - Estados: reportada, en atención, resuelta, desestimada.

### Hito 3.2: Motor de Cálculo de Puntualidad (OTP) y Cumplimiento
- **Fórmula OTP (On-Time Performance):**
  $$\text{OTP} (\%) = \left( \frac{\text{Paradas Arribadas en Tolerancia } [-2, +5] \text{ min}}{\text{Total de Paradas Atendidas}} \right) \times 100$$
- **Fórmula de Cumplimiento de Ruta:**
  $$\text{Cumplimiento} (\%) = \left( \frac{\text{Paradas Atendidas}}{\text{Paradas Totales Programadas en el Viaje}} \right) \times 100$$
- Implementación de modelo computado/asistente para reportes agregados por línea, por día y por conductor.

### Hito 3.3: Disponibilidad de Flota e Incidencias por cada 100 Viajes
- **Disponibilidad de Flota:**
  $$\text{Disponibilidad} (\%) = \left( \frac{\text{Buses Disponibles} + \text{Buses en Servicio}}{\text{Parque Total de Buses de Pasajeros}} \right) \times 100$$
- **Tasa de Incidencias:**
  $$\text{Tasa Incidencias} = \left( \frac{\text{Total Incidencias en Periodo}}{\text{Total Viajes Despachados en Periodo}} \right) \times 100$$
- Tratamiento explícito de viajes cancelados y datos con omisiones.

### Hito 3.4: Dashboards y Tableros de Control
- Implementar vistas de Odoo Community:
  - Vista Graph (gráfico de líneas temporales de puntualidad y barras de cumplimiento).
  - Vista Pivot (análisis multidimensional por ruta, bus y semana).
- Diseñar tarjeta ejecutiva con semáforos de calidad (Verde $> 85\%$, Amarillo $70-85\%$, Rojo $< 70\%$).

---

## Próximas Tareas Pendientes
- [ ] Crear la rama de trabajo `feature/calidad-kpis` a partir de `develop`.
- [ ] Crear la estructura del módulo `addons/transporte_calidad/`.
- [ ] Implementar el modelo de incidencias y sus vistas de formulario y lista.
- [ ] Desarrollar pruebas unitarias con viajes sintéticos para validar las fórmulas de OTP y cumplimiento.

