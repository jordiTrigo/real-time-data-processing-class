# Examen final: Procesamiento de Datos en Tiempo Real

**Duración:** 120 minutos  
**Puntaje:** 100 puntos  
**Reactivos:** 20  
**Modalidad:** Individual

Nombre: ____________________________________  
Fecha: _____________________________________

## Instrucciones

- Selecciona una sola respuesta en cada reactivo: la opción que mejor integra la evidencia y las garantías descritas.
- Puedes usar una calculadora básica y el apéndice de referencia incluido al final.
- No se evalúa la memorización de comandos, puertos o sintaxis exacta.
- No hay penalización por respuestas incorrectas.

---

## Sección A: fundamentos y diagnóstico — 16 puntos

Cada reactivo vale 2 puntos.

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

## Sección B: arquitectura y decisiones operativas — 36 puntos

Cada reactivo vale 6 puntos.

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

¿Cuál explicación está mejor sustentada por la evidencia?

A. DuckDB es más rápido únicamente porque usa más CPU; el formato de almacenamiento no influye, y Postgres conviene para una actualización puntual porque siempre hace un scan completo.  
B. DuckDB puede podar 19 columnas y 88 row groups, aprovechar compresión y ejecución vectorizada, y así leer mucho menos; Postgres aún puede ser mejor para una actualización puntual gracias al índice, su almacenamiento por filas y sus garantías transaccionales.  
C. La diferencia demuestra que todo sistema columnar es siempre más rápido; Postgres conviene para la actualización porque no utiliza WAL ni MVCC.  
D. DuckDB evita leer las 400 millones de filas exclusivamente por tener un índice B-tree; Postgres debe reescribir toda la tabla para actualizar una fila.

### 10. Snapshot inicial y posición del WAL

Un consumidor CDC debe copiar una tabla existente y continuar con cambios en vivo. El proceso registra una posición del WAL, `LSN 5000`, abre un snapshot consistente, copia las filas y después consume los eventos del WAL a partir de `LSN 5000`.

¿Cuál diseño evita gaps y mantiene un resultado final correcto ante reintentos?

A. Copiar la tabla sin snapshot, empezar el WAL en su posición más reciente y confirmar cada LSN antes de escribirlo al destino.  
B. Abrir cualquier snapshot, copiarlo y consumir sólo eventos posteriores al fin de la copia; los deletes pueden ignorarse porque no contienen `after`.  
C. Registrar `LSN 5000`, confirmar inmediatamente esa posición y usar inserts append-only; si hay un crash, eliminar manualmente todo el destino.  
D. Asociar el snapshot consistente con `LSN 5000`, reproducir desde esa frontera, aplicar upserts y deletes de forma idempotente y confirmar cada avance sólo después de que el efecto downstream sea durable.

### 11. Elegir un watermark

Para un stream de pagos:

- 99.5% de los eventos llega con menos de 3 minutos de retraso.
- El 0.5% restante puede llegar hasta 25 minutos tarde.
- Un watermark de 30 minutos mantiene aproximadamente 120 GB de estado y el job está cerca de su límite de memoria.
- El producto exige resultados operativos en menos de 5 minutos.

¿Cuál política equilibra mejor el SLA, la memoria y la completitud?

A. Usar un watermark aproximado de 3–4 minutos y enviar los eventos que lleguen después del cierre a una ruta de late data para corrección o backfill; así se limita estado y latencia a cambio de corregir por otra vía una fracción pequeña.  
B. Mantener 30 minutos porque maximizar la completitud siempre tiene prioridad, aunque el job exceda memoria y los resultados operativos tarden más de 5 minutos.  
C. Usar exactamente 5 minutos y descartar silenciosamente cualquier evento posterior; un watermark igual al SLA garantiza cero pérdida.  
D. Eliminar el watermark y usar processing time; esto conserva menos estado y mantiene la misma semántica de event time.

### 12. Spark o Flink según el SLA

Una prueba con el volumen pico esperado produjo:

| Motor | p50 | p99 | Throughput | CPU |
|---|---:|---:|---:|---:|
| Spark, trigger 1 s | 1.3 s | 3.6 s | 75,000/s | 55% |
| Flink | 0.12 s | 0.42 s | 52,000/s | 76% |

