# Examen final: Procesamiento de Datos en Tiempo Real

**Duración:** 120 minutos  
**Puntaje:** 100 puntos  
**Reactivos:** 20  
**Modalidad:** Individual

Nombre: ____________________________________  
Fecha: _____________________________________

## Instrucciones

- Justifica tus respuestas con la evidencia proporcionada. Una afirmación correcta sin razonamiento puede recibir crédito parcial.
- Puedes usar una calculadora básica y el apéndice de referencia incluido al final.
- No se evalúa la memorización de comandos, puertos o sintaxis exacta.
- Cuando propongas una solución, distingue entre **corregir el incidente actual** y **prevenir o detectar la recurrencia**.
- Si necesitas hacer una suposición, escríbela explícitamente.
- No hay penalización por respuestas incorrectas.

---

## Sección A: escenarios de respuesta restringida — 16 puntos

Selecciona la mejor respuesta. Cada reactivo vale 2 puntos.

### 1. Saturación de Postgres

Un generador de carga ejecuta el mismo `INSERT` en un Postgres limitado a dos CPU. No existe contención sobre una fila compartida.

| Conexiones | TPS | p99 | CPU | Utilización de disco | Esperas por locks |
|---:|---:|---:|---:|---:|---:|
| 20 | 1,850 | 12 ms | 38% | 18% | 0% |
| 50 | 4,120 | 23 ms | 74% | 24% | 0% |
| 100 | 4,260 | 91 ms | 98% | 27% | 0% |
| 200 | 3,780 | 440 ms | 100% | 29% | 0% |

¿Cuál intervención está mejor sustentada por la evidencia?

A. Aumentar `max_connections` a 1,000.  
B. Desactivar `synchronous_commit`, porque el disco está saturado.  
C. Reducir el trabajo de CPU por transacción —por ejemplo, revisar índices/código— o asignar más CPU.  
D. Ejecutar `VACUUM FULL`, porque los locks explican el colapso.

### 2. Riesgo operativo de CDC

El conector CDC dejó de funcionar hace 40 minutos. En Postgres, el `restart_lsn` del slot no avanza y el directorio de WAL crece rápidamente. Kafka y la red están disponibles.

¿Cuál es la mejor primera acción?

A. Reiniciar o reparar el conector y verificar que el LSN confirmado avance.  
B. Aumentar `max_wal_size`; esto permitirá que Postgres recicle el WAL retenido por el slot.  
C. Crear un segundo slot de replicación para repartir el WAL.  
D. Aumentar la frecuencia de un proceso de polling sobre las tablas fuente.

### 3. Particiones y orden en Kafka

Un tópico tiene seis particiones. El productor utiliza `customer_id` como clave y existen dos consumidores en el mismo consumer group.

¿Qué garantía es correcta?

A. Existe orden total entre todos los eventos del tópico.  
B. Los eventos de un mismo `customer_id` conservan su orden dentro de su partición, aunque la propiedad de esa partición cambie durante un rebalanceo.  
C. Ambos consumidores procesan cada evento para proporcionar redundancia.  
D. Kafka conserva el orden entre particiones siempre que el productor use `acks=all`.

### 4. Trigger, ventana y watermark

Una consulta usa ventanas tumbling de 5 minutos, un trigger de 2 segundos y un watermark de 10 minutos.

¿Cuál afirmación es correcta?

A. El trigger determina a qué ventana pertenece cada evento.  
B. El watermark hace que Spark ejecute un micro-batch cada 10 minutos.  
C. La ventana agrupa por event time; el trigger controla la frecuencia de ejecución; el watermark limita cuánto tiempo se espera y conserva estado para datos tardíos.  
D. Reducir el trigger de 2 segundos a 1 segundo permite aceptar eventos dos veces más tardíos.

### 5. Límite de un checkpoint

