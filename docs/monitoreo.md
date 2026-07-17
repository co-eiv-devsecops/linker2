# Monitoreo post-despliegue con Grafana

Linker exporta trazas y métricas por OpenTelemetry (OTLP) hacia el backend de
observabilidad, y Grafana es el punto único para verificar la salud de la
aplicación después de cada despliegue.

## Chequeo automático en el pipeline (bono)

Después de cada despliegue Blue/Green, el job **`grafana-post-deploy`** ejecuta
[`scripts/grafana_check.sh`](../scripts/grafana_check.sh):

1. **Salud de Grafana**: `GET /api/health` debe responder con `database: ok`.
2. **Dashboards de Linker**: debe existir al menos un dashboard cuyo nombre
   contenga `linker` (búsqueda vía `/api/search`).
3. **Anotación del despliegue**: crea una anotación con tags
   `deployment, linker, blue-green`, el commit desplegado y el link a la
   corrida del pipeline. La anotación aparece como una línea vertical en los
   dashboards, lo que permite correlacionar cualquier cambio de comportamiento
   con el despliegue exacto que lo causó.

Requiere la variable `GRAFANA_URL` y el secreto `GRAFANA_API_TOKEN`
(service account token con rol que permita leer dashboards y crear
anotaciones).

## Checklist manual post-despliegue

Durante los ~15 minutos siguientes a un despliegue, revisar en el dashboard de
Linker (método **RED**):

| Señal | Qué mirar | Alarma si... |
|---|---|---|
| **Rate** | Tasa de solicitudes a `/link` y `/r/<short_id>` | Cae a cero tras el switchover (el tráfico no llegó al ambiente nuevo) |
| **Errors** | Respuestas 5xx y spans con status `ERROR` | Suben respecto a la ventana previa al despliegue |
| **Duration** | Latencia de `linker.http.create_link` y `linker.http.redirect` | La p95 se degrada tras el despliegue |
| **Healthchecks** | Spans `linker.healthcheck` (incluye ping a la base de datos) | Aparecen eventos `healthcheck.failed` |

Pasos:

1. Abrir el dashboard de Linker en Grafana y ubicar la **anotación** del
   despliegue recién hecho.
2. Comparar Rate/Errors/Duration antes y después de la anotación.
3. Verificar que el servicio reporta con el `OTEL_SERVICE_NAME` esperado
   (la instancia nueva debe estar enviando telemetría).
4. Si los errores suben o la latencia se degrada de forma sostenida:
   ejecutar de nuevo el pipeline con la versión anterior (el despliegue
   Blue/Green retirará la versión problemática), o usar el rollback del
   workflow si la corrida sigue abierta.

## Fuentes de telemetría

- `web.py` instrumenta cada ruta con spans (`linker.http.*`,
  `linker.healthcheck`) y atributos de negocio (dominio destino, longitud de
  URL, feature flags).
- Los healthchecks (`/health`, `/healthz`) son consultados por el pipeline en
  cada fase (entorno efímero, QA del ambiente inactivo y validación
  post-switchover), de modo que un despliegue solo se promueve si la
  telemetría básica está sana.

## Validación post-despliegue usando OpenTelemetry

El proyecto no depende de un token de API de Grafana para validar el monitoreo post-despliegue.

Después de un despliegue exitoso, el pipeline ejecuta:

```txt
scripts/grafana_check.sh