Ambos workloads alcanzan como máximo 40,000 eventos/s:

1. Dashboard operativo con SLA de 10 segundos.
2. Detección de fraude con SLA p99 de 500 ms.

¿Qué recomendación está mejor respaldada por la prueba?

A. Flink para ambos, porque una p50 menor demuestra que siempre cuesta menos y escala mejor.  
B. Spark para ambos, porque su throughput máximo es mayor aunque no cumpla el p99 de fraude.  
C. Spark para el dashboard, pues cumple p99 < 10 s con menor CPU en esta prueba; Flink para fraude, pues cumple p99 < 500 ms y sostiene 40,000/s. La conclusión se limita al workload, hardware y configuración probados.  
D. Spark para fraude y Flink para el dashboard, porque el motor con mayor throughput siempre debe atender el SLA más estricto.

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

¿Cuál diagnóstico y cambio son más adecuados?

A. La frescura de 0.6 s prueba que ClickHouse está sano; se deben reducir los inserts a una fila para que cada merge termine antes.  
B. Los micro-inserts crean miles de partes y merges que compiten por CPU e I/O con las consultas. Conviene agrupar por tamaño o hacer flush cada 1–2 s, manteniendo margen frente al SLA de 5 s y monitoreando frescura, partes, merges y p95.  
C. El problema es exclusivamente la API; agregar una materialized view por cada insert reducirá las partes activas.  
D. Se debe esperar 30 s entre inserts: es la única forma de reducir merges, aunque viole el SLA de frescura.

### 14. Capacidad de Kafka

Un clúster recibe **12 MB/s** de datos, requiere **72 horas** de retención y usa factor de replicación **3**. Se desea además **25% de espacio libre** como margen operativo. Usa unidades decimales: 1 TB = 1,000,000 MB.

¿Qué capacidad y alerta son correctas?

A. 3.1104 TB; alertar sólo cuando el disco llegue a 100%, porque el factor de replicación no consume espacio adicional.  
B. 11.664 TB; multiplicar el almacenamiento replicado por 1.25 deja exactamente 25% de la capacidad libre.  
C. 9.3312 TB; alertar a 95%, porque el margen ya está incluido por el factor de replicación.  
D. Aproximadamente 12.44 TB: `12 × 259,200 × 3 / 0.75` MB; monitorear uso por broker o log directory, con alerta anticipada, por ejemplo warning a 70% y crítica a 85%.

---

## Sección C: fallas y semántica de ejecución — 24 puntos

Cada reactivo vale 8 puntos.

### 15. Falla parcial en un ETL incremental

El pipeline procesa intervalos horarios con estos pasos:

1. Lee `last_success = 10:00`.
2. Extrae 1,000 filas del intervalo `[10:00, 11:00)`.
3. Actualiza `last_success = 11:00`.
4. Inserta las filas en el destino en batches con autocommit y sin llave única.

El proceso falla después de insertar 600 filas. Al reiniciar, vuelve a leer `last_success`.

¿Qué ocurre y cuál rediseño resuelve el problema de forma completa?

A. Quedan 600 filas y las otras 400 se omiten porque el reinicio comienza en 11:00. Se debe conservar el intervalo pendiente, cargar a staging, publicar mediante upsert/reemplazo atómico y avanzar `last_success` sólo con o después del commit durable.  
B. Se releen las 1,000 filas automáticamente; basta mover la actualización de `last_success` al final aunque el destino siga siendo append-only con autocommit.  
C. Las 600 filas insertadas se revierten por el checkpoint; se debe aumentar el tamaño del batch para impedir futuros crashes.  
D. Quedan las 1,000 filas completas porque `last_success` confirma el intervalo; sólo hace falta agregar un índice al destino.

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

¿Cuál análisis y estrategia son correctos?

A. P0 relee 100–109 y P1 continúa en 210; aparecen diez duplicados de P0. Se evitan confirmando offsets antes de escribir.  
B. Ambas particiones continúan en 210 y no hay duplicados, porque los commits del consumer group son atómicos entre particiones.  
C. P0 continúa en 110 y P1 relee 200–209; aparecen diez duplicados de P1 y no hay pérdida. Un sink con llave determinista —por ejemplo `(topic, partition, offset)`— y upsert/dedupe hace inocuo el replay.  
D. P0 continúa en 110 y P1 en 200, pero los diez registros de P1 se pierden; un sink append-only garantiza exactly-once si el commit ocurre después de la escritura.

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

