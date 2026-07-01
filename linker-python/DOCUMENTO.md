# Implementación de Linker en Python

## 1. Introducción

Este proyecto implementa una aplicación web llamada **Linker Python**, cuyo propósito es acortar URL. La aplicación toma como referencia el proyecto Linker original, pero se desarrolla en Python utilizando únicamente librerías estándar y un servidor web simple.

El sistema permite que un usuario ingrese una URL larga desde un cliente web. La aplicación genera un identificador corto, almacena la relación entre el identificador y la URL original en una base de datos SQLite y permite acceder posteriormente a la URL original mediante una ruta corta.

---

## 2. Objetivo

Construir una aplicación web ligera desarrollada en Python para demostrar conceptos básicos de desarrollo, persistencia de datos y despliegue de aplicaciones en una máquina virtual de Oracle Cloud Infrastructure (OCI).

---

## 3. Propósito de la aplicación

El propósito de Linker Python es ofrecer un servicio simple de acortamiento de URL. Por ejemplo, una dirección como:

```txt
https://www.ejemplo.com/documentos/proyecto/cloud/linker
```

puede convertirse en una URL corta como:

```txt
https://2.n-la-c.app/AbC123
```

Cuando un usuario accede a la URL corta, la aplicación consulta la base de datos y redirecciona automáticamente a la URL original.

---

## 4. Tecnologías utilizadas

- **Python 3:** lenguaje principal de la aplicación.
- **http.server:** librería estándar utilizada para implementar el servidor web.
- **sqlite3:** librería estándar utilizada para almacenar las URL en una base de datos SQLite.
- **urllib.parse:** procesamiento de rutas, formularios y URL.
- **SQLite:** base de datos utilizada para la persistencia de la información.
- **HTML, CSS y JavaScript:** interfaz de usuario.
- **systemd:** administración del servicio en Linux.
- **Git y GitHub:** control de versiones y almacenamiento del código fuente.

---

## 5. Estructura del proyecto

```txt
linker-python/
├── app.py
├── linker.db
├── requirements.txt
├── README.md
├── DOCUMENTO.md
└── scripts/
    ├── run_local.sh
    ├── install_vm.sh
    └── deploy.sh
```

El archivo principal del proyecto es `app.py`, donde se implementa el servidor HTTP, la lógica de negocio, la conexión con SQLite y la interfaz web.

---

## 6. Funcionamiento general

La aplicación expone las siguientes rutas:

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Muestra la interfaz web |
| POST | `/link` | Crea una URL corta |
| GET | `/<id>` | Redirecciona a la URL original |
| GET | `/health` | Verifica el estado de la aplicación |

El flujo principal de la aplicación es el siguiente:

1. El usuario accede a la interfaz web.
2. Ingresa una URL válida.
3. El cliente envía la URL mediante una petición `POST /link`.
4. El servidor valida la información recibida.
5. Se genera un identificador corto.
6. Se almacena la relación entre el identificador y la URL en SQLite.
7. El servidor responde con código **HTTP 201 Created** y el encabezado `Location`.
8. El cliente muestra la URL corta generada.
9. Cuando un usuario visita la URL corta, el servidor redirecciona automáticamente a la dirección original.

---

## 7. Cómo acceder al código fuente

El código fuente del proyecto se encuentra publicado en GitHub.

Repositorio:

```text
https://github.com/co-eiv-devsecops/linker2
```

Para obtener una copia del proyecto:

```bash
git clone https://github.com/co-eiv-devsecops/linker2.git
cd linker2
git checkout feat/newLinker2
cd linker-python
```

---

## 8. Cómo modificar y ejecutar el programa

El archivo principal de la aplicación es:

```txt
app.py
```

Algunos cambios comunes que pueden realizarse son:

- Modificar la interfaz web definida en la constante `INDEX_HTML`.
- Cambiar la longitud del identificador generado.
- Cambiar la base de datos utilizando la variable de entorno `LINKER_DB`.
- Cambiar el puerto mediante la variable de entorno `PORT`.

