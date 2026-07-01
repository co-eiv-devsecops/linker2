# Linker Python

Implementación en Python del ejercicio **Linker**, una aplicación web sencilla para acortar URL.


La aplicación está construida librerías estándar de Python:

- `http.server` para el servidor web.
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
├── app.py
├── requirements.txt
├── README.md
├── DOCUMENTO.md
└── scripts/
    ├── run_local.sh
    ├── install_vm.sh
    └── deploy.sh
```

## Flujo DevSecOps

La organización del trabajo, el tablero Kanban, la Definition of Ready y la Definition of Done están documentadas en:

[DEVSECOPS.md](./DEVSECOPS.md)

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

## Despliegue en máquina virtual

Editar los valores del script `scripts/deploy.sh` o enviarlos como variables de entorno:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

El despliegue copia la aplicación a la VM, instala Python 3 y Nginx, configura systemd y deja la aplicación ejecutándose como servicio.

La aplicación debe quedar disponible en:

```txt
https://2.n-la-c.app
```

> Nota: si la plataforma no configura HTTPS automáticamente, se debe habilitar TLS según las instrucciones del curso o del administrador de la VM.