¿Cuál traza es correcta?

A. Después de C el watermark es 12:08 y la primera suma es 37; D se acepta porque llegó antes de E. El trigger de 10 s mueve los eventos a ventanas distintas.  
B. Después de C el watermark es 12:06 y se finaliza `[12:00, 12:05)` con 30; D se descarta. Después de E el watermark es 12:09 y, después de F, 12:10:30, cuando se finaliza `[12:05, 12:10)` con 5. El trigger cambia frecuencia/latencia, no pertenencia por event time.  
C. Después de C el watermark es 12:06, pero ninguna ventana puede cerrarse hasta que llegue un evento exactamente a las 12:05; D eleva la primera suma a 37.  
D. El watermark retrocede a 12:01 cuando llega D, por lo que ambas ventanas terminan con todos los eventos; cambiar el trigger cambia también el watermark a 10 minutos.

---

## Sección D: casos integradores — 24 puntos

Cada reactivo vale 8 puntos.

### 18. Quorum, fallas y latencia

Una réplica Raft de tres nodos tiene líder A. Para simplificar, asume que una escritura se confirma cuando A y al menos un follower persisten la entrada.

```text
Latencia A ↔ B: 20 ms
Latencia A ↔ C: 120 ms
```

¿Cuál afirmación describe correctamente los tres estados y el costo de replicación?

A. Con todos sanos A debe esperar siempre a B y C; si B falla no puede escribir, y más réplicas siempre multiplican el throughput.  
B. Con todos sanos A confirma localmente; con B fuera espera sólo su propio disco, y con B y C fuera continúa porque el líder cuenta como quorum.  
C. Con todos sanos el quorum requiere los tres nodos; con B fuera A+C ya no forman mayoría, aunque agregar réplicas elimina los round trips de escritura.  
D. Con todos sanos A puede confirmar con B, el follower más rápido; con B fuera aún confirma con A+C pero con mayor latencia; con B y C fuera no hay mayoría. Replicar el log y esperar quorum agrega coordinación, por lo que no garantiza más throughput.

### 19. Exactly-once fuera del procesador

Un job lee 500 eventos de Kafka por micro-batch y llama una API de cobro una vez por evento. La API acepta opcionalmente un encabezado `Idempotency-Key`, pero el job no lo utiliza. Después de 400 respuestas exitosas, el driver muere antes de confirmar el checkpoint del batch.

¿Qué comportamiento y diseño proporcionan la mejor seguridad de entrega?

A. Spark puede reproducir los 500 eventos y repetir hasta 400 cobros ya aceptados. Debe reutilizar una `Idempotency-Key` determinista por evento, confirmar progreso después del efecto durable y enviar errores permanentes identificados a una DLQ monitoreada, con retries para errores transitorios.  
B. Spark reanuda necesariamente en el evento 401; el checkpoint revierte automáticamente las 400 llamadas externas, así que no hace falta idempotencia.  
C. Se deben confirmar los 500 offsets antes de llamar a la API y descartar cualquier error; así no hay duplicados ni pérdida.  
D. Una `Idempotency-Key` aleatoria en cada retry evita cobros duplicados, y un registro inválido debe bloquear indefinidamente todo el stream.

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

¿Cuál diagnóstico y corrección son más completos?

A. ClickHouse está atrasado por merges; reiniciarlo eliminará las 2,000 órdenes extra, y la frescura es suficiente para detectar el problema.  
B. Debezium no emitió deletes; se debe aumentar la retención de Kafka y alertar únicamente por consumer lag.  
C. El filtro descarta los deletes porque tienen `after=null`, aunque todas las etapas sigan rápidas y sin errores. Se debe procesar `op=d` como retractación/tombstone o versión `is_deleted`, reconciliar las filas ya obsoletas y alertar si los deletes de origen no se reflejan downstream.  
D. Las 2,000 órdenes extra provienen de los updates; se corrige ignorando también `op=u` y comparando sólo la latencia de la API.

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
