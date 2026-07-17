# Operación de Linker

Este documento explica cómo un nuevo integrante del equipo puede contribuir, probar, desplegar, monitorear y operar Linker sin realizar operaciones manuales en la consola de OCI.

## 1. Propósito

Linker es una aplicación para acortar URLs. Permite crear enlaces cortos, redireccionar hacia la URL original, validar la salud de la aplicación, ejecutar pruebas funcionales, desplegar usando Blue/Green y monitorear la aplicación con Grafana.

## 2. Reglas de trabajo del equipo

- Todo cambio debe hacerse en una rama diferente a `main`.
- Todo cambio debe pasar por Pull Request.
- Otro integrante del equipo debe revisar y aprobar el Pull Request.
- No se deben subir secretos al repositorio.
- No se debe subir el archivo `.env`.
- No se deben hacer operaciones manuales en la consola de OCI.
- Los despliegues se ejecutan desde GitHub Actions.
- Las funcionalidades nuevas deben lanzarse mediante feature flags.
- Los enlaces externos usados en documentación deben estar acortados con Linker.

## 3. Flujo para contribuir

El flujo de trabajo recomendado es:

```bash
git checkout main
git pull origin main
git checkout -b tipo/descripcion-corta
```

Ejemplos de ramas:

```bash
git checkout -b ops/grafana-post-deploy
git checkout -b docs/operaciones
git checkout -b feat/head-delete
git checkout -b feat/serverless-lambda
```

Después de realizar cambios:

```bash
git status
git add .
git commit -m "tipo(scope): descripcion corta del cambio"
git push origin nombre-de-la-rama
```

Luego se crea un Pull Request hacia `main` y se solicita revisión a otro integrante del equipo.

## 4. Convención de commits

Se recomienda usar commits claros y pequeños.

Ejemplos:

```txt
ops(grafana): add post-deploy monitoring validation
docs(ops): add Linker operations runbook
ops(release): separate feature launch from deployment
feat(links): add HEAD and DELETE operations behind feature flag
feat(serverless): add AWS Lambda adapter and artifact workflow
fix(deploy): validate healthz after switchover
```

## 5. Ejecución local

Para ejecutar Linker localmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

En otra terminal, definir la URL base:

```bash
export BASE_URL="localhost:8080"
```

Validar la aplicación:

```bash
curl -i "$BASE_URL/health"
curl -i "$BASE_URL/healthz"
```

## 6. Pruebas locales

Antes de crear un Pull Request, se deben ejecutar estas validaciones:

```bash
python -m compileall .
python -m unittest discover -s tests -p "test_*.py" -v
```

También se pueden ejecutar pruebas funcionales:

```bash
export BASE_URL="localhost:8080"
bash scripts/integration_tests.sh "$BASE_URL"
```

## 7. Scripts principales

| Script | Uso |
|---|---|
| `scripts/integration_tests.sh` | Ejecuta pruebas funcionales contra una URL base de Linker. |
| `scripts/remote_install.sh` | Instala Linker en una VM desde el artefacto del pipeline. |
| `scripts/grafana_check.sh` | Valida Grafana después del despliegue y crea una anotación. |
| `scripts/oci/load_infra_env.sh` | Carga variables de infraestructura desde `infra/linker.env`. |
| `scripts/oci/launch_instance.sh` | Crea una nueva instancia en OCI desde el pipeline. |
| `scripts/oci/find_active_instance.sh` | Identifica cuál ambiente está activo en Blue/Green. |
| `scripts/oci/switch_traffic.sh` | Cambia el tráfico hacia la nueva instancia. |
| `scripts/oci/terminate_instance.sh` | Elimina una instancia cuando ya no se necesita. |

## 8. Pipeline principal

El workflow principal es:

```txt
.github/workflows/linker-python-pipeline.yml
```

Este pipeline ejecuta:

1. Validación de estructura del proyecto.
2. Instalación de dependencias.
3. Compilación del código Python.
4. Pruebas unitarias.
5. Construcción y publicación de imagen Docker.
6. Construcción del artefacto de despliegue.
7. Despliegue de un entorno efímero.
8. Pruebas de integración y funcionalidad.
9. Despliegue Blue/Green.
10. Switchover hacia la nueva versión.
11. Eliminación de la VM anterior si el despliegue fue exitoso.
12. Eliminación de la VM nueva si el despliegue falla.
13. Validación post-despliegue en Grafana.

## 9. Entorno efímero

Antes de desplegar a producción, el pipeline crea una instancia efímera.

Ese entorno se usa para:

- instalar el artefacto generado;
- ejecutar healthchecks;
- ejecutar pruebas funcionales;
- validar que la nueva versión puede correr correctamente.

Después de las pruebas, la instancia efímera se elimina automáticamente.

## 10. Despliegue Blue/Green

Linker usa una estrategia Blue/Green.

- El ambiente activo atiende el tráfico de producción.
- El ambiente inactivo recibe la nueva versión.
- La nueva versión se valida antes de recibir tráfico.
- Si las pruebas pasan, el pipeline realiza el switchover.
- Si la nueva versión falla, el pipeline elimina la nueva VM.
- Si el switchover es exitoso, el pipeline retira la VM anterior.

Todo este proceso se realiza desde GitHub Actions. No se debe entrar manualmente a la consola de OCI para crear, modificar o eliminar máquinas.

## 11. Healthchecks

Linker expone dos healthchecks:

| Endpoint | Uso |
|---|---|
| `/health` | Valida que la aplicación está viva. |
| `/healthz` | Valida aplicación y base de datos usando `SELECT 1`. |

Validación:

```bash
export BASE_URL="localhost:8080"
curl -i "$BASE_URL/health"
curl -i "$BASE_URL/healthz"
```

## 12. Monitoreo con Grafana

Después de cada despliegue exitoso, el pipeline ejecuta:

```bash
scripts/grafana_check.sh
```

Este script realiza tres acciones:

1. Valida que Grafana esté disponible.
2. Verifica que existan dashboards de Linker.
3. Crea una anotación del despliegue.

En Grafana se deben revisar:

- disponibilidad de la aplicación;
- errores 4xx y 5xx;
- latencia;
- trazas del healthcheck;
- trazas de creación de enlaces;
- trazas de redirección;
- anotaciones de despliegue.

## 13. Spans importantes

En las trazas se deben buscar spans como:

```txt
linker.healthcheck
linker.healthcheck.db.select_1
linker.http.create_link
linker.usecase.create_short_link
linker.http.redirect
linker.usecase.resolve_short_link
```

## 14. Variables y secretos

Las variables no sensibles se configuran en GitHub Actions Variables.

Los secretos se configuran en GitHub Actions Secrets.

Nunca se debe subir un archivo `.env` al repositorio.

### Variables principales

| Variable | Uso |
|---|---|
| `MYSQL_HOST` | Host de MySQL. |
| `MYSQL_PORT` | Puerto de MySQL. |
| `MYSQL_DATABASE` | Base de datos. |
| `MYSQL_USER` | Usuario de MySQL. |
| `OTEL_SERVICE_NAME` | Nombre del servicio observado en Grafana. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint OTLP de Grafana. |
| `GRAFANA_URL` | URL base de Grafana. |
| `PROD_BASE_URL` | URL productiva de Linker. |
| `OCI_CLI_REGION` | Región de OCI. |
| `OCI_BASTION_OCID` | OCID del Bastion. |
| `OCI_COMPARTMENT_OCID` | OCID del compartimiento. |
| `OCI_IMAGE_OCID` | OCID de la imagen usada para crear VMs. |
| `OCI_AVAILABILITY_DOMAIN` | Availability domain usado por OCI. |
| `OCI_INSTANCE_SHAPE` | Shape de las instancias. |
| `OCI_SHAPE_OCPUS` | OCPUs asignadas. |
| `OCI_SHAPE_MEMORY_GB` | Memoria asignada. |

### Secrets principales

| Secret | Uso |
|---|---|
| `MYSQL_PWD` | Contraseña de MySQL. |
| `OTEL_EXPORTER_OTLP_HEADERS` | Header de autenticación OTLP. |
| `GRAFANA_API_TOKEN` | Token para consultar Grafana y crear anotaciones. |
| `LAUNCHDARKLY_SDK_KEY` | SDK key usado por la aplicación para evaluar flags. |
| `LAUNCHDARKLY_API_TOKEN` | Token usado por el pipeline para modificar flags. |
| `DEPLOYMENT_PRIVATE_KEY` | Llave privada para conexión de despliegue. |
| `DEPLOYMENT_PUBLIC_KEY` | Llave pública para sesiones Bastion. |
| `OCI_CLI_USER` | Usuario de OCI CLI. |
| `OCI_CLI_TENANCY` | Tenancy de OCI. |
| `OCI_CLI_FINGERPRINT` | Fingerprint de la llave OCI. |
| `OCI_CLI_KEY_CONTENT` | Contenido de la llave privada OCI. |

## 15. Lanzamiento de funcionalidades

El despliegue y el lanzamiento son procesos diferentes.

- Despliegue: instala una nueva versión del código.
- Lanzamiento: activa o desactiva una funcionalidad ya desplegada.

El workflow de lanzamiento es:

```txt
.github/workflows/release_feature.yml
```

Ejemplo de funcionalidad:

```txt
advanced-operations
```

Esta funcionalidad permite:

```txt
HEAD /r/<id>
DELETE /r/<id>
```

La funcionalidad debe poder activarse o desactivarse sin redesplegar la aplicación.

## 16. Rollback

Si una funcionalidad falla, se debe apagar la feature flag desde el pipeline de lanzamiento.

Si un despliegue falla, el pipeline Blue/Green elimina la nueva VM y conserva la versión anterior.

No se debe corregir manualmente la VM desde la consola de OCI.

## 17. Operación ante incidentes

Si producción falla después de un despliegue:

1. Revisar el job `deploy-blue-green`.
2. Revisar las pruebas de integración.
3. Revisar los healthchecks.
4. Revisar Grafana.
5. Confirmar si el rollback automático eliminó la nueva VM.
6. Crear un Pull Request de corrección.
7. Ejecutar nuevamente el pipeline de despliegue.

## 18. Pull Request

Todo cambio debe llegar a `main` mediante Pull Request.

El Pull Request debe incluir:

- objetivo del cambio;
- archivos modificados;
- pruebas ejecutadas;
- evidencia del pipeline;
- riesgos;
- plan de rollback;
- compañero responsable de la aprobación.

## 19. Checklist antes de aprobar

Antes de aprobar un Pull Request, el revisor debe validar:

- Las pruebas pasan.
- El pipeline está verde.
- No se sube `.env`.
- No se suben secretos.
- La documentación está actualizada.
- El cambio tiene rollback claro.
- No hay enlaces externos sin acortar.
- El cambio no rompe `/health` ni `/healthz`.

## 20. Buscar enlaces externos

Para buscar enlaces externos pendientes:

```bash
grep -RInE 'https?://' . \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=__pycache__ \
  --exclude='*.pyc'
```

Los enlaces externos de documentación deben reemplazarse por enlaces acortados con Linker.

Los endpoints locales usados en comandos operativos deben escribirse usando variables como `BASE_URL`.