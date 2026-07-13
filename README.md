# Linker Python

![CI](https://github.com/co-eiv-devsecops/linker2/actions/workflows/linker-python-pipeline.yml/badge.svg)

Implementación en Python del ejercicio **Linker**, una aplicación web sencilla para acortar URL, ahora refactorizada sobre **Flask** con inyección de dependencias en la capa de aplicación y persistencia.


La aplicación está construida con Flask y componentes desacoplados de Python:

- `Flask` para la capa web.
- `sqlite3` para la persistencia.
- `urllib.parse` para procesar rutas, formularios y URL.
- `secrets` para generar identificadores cortos.


## Tecnologías

- Python 3
- SQLite
- Nginx
- systemd
- JavaScript
- HTML y CSS

## Estructura

```txt
linker-python/
├── app.py              # Punto de entrada de la aplicacion
├── config.py           # Variables de configuracion
├── database.py         # Repositorio SQLite e inicializacion
├── link_service.py     # Logica de aplicacion para validar, crear y buscar enlaces
├── web.py              # Factory de Flask y rutas HTTP
├── views.py            # Carga de vistas HTML
├── views/
│   └── index.html      # Frontend sencillo
├── tests/
│   └── test_link_service.py
├── linker.db
├── requirements.txt
├── README.md
├── DEVSECOPS.md
├── DOCUMENTO.md
└── scripts/
    ├── run_local.sh
    ├── install_vm.sh
    └── deploy.sh
```

## Flujo DevSecOps

La organización del trabajo, el tablero Kanban, la Definition of Ready y la Definition of Done están documentadas en:

[DEVSECOPS.md](./DEVSECOPS.md)

## Guia de trabajo del equipo

Para trabajar de forma fluida en este proyecto, revise primero estas guias:

- [CONTRIBUTING.md](./CONTRIBUTING.md): flujo de contribucion, validaciones y checklist de PR.
- [SUPPORT.md](./SUPPORT.md): como pedir ayuda y que informacion incluir.
- [SECURITY.md](./SECURITY.md): como reportar problemas de seguridad.
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md): reglas de convivencia del equipo.

Al abrir issues o pull requests, use las plantillas que estan en [.github/ISSUE_TEMPLATE](./.github/ISSUE_TEMPLATE) y el template de PR que se aplica automaticamente.

## Lanzamientos progresivos

La estrategia de releases con feature flags, rollback y small batch development esta documentada en:

[docs/releases.md](./docs/releases.md)

## Componentes

El proyecto separa responsabilidades de esta forma:

- `web.py`: crea la app de Flask y define las rutas.
- `link_service.py`: contiene la logica de negocio y recibe el repositorio por inyeccion.
- `database.py`: encapsula el acceso a SQLite.
- `feature_flags.py`: resuelve flags locales y, opcionalmente, LaunchDarkly.
- `views/index.html`: plantilla HTML de la interfaz.

## Ejecutar localmente

```bash
python3 app.py
```

Luego abrir:

```txt
http://localhost:8080
```

También puede usarse el script:

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

## Cambiar el puerto

```bash
PORT=9090 python3 app.py
```

## Ejecutar pruebas

```bash
python3 -m unittest discover tests
```

## Cobertura

El objetivo de cobertura del proyecto es mayor a 90%. Para medirla localmente:

```bash
python3 -m coverage run -m unittest discover tests
python3 -m coverage report -m
```

## DevContainer

El proyecto incluye un DevContainer para ejecutar Linker en un entorno de desarrollo consistente, sin depender de la configuracion local del computador.

Para usarlo:

1. Abrir el repositorio en VS Code.
2. Seleccionar **Reopen in Container**.
3. Ejecutar la aplicacion:

```bash
cd linker-python
python3 app.py
```

La aplicacion queda disponible en:

```txt
http://localhost:8080
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Cliente web |
| POST | `/link` | Crea una URL corta |
| GET | `/<id>` | Redirecciona a la URL original |
| GET | `/health` | Verifica el estado de la aplicación |

## Ejemplo con curl

```bash
curl -i -X POST http://localhost:8080/link \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://www.python.org"
```

La respuesta incluye el encabezado `Location` con la URL corta generada.

## Integración continua (CI)

El workflow [`linker-python-pipeline.yml`](./.github/workflows/linker-python-pipeline.yml) se ejecuta en cada `push` y `pull_request` hacia `main`/`master`, y valida:

1. Estructura del proyecto (`app.py`, `requirements.txt`, `tests/`).
2. Sintaxis de todo el código Python (`compileall`).
3. Pruebas unitarias (`unittest discover`).
4. Arranque real de la aplicación y verificación de `/health` y `/link`.

Cuando ese `push` cae directamente sobre `main`/`master` y las pruebas pasan, un segundo job (`publish-image`) construye la imagen Docker de la aplicación y la publica en **GitHub Packages** (GitHub Container Registry).

## Distribución de artefactos con GitHub Packages

El artefacto que se distribuye es una **imagen Docker**, publicada en el GitHub Container Registry (`ghcr.io`) del repositorio. Se generan dos tags en cada publicación:

- `ghcr.io/co-eiv-devsecops/linker2:latest`
- `ghcr.io/co-eiv-devsecops/linker2:<sha-del-commit>`

Para descargar y ejecutar la imagen (el paquete debe estar público, o hay que autenticarse con `docker login ghcr.io` usando un Personal Access Token con permiso `read:packages`):

```bash
docker pull ghcr.io/co-eiv-devsecops/linker2:latest
docker run -p 8080:8080 ghcr.io/co-eiv-devsecops/linker2:latest
```

La aplicación queda disponible en `http://localhost:8080`.