Un job de Spark lee Kafka, envía resultados con `POST` a una API externa no idempotente y después guarda progreso en su checkpoint. El proceso falla después de que la API aceptó una solicitud pero antes de que el checkpoint refleje el avance.

¿Qué puede ocurrir al reiniciar?

A. Spark omite el registro y se pierde necesariamente.  
B. Spark puede repetir la solicitud y producir un efecto duplicado.  
C. El checkpoint revierte automáticamente la operación en la API.  
D. Kafka elimina el registro porque la API ya lo recibió.

### 6. Lectura de una distribución de latencia

En el mismo workload se obtuvieron estos resultados:

| Motor | p50 | p99 | Throughput sostenido |
|---|---:|---:|---:|
| Spark | 410 ms | 2,800 ms | 70,000 eventos/s |
| Flink | 120 ms | 420 ms | 51,000 eventos/s |

El SLA exige p99 menor a 1 segundo y el workload produce 40,000 eventos/s.

¿Cuál conclusión está respaldada?

A. Flink satisface el SLA en esta prueba; esto no demuestra que siempre sea mejor que Spark.  
B. Spark satisface el SLA porque su p50 es menor a 1 segundo.  
C. Ningún motor satisface el SLA porque Flink tiene menor throughput máximo.  
D. Flink garantiza p99 menor a 1 segundo para cualquier workload futuro.

### 7. Presión de merges en ClickHouse

Una tabla recibe miles de inserts de una sola fila por segundo. `system.parts` muestra miles de partes activas y `system.merges` permanece ocupado; la latencia de consulta aumentó de 180 ms a 8 s.

¿Cuál cambio ataca directamente la causa?

A. Enviar bloques más pequeños con mayor frecuencia.  
B. Acumular eventos y escribir bloques más grandes con una latencia de flush acotada.  
C. Agregar otra materialized view sobre cada insert individual.  
D. Cambiar todas las columnas numéricas a `String`.

### 8. Evolución segura de esquema

Se necesita agregar `discount_code` a un flujo Postgres → CDC → Kafka → procesador → ClickHouse. Durante el despliegue coexistirán productores y consumidores de versiones distintas.

¿Cuál secuencia es más segura?

A. Hacer el campo obligatorio sin default en el productor y después actualizar consumidores.  
B. Detener todo el pipeline, borrar el tópico y desplegar todas las capas a la vez.  
C. Agregar primero soporte downstream para un campo opcional/con default, desplegar consumidores, después empezar a producirlo y endurecer el contrato sólo cuando las versiones antiguas hayan desaparecido.  
D. Renombrar un campo existente para evitar crear una nueva versión del esquema.

---

## Sección B: respuestas breves con evidencia — 36 puntos

Cada reactivo vale 6 puntos. Responde de forma concreta; no se requiere escribir código completo.

### 9. Por qué cambia el rendimiento analítico

La misma consulta calcula `SUM(fare_amount)` por día para viajes de enero:

```text
Postgres
  Parallel Seq Scan on trips
  rows examined: 400,000,000
  row width: 180 bytes
  bytes read: 72 GB
  elapsed: 38.2 s

DuckDB sobre Parquet
  projected columns: pickup_at, fare_amount, zone_id  (3 de 22)
  row groups read: 8 de 96
  bytes read: 1.8 GB
  elapsed: 0.74 s
```

Explica al menos tres mecanismos que sustentan la diferencia observada. Después indica por qué Postgres todavía podría ser la opción correcta para actualizar una sola fila por llave primaria.

### 10. Snapshot inicial y posición del WAL

Un consumidor CDC debe copiar una tabla existente y continuar con cambios en vivo. El proceso registra una posición del WAL, `LSN 5000`, abre un snapshot consistente, copia las filas y después consume los eventos del WAL a partir de `LSN 5000`.

Explica por qué la posición y el snapshot deben coordinarse. Describe también cómo aplicar y confirmar los eventos para que un crash no produzca pérdida silenciosa ni resultados finales duplicados.

### 11. Elegir un watermark