Al tratarse de una aplicación desarrollada en Python, **no existe un proceso de compilación**. Los cambios realizados se reflejan al ejecutar nuevamente la aplicación.

Para ejecutarla localmente:

```bash
python3 app.py
```

También puede utilizarse el script incluido:

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

La aplicación quedará disponible en:

```txt
http://localhost:8080
```

---

## 9. Instrucciones de despliegue

El despliegue se realizó sobre una máquina virtual Ubuntu en Oracle Cloud Infrastructure (OCI).

### Clonar el repositorio

```bash
git clone https://github.com/co-eiv-devsecops/linker2.git
cd linker2
git checkout feat/newLinker2
cd linker-python
```

### Configurar el servicio

Se creó un servicio de **systemd** para ejecutar la aplicación automáticamente al iniciar la máquina virtual.

Archivo del servicio:

```txt
/etc/systemd/system/linker.service
```

Contenido:

```ini
[Unit]
Description=Linker Python App
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/linker2/linker-python
ExecStart=/usr/bin/python3 /home/ubuntu/linker2/linker-python/app.py
Environment=PORT=8080
Restart=always
RestartSec=10
KillSignal=SIGINT
SyslogIdentifier=linker
User=ubuntu

[Install]
WantedBy=multi-user.target
```

Una vez configurado el servicio se ejecutaron los siguientes comandos:

```bash
sudo systemctl daemon-reload
sudo systemctl restart linker
sudo systemctl status linker
```

Con esta configuración la aplicación queda ejecutándose automáticamente y disponible en el puerto **8080**.

---

## 10. Verificación del despliegue

Para comprobar el correcto funcionamiento de la aplicación se utilizó el endpoint de salud:

```bash
curl http://localhost:8080/health
```

Respuesta esperada:

```json
{
    "status": "ok",
    "app": "linker-python"
}
```

También se verificó la página principal:

```bash
curl http://localhost:8080/
```

Finalmente, se comprobó el acceso mediante el dominio configurado para el equipo:

```txt
https://2.n-la-c.app
```

---

## 11. Scripts incluidos

### `scripts/run_local.sh`

Ejecuta la aplicación localmente.

Invocación:

```bash
./scripts/run_local.sh
```

---

### `scripts/install_vm.sh`

Instala y configura la aplicación en una máquina virtual Linux.

Invocación:

```bash
DOMAIN=2.n-la-c.app ./scripts/install_vm.sh
```

---

### `scripts/deploy.sh`

Automatiza el despliegue de la aplicación hacia la máquina virtual.

Invocación:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

---

## 12. Consideraciones de seguridad y operación

La aplicación valida que las URL ingresadas utilicen los esquemas `http` o `https`.

Las consultas a SQLite se realizan mediante consultas parametrizadas, evitando la concatenación directa de datos enviados por el usuario y reduciendo el riesgo de inyección SQL.

La aplicación se ejecuta como un servicio administrado por **systemd**, permitiendo su reinicio automático en caso de fallo.

Para un entorno de producción se recomienda complementar la solución con mecanismos de autenticación, registros de auditoría, monitoreo, copias de seguridad de la base de datos y políticas de limitación de solicitudes.

---

## 13. Conclusiones

Este proyecto demuestra cómo desarrollar y desplegar una aplicación web sencilla utilizando únicamente Python y librerías estándar. La solución implementa un servicio funcional de acortamiento de URL con persistencia en SQLite, una interfaz web simple y un despliegue automatizado sobre una máquina virtual en Oracle Cloud Infrastructure mediante un servicio de **systemd**.

El proyecto cumple con los objetivos planteados, permitiendo acceder al código fuente desde GitHub, modificar fácilmente la aplicación, ejecutarla sin proceso de compilación y desplegarla de forma permanente para su acceso mediante el dominio asignado al equipo.