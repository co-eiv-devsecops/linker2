# Monitoreo post-despliegue con Grafana

Linker exporta trazas y metricas por OpenTelemetry (OTLP) hacia el backend de
observabilidad, y Grafana es el punto unico para verificar la salud de la
aplicacion despues de cada despliegue.

## Chequeo automatico en el pipeline (bono)

Despues de cada despliegue Blue/Green, el job **`grafana-post-deploy`** ejecuta
[`scripts/grafana_check.sh`](../scripts/grafana_check.sh):

1. Valida que produccion responda `/health` y `/healthz`.
2. Crea un enlace corto de prueba contra produccion.
3. Genera trafico para que aparezcan trazas en Grafana.
4. Emite el span `linker.deployment.post_deploy_check` por OpenTelemetry.

Este chequeo no usa la API HTTP de Grafana ni requiere `GRAFANA_API_TOKEN`.
Requiere `PROD_BASE_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT` y
`OTEL_EXPORTER_OTLP_HEADERS`.

## Checklist manual post-despliegue

Durante los siguientes minutos despues de un despliegue, revisar en el dashboard
de Linker:

| Senal | Que mirar | Alarma si... |
|---|---|---|
| Rate | Tasa de solicitudes a `/link` y `/r/<short_id>` | Cae a cero tras el switchover. |
| Errors | Respuestas 5xx y spans con status `ERROR` | Suben respecto a la ventana previa. |
| Duration | Latencia de `linker.http.create_link` y `linker.http.redirect` | La p95 se degrada. |
| Healthchecks | Spans `linker.healthcheck` | Aparecen eventos `healthcheck.failed`. |

Pasos:

1. Abrir el dashboard de Linker en Grafana y buscar el span
   `linker.deployment.post_deploy_check`.
2. Usar la hora de la corrida del pipeline para comparar Rate/Errors/Duration
   antes y despues del despliegue.
3. Verificar que el servicio reporta con el `OTEL_SERVICE_NAME` esperado.
4. Si los errores suben o la latencia se degrada de forma sostenida, ejecutar
   nuevamente el pipeline con una version estable o usar el rollback si la
   corrida sigue abierta.

## Fuentes de telemetria

- `web.py` instrumenta cada ruta con spans (`linker.http.*`,
  `linker.healthcheck`) y atributos de negocio.
- Los healthchecks (`/health`, `/healthz`) son consultados por el pipeline en
  el entorno efimero, QA del ambiente inactivo y validacion post-switchover.
- `scripts/grafana_check.sh` genera trafico real y emite el span
  `linker.deployment.post_deploy_check`, con atributos de commit, corrida,
  repositorio, URL base y estrategia `blue-green`.

## Validacion post-despliegue usando OpenTelemetry

El proyecto no depende de un token de API de Grafana para validar el monitoreo
post-despliegue.

Despues de un despliegue exitoso, el pipeline ejecuta:

```txt
scripts/grafana_check.sh
```
