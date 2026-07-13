# Redespliegue de Linker: entorno efímero + Blue/Green

Este documento describe cómo funciona el pipeline de **despliegue** de Linker
([`linker-python-pipeline.yml`](../.github/workflows/linker-python-pipeline.yml)).
El pipeline antepone **estabilidad** a nueva funcionalidad: ningún cambio llega a
producción sin pasar antes por un entorno efímero de pruebas, y el switchover
Blue/Green tiene rollback automático.

Todo el ciclo se ejecuta desde GitHub Actions con el OCI CLI:
**0 operaciones manuales en la consola de OCI**.

## Flujo completo

```txt
push a main
   │
   ├─ build-and-test        Pruebas unitarias + validación de rutas
   ├─ publish-image         Imagen Docker a GitHub Packages
   ├─ Build                 Artefacto de despliegue (linker-app)
   │
   ├─ ephemeral-test        ① Crea VM efímera  ② Despliega  ③ Prueba  ④ Destruye
   │
   ├─ deploy-blue-green     Despliegue Blue/Green a producción 🔵🟢
   │
   └─ grafana-post-deploy   Chequeo de Grafana + anotación del despliegue (bono)
```

## 1. Entorno efímero de pruebas (`ephemeral-test`)

El entorno efímero **se crea, se prueba y se destruye** en la misma corrida:

1. **Crear**: `scripts/oci/launch_instance.sh` lanza una VM
   `linker-ephemeral-<run_id>` con cloud-init
   ([`scripts/oci/cloud-init-linker.yaml`](../scripts/oci/cloud-init-linker.yaml))
   y el plugin Bastion habilitado.
2. **Desplegar**: el **mismo artefacto** que irá a producción (`linker-app`) se
   instala con [`scripts/remote_install.sh`](../scripts/remote_install.sh)
   (venv + systemd + healthchecks), a través de una sesión Bastion.
3. **Probar**: [`scripts/integration_tests.sh`](../scripts/integration_tests.sh)
   ejecuta las pruebas de integración y funcionalidad:
   `GET /`, `GET /health`, `GET /healthz`, `POST /link` (201 + `Location`),
   redirección `301` a la URL original, `404` para IDs inexistentes y `400`
   para URLs inválidas.
4. **Destruir**: `scripts/oci/terminate_instance.sh` elimina la VM **siempre**
   (`if: always()`), incluso si las pruebas fallaron.

El entorno es autocontenido: usa SQLite local y telemetría apagada, para no
contaminar la base de datos ni las métricas de producción.

## 2. Despliegue Blue/Green (`deploy-blue-green`)

Solo un ambiente (🔵 o 🟢) recibe tráfico en cada momento. El pipeline:

1. **Identifica el ambiente activo** (`scripts/oci/find_active_instance.sh`):
   busca la instancia RUNNING con tag `linker-role=active` y lee su color.
   El nuevo despliegue usa el color contrario.
2. **Crea una instancia** nueva (`linker-<color>-<run_number>`) con tag
   `linker-role=candidate`.
3. **Despliega y hace QA en el ambiente inactivo**: instala el artefacto y
   corre healthchecks (`/health`, `/healthz`) y las pruebas de funcionalidad
   contra la instancia nueva, **mientras el tráfico sigue en el ambiente
   anterior**.
4. **Switchover** (`scripts/oci/switch_traffic.sh`): mueve el tráfico al
   ambiente nuevo (ver mecanismos abajo). *Este es el lanzamiento.*
5. **Valida producción**: reintenta `/health` y `/healthz` a través de la URL
   pública (`PROD_BASE_URL`) y vuelve a correr las pruebas de funcionalidad.
6. **Si todo fue exitoso**: la instancia nueva se marca `linker-role=active` y
   la **VM de la versión anterior se elimina**.
7. **Si algo falla**: el rollback automático regresa el tráfico al ambiente
   anterior (si el switch ya había ocurrido) y **elimina la VM con la nueva
   versión**. Producción queda como estaba.

La persistencia vive **fuera** de las VMs (MySQL externo, `DB_ENGINE=mysql`),
por eso se pueden retirar instancias sin perder los enlaces acortados.

### Mecanismos de switchover

`switch_traffic.sh` soporta dos modos, según las variables configuradas:

| Modo | Variables | Cómo funciona |
|---|---|---|
| **IP privada flotante** (recomendado) | `OCI_FLOATING_IP_ADDRESS` | El dominio del equipo apunta a una IP privada fija. Esa IP se mantiene como IP secundaria y se mueve entre la VNIC del ambiente azul y verde (`oci network vnic assign-private-ip --unassign-if-already-assigned`). |
| **Load Balancer OCI** | `OCI_LB_OCID`, `OCI_LB_BACKEND_SET` | Se registra la IP de la instancia nueva como backend y se retiran los backends anteriores del backend set. |

> **Primera ejecución**: si ninguna instancia tiene el tag `linker-role=active`
> (por ejemplo, cuando aún existe la VM fija original), el pipeline despliega
> `blue`, mueve el tráfico y no elimina nada. La VM antigua debe retirarse una
> única vez con el propio pipeline o etiquetarse `linker-role=active` para que
> el siguiente ciclo la retire automáticamente.

## Variables y secretos requeridos

Configurar en *Settings → Secrets and variables → Actions*:

**Secrets** (ya existentes): `DEPLOYMENT_PRIVATE_KEY`, `DEPLOYMENT_PUBLIC_KEY`,
`OCI_CLI_USER`, `OCI_CLI_TENANCY`, `OCI_CLI_FINGERPRINT`, `OCI_CLI_KEY_CONTENT`,
`MYSQL_PWD`, `OTEL_EXPORTER_OTLP_HEADERS`, `LAUNCHDARKLY_SDK_KEY`.
Nuevos: `GRAFANA_API_TOKEN` (bono de Grafana).

**Variables** (ya existentes): `OCI_CLI_REGION`, `OCI_BASTION_OCID`,
`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`,
`OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`.

**Variables nuevas** para crear instancias y hacer switchover:

| Variable | Descripción |
|---|---|
| `OCI_COMPARTMENT_OCID` | Compartment del equipo |
| `OCI_SUBNET_OCID` | Subred privada de las VMs |
| `OCI_IMAGE_OCID` | Imagen Ubuntu para las instancias |
| `OCI_AVAILABILITY_DOMAIN` | Availability domain |
| `OCI_INSTANCE_SHAPE` | Shape (default `VM.Standard.E2.1.Micro`) |
| `OCI_SHAPE_OCPUS`, `OCI_SHAPE_MEMORY_GB` | Solo para shapes `*.Flex` |
| `OCI_FLOATING_IP_ADDRESS` **o** `OCI_LB_OCID` + `OCI_LB_BACKEND_SET` | Mecanismo de switchover |
| `PROD_BASE_URL` | URL pública de producción (default `http://2.n-la-c.app`) |
| `GRAFANA_URL` | URL base de la instancia de Grafana |

## Después del despliegue

El job `grafana-post-deploy` verifica Grafana y anota el despliegue en los
dashboards. El monitoreo post-despliegue está documentado en
[monitoreo.md](./monitoreo.md).
