# Bitácora Individual de Desarrollo
## Integrante 3 — GPS y Traccar

**Integrante:** Colaborador (`mfalcon6508@uta.edu.ec`)  
**Rol:** Integrante 3  
**Responsabilidades:** Desarrollo del módulo telemático `transporte_gps_traccar`, configuración de Traccar Server, ingesta de posiciones vía webhook/API REST, geocercas para detección automática de arribos a paradas y resiliencia ante pérdida de señal GPS.  
**Rama Asignada:** `feature/gps-traccar`.  

---

## Registro de Actividades

### 2026-11-04 | Fase 1.5: Planificación de la Integración Telemática y Revisión de Modelos Base
- **Actividad:** Análisis de los modelos entregados en `transporte_core` (`fleet.vehicle`, `transporte.parada` y `transporte.viaje.parada`) para preparar la arquitectura de extensión no invasiva en la Fase 2.
- **Objetivo:** Definir la interfaz de integración sin acoplar `transporte_core` a dependencias telemáticas externas.
- **Archivos Modificados:** `docs/bitacoras/integrante_3.md` (apertura de bitácora).
- **Pruebas:** Verificación de ejecución limpia de la suite de 35 pruebas de `transporte_core` en entorno local.
- **Errores y Soluciones:** Ninguno.
- **Commit:** N/A (fase preparatoria documental).
- **Estado:** Preparado para iniciar Fase 2 una vez autorizada.

---

## Plan de Trabajo para la Fase 2 (Hitos Secuenciales)

### Hito 2.1: Scaffolding de `transporte_gps_traccar` y Modelo de Dispositivos
- Crear `addons/transporte_gps_traccar/` con manifiesto que dependa de `transporte_core`.
- Extender `fleet.vehicle` con campo `traccar_device_id` (Integer indexado) y fecha de última posición telemática.
- Diseñar modelo `transporte.gps.log` para almacenar la traza histórica de posiciones.

### Hito 2.2: Endpoint Webhook y Autenticación Segura
- Crear controlador Odoo en `/api/v1/traccar/webhook` para recepción de posiciones de Traccar.
- Validar formato de tramas JSON (latitud, longitud, velocidad, timestamp, deviceId).
- Implementar autenticación obligatoria mediante token Bearer (`TRACCAR_WEBHOOK_SECRET`).
- Manejar descarte de tramas duplicadas o coordenadas inválidas ($0, 0$).

### Hito 2.3: Algoritmo de Geocercas y Arribo Automático
- Implementar función de cálculo de distancia ortodrómica (Haversine) en Python.
- Comparar posición recibida contra el catálogo de paradas pendientes del viaje activo del bus.
- Si la distancia $\le$ `parada.radio_deteccion`:
  - Registrar automáticamente `hora_llegada_real = fields.Datetime.now()`.
  - Conmutar `estado_parada = 'atendida'`.
  - Marcar `metodo_registro = 'gps'`.

### Hito 2.4: Resiliencia Telemática y Pruebas
- Desarrollar mecanismo de buffer/cola para procesar ráfagas de datos sin saturar transacciones de PostgreSQL.
- Diseñar pruebas unitarias automatizadas simulando secuencias de coordenadas para verificar detección de paradas sin hardware físico.

---

## Próximas Tareas Pendientes
- [ ] Configurar contenedor de Traccar GPS Server en Docker local.
- [ ] Crear la rama de trabajo `feature/gps-traccar` a partir de `develop`.
- [ ] Redactar el manifiesto y modelos iniciales de `transporte_gps_traccar`.
- [ ] Coordinar con el Integrante 1 el puerto de red y variables de entorno requeridas para el webhook.

