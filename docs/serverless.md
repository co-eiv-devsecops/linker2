# Serverless Linker

Este documento describe el bono de reimplementación serverless de Linker usando AWS Lambda.

## 1. Objetivo

El objetivo es demostrar que Linker fue abstraído para poder ejecutarse en más de una plataforma usando el mismo núcleo de negocio.

## 2. Arquitectura

| Plataforma | Adaptador | Núcleo común |
|---|---|---|
| VM con Flask | `web.py` | `linker_app.py` |
| OCI Functions | `serverless.py` | `linker_app.py` |
| AWS Lambda | `aws_lambda.py` | `linker_app.py` |

El archivo `linker_app.py` contiene la lógica principal de la aplicación.

Los adaptadores solamente traducen la entrada de cada plataforma al modelo común `LinkerRequest`.

## 3. Artefacto común

Los archivos principales reutilizados por todas las plataformas son:

```txt
linker_app.py
link_service.py
database.py
feature_flags.py
telemetry.py
```

## 4. Rutas soportadas

La versión serverless soporta:

```txt
GET /health
GET /healthz
POST /link
GET /r/<id>
HEAD /r/<id>
DELETE /r/<id>
```

## 5. Variables requeridas

| Variable | Uso |
|---|---|
| `DB_ENGINE` | Motor de base de datos. |
| `MYSQL_HOST` | Host de MySQL. |
| `MYSQL_PORT` | Puerto de MySQL. |
| `MYSQL_DATABASE` | Base de datos. |
| `MYSQL_USER` | Usuario. |
| `MYSQL_PWD` | Contraseña. |
| `OTEL_SERVICE_NAME` | Nombre del servicio. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint OTLP. |
| `OTEL_EXPORTER_OTLP_HEADERS` | Autenticación OTLP. |
| `LAUNCHDARKLY_SDK_KEY` | SDK key para evaluar feature flags. |

## 6. Workflow serverless

El workflow es:

```txt
.github/workflows/serverless-aws-lambda.yml
```

Este workflow:

1. Ejecuta pruebas.
2. Empaqueta el artefacto Lambda.
3. Publica el artefacto como evidencia.
4. Despliega en AWS Lambda cuando se configura la variable `AWS_LAMBDA_FUNCTION_NAME`.

## 7. Separación frente al despliegue en VM

El despliegue en VM sigue usando:

```txt
.github/workflows/linker-python-pipeline.yml
```

El despliegue serverless usa:

```txt
.github/workflows/serverless-aws-lambda.yml
```

Esto permite tener dos objetivos de producción independientes:

- producción en VM;
- producción serverless.

## 8. Validación

Después del despliegue serverless se deben validar:

```txt
/health
/healthz
/link
/r/<id>
```

## 9. Rollback

Si la versión serverless falla, se debe publicar nuevamente el artefacto anterior o deshabilitar el tráfico hacia la función Lambda.

El despliegue serverless no afecta el despliegue Blue/Green actual en VM.