Para un stream de pagos:

- 99.5% de los eventos llega con menos de 3 minutos de retraso.
- El 0.5% restante puede llegar hasta 25 minutos tarde.
- Un watermark de 30 minutos mantiene aproximadamente 120 GB de estado y el job está cerca de su límite de memoria.
- El producto exige resultados operativos en menos de 5 minutos.

Propón una política de watermark y manejo de datos excepcionalmente tardíos. Explica el tradeoff entre completitud, latencia y uso de estado.

### 12. Spark o Flink según el SLA

Una prueba con el volumen pico esperado produjo:

| Motor | p50 | p99 | Throughput | CPU |
|---|---:|---:|---:|---:|
| Spark, trigger 1 s | 1.3 s | 3.6 s | 75,000/s | 55% |
| Flink | 0.12 s | 0.42 s | 52,000/s | 76% |

Ambos workloads alcanzan como máximo 40,000 eventos/s:

1. Dashboard operativo con SLA de 10 segundos.
2. Detección de fraude con SLA p99 de 500 ms.

Recomienda un motor para cada workload. Justifica con los datos y menciona una limitación de la recomendación.

### 13. Frescura frente a salud de ClickHouse

El SLA exige frescura menor a 5 s y p95 de consulta menor a 300 ms. El pipeline actualmente hace flush en cuanto recibe cualquier evento:

```text
filas por insert:              1–20
frescura end-to-end p95:      0.6 s
partes activas:               4,200
merges activos:               31
CPU de ClickHouse:            100%
latencia de consulta p95:     4.8 s
```

Explica la cadena causal. Propón un cambio que recupere la latencia de consulta sin violar necesariamente el SLA de frescura.

### 14. Capacidad de Kafka

Un clúster recibe **12 MB/s** de datos, requiere **72 horas** de retención y usa factor de replicación **3**. Se desea además **25% de espacio libre** como margen operativo. Usa unidades decimales: 1 TB = 1,000,000 MB.

Calcula la capacidad mínima aproximada que debe provisionarse para los datos retenidos, incluyendo réplicas y margen. Indica además una métrica y un umbral de alerta razonable para evitar un incidente de disco lleno.

---

## Sección C: cálculos y trazas de ejecución — 24 puntos

Cada reactivo vale 8 puntos. Muestra tu razonamiento.

### 15. Falla parcial en un ETL incremental

El pipeline procesa intervalos horarios con estos pasos:

1. Lee `last_success = 10:00`.
2. Extrae 1,000 filas del intervalo `[10:00, 11:00)`.
3. Actualiza `last_success = 11:00`.
4. Inserta las filas en el destino en batches con autocommit y sin llave única.

El proceso falla después de insertar 600 filas. Al reiniciar, vuelve a leer `last_success`.

1. Traza qué sucede con las 1,000 filas después del crash y del reinicio.
2. Rediseña el orden y la escritura para que el intervalo pueda reintentarse sin pérdida, duplicados finales ni exposición permanente de un resultado parcial.

### 16. Offsets, crash y duplicados

En este ejercicio, el offset comprometido representa el **siguiente** registro que debe leerse.

```text
Offsets comprometidos antes del batch:
  P0 = 100
  P1 = 200

Registros procesados y escritos en un sink append-only:
  P0: 100–109
  P1: 200–209

El consumidor compromete P0 = 110.
El proceso falla antes de comprometer P1 = 210.
```

1. Al reiniciar el consumer group, ¿qué offsets se vuelven a leer en cada partición y qué duplicados o pérdidas aparecen en el sink?
2. Propón una estrategia que preserve la corrección aun si el proceso falla entre escribir el sink y comprometer offsets.

### 17. Event time, ventanas y datos tardíos

Se usan ventanas tumbling de 5 minutos, alineadas al reloj, y un watermark de 2 minutos:

```text
watermark = máximo event_time observado − 2 minutos
```

