# Bitácora Individual de Desarrollo
## Integrante 1 — Coordinación Técnica, DevOps e Integración

**Rol:** Integrante 1  
**Responsabilidades:** Gobernanza del repositorio Git, arquitectura contenerizada, Docker Compose, configuración de Odoo/PostgreSQL, automatización de pruebas, empaquetado de módulos, revisión de Pull Requests y releases.  
**Rama Asignada:** `feature/integracion-devops` / Gobernanza de `develop` y `main`.  

---

## Registro de Actividades

### 2026-10-31 | Fase 0.1: Respaldo Preventivo de PostgreSQL
- **Actividad:** Creación del respaldo binario de la base de datos `transporte_universitario_gc`.
- **Objetivo:** Salvaguardar el estado previo de la base antes de cualquier instalación.
- **Archivos Modificados:** `backups/transporte_universitario_gc_pre_fase0.dump` (excluido de Git).
- **Pruebas:** Verificación exitosa de 2,274 entradas en TOC con `pg_restore --list`.
- **Errores y Soluciones:** Ninguno.
- **Commit:** N/A (archivo binario resguardado fuera del control de versiones).
- **Estado:** Completado.

---

### 2026-10-31 | Fase 0.2: Inicialización del Repositorio Git y Configuración de Seguridad
- **Actividad:** Auditoría de archivos, redacción de `.gitignore`, plantillas seguras y creación de ramas `main` y `develop`.
- **Objetivo:** Establecer un control de versiones limpio y protegido contra exposición de secretos.
- **Archivos Modificados:** `.gitignore`, `.env.example`, `config/odoo.conf.example`.
- **Pruebas:** `git status` y `git status --ignored` comprobando exclusión de respaldos y cachés.
- **Errores y Soluciones:** Ninguno.
- **Commit:** `90b928d` (*"chore: initial commit - baseline project structure and environment templates"*).
- **Estado:** Completado.

---

### 2026-11-04 | Fase 0.3: Instalación y Verificación de Módulos Oficiales Fleet y HR
- **Actividad:** Instalación controlada de `fleet` y `hr` en `transporte_universitario_gc` mediante CLI de Odoo en Docker.
- **Objetivo:** Habilitar los cimientos oficiales de flota y recursos humanos en el entorno.
- **Archivos Modificados:** Base de datos `transporte_universitario_gc` (tablas `fleet_*` y `hr_*`).
- **Pruebas:** Consulta SQL a `ir_module_module` verificando estado `installed`. Comprobación de respuesta HTTP 303 en puerto 8075.
- **Errores y Soluciones:**
  - *Error*: Docker Desktop cerrado en el anfitrión tras reinicio.
  - *Solución*: Se inició Docker Desktop en Windows y se reinició el proxy socat `odoo_acceso_temporal`.
- **Commit:** N/A (cambio a nivel de base de datos).
- **Estado:** Completado.

---

### 2026-11-04 | Fase 0.4: Estructuración e Inicialización del Módulo Base `transporte_core`
- **Actividad:** Creación del scaffolding oficial de Odoo 16 para `addons/transporte_core/`.
- **Objetivo:** Contar con un módulo personalizado reconocido por Odoo sin modelos funcionales aún.
- **Archivos Modificados:** `__manifest__.py`, `__init__.py`, `security/transporte_security.xml`, `README.md`.
- **Pruebas:** Instalación mediante CLI de Odoo comprobando registro en `ir_module_module`.
- **Errores y Soluciones:** Ninguno.
- **Commit:** `9b21870` (*"feat(core): scaffold initial transporte_core module structure"*).
- **Estado:** Completado.

---

### 2026-11-04 | Fase 1.5: Preparación de la Infraestructura Colaborativa y Documentación
- **Actividad:** Auditoría de seguridad del repositorio, diseño de la estrategia de GitHub, redacción de guías técnicas (`GUIA_INSTALACION.md`, `GUIA_GIT.md`, `DISTRIBUCION_TRABAJO.md`, `ARQUITECTURA.md`, `PLAN_INTEGRACION.md`) y preparación de bitácoras individuales.
- **Objetivo:** Habilitar el trabajo concurrente y ordenado de los cuatro integrantes sin colisiones ni riesgos de seguridad.
- **Archivos Modificados:** Directorio `docs/` completo y `docs/bitacoras/`.
- **Pruebas:** Auditoría de historial Git con `git log -S "password"`, verificación de exclusiones en `.gitignore` y comprobación de integridad en base de datos.
- **Errores y Soluciones:** Ninguno.
- **Commit:** `1a7b95c` (*"docs(devops): prepare multi-developer collaboration, installation guides, and work distribution (step 1.5)"*), fusionado en `develop` (`c514514`).
- **Estado:** Completado.

---

### 2026-11-04 | Fase 1.6: Publicación Privada y Configuración de GitHub
- **Actividad:** Ejecución de auditoría de seguridad previa al despliegue remoto: desvinculación de `config/odoo.conf` del índice de Git, actualización de `.gitignore`, parametrización de variables de entorno en `docker-compose.yml` y `scripts/cargar_datos_demo.py`. Verificación del estado de autenticación en GitHub y diagnóstico de conectividad SSH/CLI.
- **Objetivo:** Garantizar que el repositorio Git se publique de forma 100% privada y segura, sin credenciales expuestas ni dependencias de entornos locales específicos.
- **Archivos Modificados:** `.gitignore`, `docker-compose.yml`, `scripts/cargar_datos_demo.py`, `docs/BITACORA_DESARROLLO.md`, `docs/bitacoras/integrante_1.md`.
- **Pruebas:** Diagnóstico de llaves SSH (`ssh -T git@github.com`), comprobación de exclusiones con `git status --ignored`, verificación de salud de contenedores (`docker ps`) y prueba de servicio HTTP en puerto 8075 (`curl -sI http://localhost:8075`).
- **Errores y Soluciones:** Ausencia de llave SSH y credenciales de GitHub en WSL. Se detiene el proceso de push remoto de forma segura para permitir que el usuario configure su acceso autenticado.
- **Commit:** En preparación en rama `feature/publicacion-github`.
- **Estado:** Listo para push una vez provista la autenticación y los nombres de usuario del equipo.

---

## Próximas Tareas Pendientes
- [ ] Configurar llave SSH o token de GitHub para el propietario del repositorio.
- [ ] Crear el repositorio privado `SGM-TB-Transporte` en GitHub.
- [ ] Enlazar el remoto `origin` y realizar el push inicial de `main` y `develop`.
- [ ] Establecer `develop` como rama predeterminada en GitHub y configurar reglas de protección de ramas.
- [ ] Enviar invitaciones con rol `Write` a los 3 compañeros de equipo.
- [ ] Coordinar la clonación inicial y verificación de entornos con los integrantes 2, 3 y 4.
- [ ] Apoyar al Integrante 3 en el despliegue del contenedor Traccar GPS para la Fase 2.

