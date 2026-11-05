# Guía de Instalación y Despliegue Local del Entorno de Desarrollo
## Sistema de Gestión, Monitoreo y Calidad del Transporte en Buses (SGM-TB)

**Versión del Documento:** 1.0  
**Fecha:** Noviembre 2026  
**Audiencia:** Desarrolladores y colaboradores del equipo SGM-TB  

---

## 1. Visión General del Entorno Tecnológico

El proyecto **SGM-TB** está diseñado sobre una arquitectura contenerizada y desacoplada que permite a cada desarrollador desplegar una instancia idéntica, reproducible e independiente en su máquina local (Linux nativo, WSL2 en Windows o macOS con Docker Desktop).

### Pila Tecnológica:
- **ERP Base:** Odoo 16.0 Community Edition (imagen Docker oficial `odoo:16.0`).
- **Motor de Base de Datos:** PostgreSQL 15 (imagen Docker oficial `postgres:15`).
- **Orquestación:** Docker Compose v2.
- **Lenguajes:** Python 3.9+, XML, JavaScript.
- **Telemetría Futura:** Traccar GPS Server (Integración en Fase 2).
- **Control de Versiones:** Git y GitHub (Flujo GitFlow adaptado).

---

## 2. Requisitos Previos del Sistema

Cada integrante debe contar con las siguientes herramientas instaladas y operativas en su sistema anfitrión:

1. **Git:** Versión 2.30 o superior (`git --version`).
2. **Docker Engine y Docker Compose:**
   - En Windows: Docker Desktop con integración habilitada para **WSL 2** (Ubuntu recomendado).
   - En Linux: Docker Engine $\ge$ 20.10 y plugin `docker-compose-plugin`.
   - Comprobación: `docker --version` y `docker compose version`.
3. **Recursos de Hardware Recomendados:**
   - Mínimo 8 GB de memoria RAM (16 GB recomendado).
   - Al menos 15 GB de espacio libre en disco para imágenes y volúmenes Docker.
4. **Puertos de Red Disponibles:**
   - Puerto `8070` (u otro configurable en `.env`, ej. `8080`, `8090`).
   - Puerto `5432` (interno en la red Docker; no requiere colisionar con PostgreSQL local del anfitrión).

---

## 3. Procedimiento de Instalación Paso a Paso

### Paso 3.1: Clonación del Repositorio y Selección de Rama

Una vez que el repositorio privado `SGM-TB-Transporte` esté habilitado en GitHub, clónalo en tu entorno de desarrollo:

```bash
# Clonar mediante SSH (recomendado) o HTTPS
git clone git@github.com:<organizacion>/SGM-TB-Transporte.git odoo16-sgmtb
cd odoo16-sgmtb

# Cambiar inmediatamente a la rama de integración 'develop'
git checkout develop
```

> [!IMPORTANT]
> **Nunca** trabajes directamente sobre la rama `main` ni realices commits sin haber creado previamente tu rama `feature/` correspondiente.

---

### Paso 3.2: Configuración de Variables de Entorno Locales

El repositorio incluye la plantilla segura `.env.example`. Crea tu archivo local `.env`:

```bash
cp .env.example .env
```

Edita el archivo `.env` según tu máquina local:
```env
# Conexión PostgreSQL
POSTGRES_DB=postgres
POSTGRES_USER=odoo
POSTGRES_PASSWORD=tu_password_local_seguro

# Puerto de Exposición en el Host
ODOO_HOST_PORT=8070

# Parámetros para desarrollo
TRACCAR_WEBHOOK_SECRET=token_desarrollo_local_123
```

> [!WARNING]
> El archivo `.env` está expresamente excluido en `.gitignore`. **Bajo ninguna circunstancia** debes forzar su subida a Git (`git add -f .env`).

---

### Paso 3.3: Inspección de Archivos de Configuración

Comprueba la estructura de directorios:
- `./addons`: Contiene los módulos personalizados, incluyendo `transporte_core`.
- `./config/odoo.conf`: Configuración del servidor Odoo montada en `/etc/odoo`.
- `./scripts`: Herramientas de soporte y carga de datos.
- `./docs`: Documentación técnica y bitácoras individuales.

---

### Paso 3.4: Arranque de los Contenedores Docker

Inicia los servicios en segundo plano:

```bash
docker compose up -d
```

Verifica que los contenedores estén levantados y saludables:
```bash
docker compose ps
```
Deberás observar activos:
- `odoo16_web` (escuchando en el puerto configurado en el host, ej. `0.0.0.0:8070->8069/tcp`).
- `odoo16_db` (PostgreSQL 15 escuchando internamente en el puerto `5432`).

---

### Paso 3.5: Creación de la Base de Datos Individual de Desarrollo