Una ventana se finaliza cuando el watermark alcanza o supera su límite superior. Un evento cuya ventana ya fue finalizada se descarta. Los eventos llegan en este orden:

| Llegada | event_time | amount |
|---|---|---:|
| A | 12:01:00 | 10 |
| B | 12:04:00 | 20 |
| C | 12:08:00 | 5 |
| D | 12:03:00 | 7 |
| E | 12:11:00 | 4 |
| F | 12:12:30 | 6 |

1. Traza el avance del watermark desde C hasta F. Indica cuándo se finalizan las ventanas `[12:00, 12:05)` y `[12:05, 12:10)`, sus sumas finales y cualquier evento descartado.
2. Si el trigger cambia de 1 a 10 segundos, ¿cambia la pertenencia de los eventos a las ventanas? Explica brevemente.

---

## Sección D: casos integradores — 24 puntos

Cada caso vale 8 puntos.

### 18. Quorum, fallas y latencia

Una réplica Raft de tres nodos tiene líder A. Para simplificar, asume que una escritura se confirma cuando A y al menos un follower persisten la entrada.

```text
Latencia A ↔ B: 20 ms
Latencia A ↔ C: 120 ms
```

1. Compara disponibilidad y latencia de escritura aproximada en tres estados: todos sanos; B fuera de línea; B y C fuera de línea.
2. Explica por qué agregar réplicas no implica automáticamente mayor throughput de escritura que un Postgres de un solo nodo.

### 19. Exactly-once fuera del procesador

Un job lee 500 eventos de Kafka por micro-batch y llama una API de cobro una vez por evento. La API acepta opcionalmente un encabezado `Idempotency-Key`, pero el job no lo utiliza. Después de 400 respuestas exitosas, el driver muere antes de confirmar el checkpoint del batch.

1. Explica qué puede ocurrir al reiniciar y por qué el checkpoint no proporciona exactly-once end-to-end.
2. Diseña una estrategia de entrega segura utilizando las capacidades descritas. Incluye cómo tratarías errores permanentes de registros individuales sin bloquear todo el stream.

### 20. Pipeline sano, datos incorrectos

El pipeline es Postgres → Debezium → Kafka → Spark → ClickHouse → API. Los dashboards técnicos están verdes, pero el total de órdenes activas mostrado por la API es demasiado alto.

```text
Postgres:
  órdenes activas reales                         98,000

Eventos de Debezium durante la última hora:
  op=c                                           1,100
  op=u                                           4,800
  op=d                                           2,000

Spark:
  input rows                                     normal
  failed batches                                 0
  filtro actual                                  after IS NOT NULL

ClickHouse/API:
  órdenes consideradas activas                  100,000
  frescura                                       2.1 s
  latencia de consulta                           140 ms
```

Un evento de delete de Debezium tiene `op=d`, datos anteriores en `before` y `after=null`.

1. Identifica la causa raíz y explica por qué lag, frescura, latencia y errores pueden permanecer normales.
2. Propón una corrección segura para representar deletes downstream y una señal de prevención o calidad de datos que detecte este problema pronto.

---

# Apéndice de referencia

## Fórmulas

```text
crecimiento de backlog = max(0, tasa_productor − tasa_consumidor)

almacenamiento Kafka =
  throughput_bytes_por_segundo × retención_segundos × factor_de_replicación

capacidad con margen = almacenamiento / fracción_utilizable

quorum mayoritario = floor(n / 2) + 1
```

Con 25% de espacio libre, la fracción utilizable es `0.75`.

## Convenciones

- Una ventana `[inicio, fin)` incluye `inicio` y excluye `fin`.
- En las trazas de Kafka de este examen, el offset comprometido es el siguiente registro que debe leerse.
- `p99 = 2 s` significa que 99% de las observaciones fue menor o igual a aproximadamente 2 segundos; no describe solamente el promedio.
- En CDC de Postgres, un LSN identifica una posición en el WAL.
