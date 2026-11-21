# Guion de Demostración y Defensa

## 0. Antes de la defensa
- `docker compose up -d && docker compose --profile tunel up -d`; Traccar Client a 30 s apuntando al túnel.
- En Odoo, el bus de prueba tiene su `ID de dispositivo Traccar` y el viaje del día está **Programado**.
- Dashboard filtrado «Solo reales» para mostrar los datos del teléfono; «Solo simulados» para los escenarios.
- Plan B sin teléfono ni Internet: los mapas cargan igual (Leaflet va incluido; sin Internet el fondo de calles es
  gris). La cadena real Traccar → Odoo se demuestra con `bash scripts/prueba_integracion_traccar.sh` (Traccar efímero,
  posiciones por el protocolo de Traccar Client, ~40 s).

## 1. Flujo en vivo (≈ 10 min)
0. **Login y pantalla de Inicio** (SGM-TB Transporte ▸ Inicio): indicadores en vivo de los últimos 7 días, buses en
   ruta con su avance, incidencias más frecuentes y accesos directos según el rol. Si los datos incluyen recorridos
   simulados aparece el aviso «incluye N SIMULADOS» (nada simulado se presenta como real).
1. **Registro del vehículo:** SGM-TB Transporte ▸ Flota y Personal ▸ Buses ▸ bus con dispositivo GPS asociado.
2. **Rutas y paradas:** Rutas y Paradas ▸ Líneas y Rutas: origen, destino, distancia y tiempo estimados,
   secuencia de ≥ 4 paradas con minutos desde el origen; pestaña *Corredor de referencia*. Calidad del Servicio ▸
   **Mapa de rutas**: el trazado contra el que se detectan desvíos, el radio de cada parada y el % de cumplimiento y
   puntualidad histórico de cada ruta.
3. **Asignación:** Operación de Viajes ▸ Viajes ▸ nuevo (ruta + bus + conductor + hora) ▸ *Programar* (se congelan
   las horas de cada parada) ▸ *Iniciar recorrido*. Mostrar que el mismo bus tiene otros viajes en otras rutas.
4. **Recorrido con el teléfono** (datos móviles): Telemetría GPS ▸ Mapa de Buses (refresca cada 15 s) y
   Log de sincronización (nuevas / duplicados = 0).
5. En el viaje: paradas pasando a *Atendida (GPS)* con su hora real y retraso; pestaña *Evaluación de calidad*
   con el retraso acumulado en vivo.
6. *Finalizar viaje* → resultado **Cumple / Incumple** e incidencias generadas automáticamente; botón *Informe PDF*.
7. **Dashboard** (Calidad del Servicio ▸ Dashboard), organizado en pestañas:
   *Resumen* (8 KPIs con semáforo, Pareto y comparación por ruta; botón **Fórmulas** para mostrar cómo se calcula
   cada uno), *Flota en vivo* (tabla de buses + mapa), *Rutas y períodos*, *Historial* y *Calidad del software*.
   Registrar un viaje nuevo y mostrar que los indicadores cambian.

## 2. Caso de cumplimiento y caso de incumplimiento
| Caso | Dónde mostrarlo | Regla que explica el resultado |
| :--- | :--- | :--- |
| Cumple | Viaje real a tiempo, o simulado «puntual» | Todas las paradas en [−2, +5] min, destino alcanzado, ninguna posición > 150 m del corredor |
| Incumple – retraso | Simulado «atrasado» | Salida +10 min → retraso de salida, de cada parada y de llegada > 5 min |
| Incumple – parada omitida | Simulado «parada omitida» | El bus pasa a 110 m de una parada de radio 35 m: ni la muestra ni el tramo entran al radio |
| Incumple – desvío | Simulado «desviación» (mapa del viaje) | ≥ 3 posiciones seguidas a más de 150 m del trazado (máx. ~450 m) |
| Incumple – incompleto | Simulado «incompleto» | Destino no alcanzado → recorrido incompleto + 3 paradas omitidas |
| Ejemplo del enunciado | Prueba `test_cp05` / explicación | 08:15 programada, tolerancia 5, llegada 08:23 → retraso de 8 min |

## 3. Respuestas a las preguntas del enunciado
| Pregunta | Dónde se responde |
| :--- | :--- |
| ¿Dónde se encuentra actualmente el vehículo? | Inicio ▸ «En ruta ahora»; Dashboard ▸ pestaña *Flota en vivo* (tabla + mapa); Mapa de Buses (posición, hora, velocidad, señal) |
| ¿Qué ruta está realizando? | Inicio ▸ «En ruta ahora»; Dashboard ▸ *Flota en vivo*, columna «Recorrido en curso» |
| ¿Qué paradas ha visitado? | Inicio ▸ barra de avance (n/m); Dashboard ▸ *Flota en vivo*, columna «Paradas» (barra n de m; nombres al pasar el ratón); viaje ▸ Control de paradas |
| ¿Está cumpliendo los horarios? | Dashboard ▸ *Flota en vivo*, columna «Estado» (A tiempo / Con retraso / Desviado); viaje ▸ puntualidad por parada |
| ¿Cuánto retraso ha acumulado? | Dashboard ▸ *Flota en vivo*, columna «Retraso» (última parada visitada) |
| ¿Se ha desviado de su ruta? | Dashboard ▸ *Flota en vivo*, estado «Desviado»; viaje ▸ alejamiento máximo y % fuera del corredor |
| ¿Cuántos recorridos ha realizado? | Dashboard ▸ columna «Recorridos» por bus y KPI de recorridos evaluados |
| ¿Qué porcentaje se ha cumplido correctamente? | Inicio y Dashboard ▸ KPI «Cumplimiento de rutas»; por ruta en el Mapa de rutas y en la lista de rutas |
| ¿Cuáles son las incidencias más frecuentes? | Gráfico de Pareto de incidencias |
| ¿Qué tan confiable es el sistema? | KPIs de calidad del software: integridad GPS, exactitud Traccar ↔ Odoo, tiempo de respuesta, detección correcta |
| ¿Qué mejoras se realizaron? | `docs/MEJORA_CONTINUA.md`: geocerca por tramo (detección correcta 90 % → 100 %), estándar de 30 s, pruebas de interfaz que ya no se saltan, mapas sin CDN y refactor de las reglas (complejidad 46 → ≤ 15) |

## 4. Pruebas y calidad (para la exposición)
`bash scripts/ejecutar_pruebas.sh` → 128 pytest + 96 pruebas Odoo + rendimiento + 6 de interfaz (navegador real)
+ 2 de integración en vivo con Traccar; matriz en `docs/PLAN_PRUEBAS.md`; ISO 25010 y SonarQube (Quality Gate
aprobado, 0 bugs, 0 vulnerabilidades) en `docs/CALIDAD_SOFTWARE.md`.