Cada desarrollador debe crear su **propia base de datos de desarrollo**, evitando colisiones o copias directas de bases de datos ajenas.

**Convención de Nombres de Base de Datos:**
- Formato: `sgmtb_dev_<alias_integrante>`
- Ejemplos: `sgmtb_dev_devops`, `sgmtb_dev_flota`, `sgmtb_dev_gps`, `sgmtb_dev_calidad`.

Ejecuta la inicialización de tu base con los módulos oficiales requeridos (`fleet`, `hr`, `mail`) y el núcleo operativo `transporte_core`:

```bash
# Inicializar la base e instalar módulos requeridos de forma limpia
docker exec odoo16_web /entrypoint.sh odoo \
  -d sgmtb_dev_tu_nombre \
  -i fleet,hr,mail,transporte_core \
  --without-demo=all \
  --no-http \
  --stop-after-init
```

---

### Paso 3.6: Carga de Datos de Demostración (DEMO SGM-TB)

Para contar de inmediato con rutas, paradas, buses y conductores sin inventar datos manualmente, ejecuta el script idempotente de carga DEMO:

```bash
# Inyectar datos representativos en tu base local
docker exec -i odoo16_web python3 < scripts/cargar_datos_demo.py
```

El script reportará la creación o verificación de:
- 12 Paradas georreferenciadas (`DEMO-PAR-01` a `DEMO-PAR-12`).
- 3 Rutas urbanas e interurbanas ordenadas por secuencias (`DEMO-RUT-01` a `DEMO-RUT-03`).
- 4 Buses de diferentes capacidades (`TB-DEMO-01` a `TB-DEMO-04`).
- 4 Conductores con licencias vigentes (`LIC-DEMO-001` a `LIC-DEMO-003`).
- 2 Viajes de prueba (uno programado y uno en borrador).

---

### Paso 3.7: Ejecución de la Suite de Pruebas Automatizadas

Antes de iniciar cualquier desarrollo, valida que todo el entorno funcione al 100%:

```bash
docker exec odoo16_web /entrypoint.sh odoo \
  -d sgmtb_dev_tu_nombre \
  -u transporte_core \
  --test-enable \
  --test-tags /transporte_core \
  --no-http \
  --stop-after-init
```

**Resultado Esperado:**
- 35 pruebas automatizadas descubiertas y ejecutadas exitosamente.
- `0 failed, 0 error(s) of 35 tests`.

---

### Paso 3.8: Acceso a la Interfaz Web

Abre tu navegador web e ingresa a:
`http://localhost:8070` (o el puerto configurado en tu `.env`).

1. Selecciona tu base de datos: `sgmtb_dev_tu_nombre`.
2. Inicia sesión con las credenciales de administrador (usuario: `admin`, contraseña configurada).
3. Accede al menú **Transporte en Buses** en la barra superior izquierda para inspeccionar las rutas, paradas, buses, conductores y despachos.

---

## 4. Diagnóstico y Solución de Problemas Frecuentes

### Problema 1: Puerto en uso (`Address already in use`)
- **Síntoma:** Docker Compose falla indicando que el puerto `8070` o `8069` está ocupado.
- **Solución:** Cambia `ODOO_HOST_PORT` en tu `.env` a un puerto libre (ej. `8085` o `8090`) y recrea el contenedor: `docker compose up -d web`.

### Problema 2: Permisos de archivos en WSL2 / Linux
- **Síntoma:** Error de permisos al intentar escribir logs o crear archivos en `./addons`.
- **Solución:** Asigna permisos de lectura/escritura a tu usuario:
  ```bash
  sudo chown -R $USER:$USER ./addons ./config ./scripts ./docs
  chmod -R u+rw ./addons
  ```

### Problema 3: Odoo no detecta los cambios en el código Python
- **Síntoma:** Se modifica un archivo `.py` en `transporte_core` pero no se refleja en la interfaz.
- **Solución:** En desarrollo, reinicia el contenedor de Odoo y actualiza el módulo:
  ```bash
  docker compose restart web
  docker exec odoo16_web /entrypoint.sh odoo -d sgmtb_dev_tu_nombre -u transporte_core --no-http --stop-after-init
  ```

---

## 5. Reglas de Aislamiento de Bases de Datos

> [!CAUTION]
> 1. **Prohibido Volcar Bases Producción al Repositorio:** Nunca subas archivos `.dump` o `.sql` a Git.
> 2. **Bases Locales Independientes:** Cada integrante debe mantener su propia base. Las discrepancias de datos se resuelven mediante scripts idempotentes en `./scripts/` o datos demo en `demo/`.
> 3. **Mantenimiento y Encuestas:** No instalar módulos como `maintenance` ni `survey` a menos que sea explícitamente acordado por el equipo.