## Despliegue continuo (CD)

Cuando un `push` llega a `main`/`master` y pasa el job `build-and-test`, el workflow ejecuta automáticamente:

1. **`Build`**: empaqueta los archivos necesarios para producción junto con los scripts de instalación remota y pruebas de integración, y los sube como artefacto de GitHub Actions (`linker-app`).
2. **`ephemeral-test`**: crea una **VM efímera** en OCI, instala el mismo artefacto que irá a producción, ejecuta healthchecks y pruebas de integración/funcionalidad, y destruye la VM al terminar (pase o falle).
3. **`deploy-blue-green`**: despliegue **Blue/Green** 🔵🟢 a producción: crea una instancia nueva con el color inactivo, hace QA sobre ella sin tráfico, ejecuta el switchover, valida producción y retira la VM de la versión anterior. Si algo falla, hace rollback automático y elimina la VM nueva.
4. **`grafana-post-deploy`**: verifica Grafana y registra una anotación del despliegue en los dashboards.

El flujo completo, los mecanismos de switchover y las variables/secretos requeridos están documentados en [docs/despliegue.md](./docs/despliegue.md). El monitoreo posterior al despliegue está en [docs/monitoreo.md](./docs/monitoreo.md).

Además se requiere un **Environment** de GitHub llamado `production` (Settings → Environments), restringido a la rama `main`.

El script de despliegue es idempotente: escribe la unidad de `systemd` en cada corrida, así que no depende de que `scripts/install_vm.sh` se haya ejecutado antes manualmente contra la VM.

## Despliegue en máquina virtual (manual)

Editar los valores del script `scripts/deploy.sh` o enviarlos como variables de entorno:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

El despliegue copia el proyecto completo a la VM, instala Git, Python 3 y Nginx, configura systemd y deja la aplicación ejecutándose como servicio. Esta ruta manual sigue sirviendo para el setup inicial de una VM nueva; una vez configurada, las actualizaciones subsecuentes las hace el pipeline de CD descrito arriba.

La aplicación debe quedar disponible en:

```txt
http://2.n-la-c.app
```

> Nota: si la plataforma no configura HTTPS automáticamente, se debe habilitar TLS según las instrucciones del curso o del administrador de la VM.

## Paridad de entornos

El proyecto implementa paridad de entornos mediante scripts Bash que automatizan completamente la preparación de una VM Ubuntu. Los scripts instalan los paquetes requeridos (`git`, `python3` y `nginx`), copian el contenido necesario del proyecto, configuran el servicio `systemd` `linker-python.service` en `/opt/linker-python`, configuran Nginx y verifican el endpoint `/health`.

Para preparar una VM Ubuntu desde una copia del proyecto:

```bash
./scripts/install_vm.sh
```

Para desplegar desde la máquina local hacia la VM del equipo:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

Con estos scripts, cualquier desarrollador puede recrear el mismo entorno de producción de forma repetible, usando las mismas rutas, el mismo servicio y los mismos comandos de arranque.

## Configuración de verbosidad de logs

El proyecto cuenta con un sistema de registro de eventos estructurado en 5 niveles de verbosidad (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### Selección de nivel mediante variables de entorno

Para configurar la verbosidad, defina la variable de entorno `LOG_LEVEL` antes de ejecutar la aplicación. Los valores válidos son:

*   **`DEBUG`**: Imprime flujos de ejecución detallados internos de la lógica del negocio (ej. validaciones de URL).
*   **`INFO`**: Nivel operativo estándar de producción. Muestra confirmaciones de creación de enlaces y redirecciones exitosas.
*   **`WARNING`**: Registra solicitudes incorrectas del cliente (URLs mal formadas o enlaces que no existen).
*   **`ERROR`**: Reporta excepciones internas que impiden procesar solicitudes (como fallas del servidor HTTP).
*   **`CRITICAL`**: Registra fallos graves que comprometen la base de datos o el estado general de la aplicación.

### Ejemplos de uso

Para modificar la verbosidad usando el mismo artefacto, configure la variable en su terminal o entorno de ejecución:

```bash
# Cambiar verbosidad a modo Diagnóstico (Muestra DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=DEBUG
python3 app.py

# Cambiar verbosidad a modo Producción estricto (Muestra solo WARNING, ERROR, CRITICAL)
export LOG_LEVEL=WARNING
python3 app.py
```
