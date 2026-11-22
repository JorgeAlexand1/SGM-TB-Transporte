# Guía 2 — Configurar y probar el celular (Traccar Client)

Para quien lleva el teléfono en el recorrido. El servidor lo prepara otra persona con
[`GUIA_LEVANTAR_APLICACION.md`](GUIA_LEVANTAR_APLICACION.md). El teléfono **solo envía su ubicación**; todo lo
demás (rutas, retrasos, incidencias, dashboard) se ve en Odoo desde la PC.

## 1. Qué necesita antes de salir

| Dato | Quién lo da | Ejemplo |
| :--- | :--- | :--- |
| **URL del túnel** | La persona del servidor (cambia cada vez que se reinicia el túnel) | `https://algo-algo.trycloudflare.com` |
| **Identificador del bus** | Según el bus que va a simular | `sgmtb-bus01` o `sgmtb-bus02` |
| Teléfono Android o iPhone con **datos móviles** y batería > 40 % | Usted | — |

Con **un solo teléfono** se pueden simular los dos buses: cambie el *identificador* antes de cada recorrido (un
identificador = un bus).

## 2. Instalar y configurar Traccar Client

1. Instale **Traccar Client** (Play Store / App Store; app oficial «Traccar Client»).
2. Conceda el permiso de ubicación **«Permitir siempre»** (en iPhone: «Siempre» y ubicación precisa).
3. Configure:

| Campo | Valor |
| :--- | :--- |
| Identificador del dispositivo | `sgmtb-bus01` (o `sgmtb-bus02`) |
| URL del servidor | la URL `https://…trycloudflare.com` **sin puerto y sin barra final** |
| Precisión de ubicación | Alta |
| Frecuencia | **30 segundos** (nunca 300 s: con intervalos largos se pierden paradas) |
| Distancia / ángulo | 0 |

4. **Android:** *Ajustes ▸ Aplicaciones ▸ Traccar Client ▸ Batería ▸ Sin restricciones*, para que el sistema no
   duerma la app. **iPhone:** deje la app en primer plano o con actualización en segundo plano activa.
5. **Apague el Wi-Fi.** El enunciado exige demostrar que las posiciones llegan por **datos móviles**, no por la
   red local.

📸 Evidencia **A2-04**: pantalla de configuración de Traccar Client.

## 3. Prueba 1 — ¿llega mi ubicación? (2 minutos, en cualquier lugar)

1. En Traccar Client active **«Estado del servicio»** (Iniciar servicio). Debe verse el estado *Enviando* /
   mensajes sin error.
2. Pida a la persona del servidor que abra http://localhost:8082 ▸ *Dispositivos*: su bus debe pasar a **Online**
   con su posición en el mapa.
3. En Odoo (*Telemetría GPS ▸ Mapa de Buses*, se refresca cada 15 s): el bus aparece con hora, velocidad y señal.
   *Posiciones GPS* debe mostrar registros nuevos con su hora local.
4. Revisar el **Log de sincronización**: posiciones nuevas > 0 y, al repetir la sincronización, 0 nuevas
   (**sin duplicados**).

| Resultado | Qué significa |
| :--- | :--- |
| Aparece en Traccar y en Odoo | Cadena completa teléfono → túnel → Traccar → Odoo ✅ |
| Aparece en Traccar pero no en Odoo | Problema del servidor: avise a quien lo administra |
| No aparece en Traccar | URL equivocada/caducada, sin datos móviles o app sin permiso de ubicación |

📸 Evidencias **A2-05** (Traccar con el bus *Online* mientras el teléfono usa datos móviles) y **A3**
(la misma posición en *Posiciones GPS* de Odoo).

## 4. Prueba 2 — un recorrido real evaluado

Necesita rutas reales con paradas donde usted pueda pasar físicamente (las rutas `DEMO-*` son de demostración;
cómo crear las reales: [`GUIA_TRABAJO_CAMPO.md`](GUIA_TRABAJO_CAMPO.md) §5). El procedimiento completo y el plan
de 10 recorridos está en esa guía (§6–§8); este es el resumen para quien lleva el teléfono:

| Paso | Dónde | Qué hacer |
| :-: | :--- | :--- |
| 1 | PC (otra persona) | Crear el viaje: ruta, bus, conductor y **hora de salida real** ▸ *Programar* |
| 2 | Teléfono | Estando en la **parada 1**: Traccar Client ▸ **Iniciar servicio** |
| 3 | PC | En el viaje ▸ **Iniciar recorrido** (solo cuentan las posiciones posteriores a este clic) |
| 4 | Calle | Seguir la ruta; en cada parada detenerse unos segundos. Las paradas pasan a *Atendida (GPS)* |
| 5 | PC | Al llegar al final ▸ **Finalizar viaje**: aparece **Cumple / Incumple** con sus incidencias |
| 6 | Teléfono | **Detener servicio** |

### Qué probar: un caso de cumplimiento y varios de incumplimiento
La defensa exige **al menos un cumplimiento y un incumplimiento** con datos reales del teléfono. Escenarios que
puede provocar a propósito:

| Escenario | Qué hacer | Esperado en Odoo |
| :--- | :--- | :--- |
| **Puntual** (cumple) | Salir a la hora y seguir la ruta | *Cumple*, sin incidencias |
| Salida tarde | Programar 8:00 y salir 8:10 | Retraso de salida, de paradas y de llegada |
| Lento | Esperar ~3 min en cada parada | Retrasos crecientes + diferencia de tiempo |
| Parada omitida | Pasar por una calle paralela a > 100 m de una parada | *Parada omitida* |
| Desvío | Salir > 200 m de la ruta durante ≥ 2 min | *Desviación de la ruta* |
| Incompleto | Llegar solo a la parada 3 y finalizar | *Recorrido incompleto* + paradas omitidas |
| Pérdida de señal | A mitad de tramo, **Detener servicio** 5 min y reiniciarlo | *Pérdida de señal GPS* |

⚠️ El **modo avión no sirve** para simular pérdida de señal: Traccar Client guarda posiciones sin conexión y las
envía después. Hay que *detener el servicio* en la app.

## 5. Reglas que usa el sistema (para explicarlas en la defensa)

| Regla | Valor |
| :--- | :--- |
| Parada visitada | El bus entra al **radio de la parada** (30–50 m) o su tramo entre dos muestras lo cruza |
| Puntualidad | Llegada entre **−2 y +5 min** del horario programado (ejemplo: 08:15 + 5 min de tolerancia, llegada 08:23 = **8 min de retraso**, incumple) |
| Desvío | ≥ 3 posiciones seguidas a más de **150 m** del trazado |
| Pérdida de señal | Hueco de **más de 3 min** entre posiciones dentro del viaje (queda registrada como incidencia, pero no hace que el viaje incumpla). Aparte, un bus sin reportes durante 5 min se marca «sin señal» en el mapa |
| Recorrido incompleto | No se alcanza la parada final |

## 6. Problemas frecuentes

| Síntoma | Solución |
| :--- | :--- |
| «Error de red» / no envía | Revise la URL (sin puerto ni `/` final), que haya datos móviles y que el túnel siga activo |
| Dejó de funcionar a media jornada | El túnel se reinició y la URL cambió: pida la nueva y actualícela |
| Posiciones con hora desplazada ~5 h | Zona horaria del usuario de Odoo ≠ `America/Guayaquil` (se corrige en el servidor) |
| Faltan paradas aunque pasó | Frecuencia > 30 s, GPS impreciso (use precisión *Alta* y cielo abierto) o radio muy pequeño |
| Todo sale «atrasado» | Hora de salida programada distinta de la real, o zona horaria mal puesta |
| La app se detiene sola | Quite la restricción de batería (§2, paso 4) |

## 7. Evidencias que debe tomar

| ID | Captura |
| :-: | :--- |
| A2-04 | Configuración de Traccar Client (identificador, URL, 30 s) |
| A2-05 | Traccar Online con el teléfono en **datos móviles** (Wi-Fi apagado visible) |
| A3 | Posiciones del teléfono en Odoo (*Posiciones GPS* y *Mapa de Buses*) |
| A5 | Viaje finalizado con paradas *Atendida (GPS)*, trazado en el mapa e incidencias |
| A6/A8 | Un caso **Cumple** y uno **Incumple**, y el dashboard actualizado después de ellos |
