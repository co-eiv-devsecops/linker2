# Implementación de Linker en Python

## 1. Introducción

Este proyecto implementa una aplicación web llamada **Linker Python**, cuyo propósito es acortar URL. La aplicación toma como referencia el proyecto Linker original, pero se desarrolla en Python usando un servidor web simple.

El sistema permite que un usuario ingrese una URL larga desde un cliente web. La aplicación genera un identificador corto, almacena la relación entre el identificador y la URL original en SQLite, y permite acceder posteriormente a la URL original mediante una ruta corta.

## 2. Objetivo

Construir una aplicación de un solo archivo con pocas líneas de código, usando Python como lenguaje principal, para demostrar conceptos básicos de desarrollo y despliegue de aplicaciones en la nube.

## 3. Propósito de la aplicación

El propósito de Linker Python es ofrecer un servicio simple de acortamiento de URL. Por ejemplo, una URL extensa como:

```txt
https://www.ejemplo.com/documentos/proyecto/cloud/linker
```

puede convertirse en una URL corta como:

```txt
https://X.n-la-c.app/AbC123
```

Cuando un usuario accede a la URL corta, la aplicación consulta la base de datos y redirecciona automáticamente a la URL original.

## 4. Tecnologías utilizadas

- **Python 3:** lenguaje principal de la aplicación.
- **http.server:** librería estándar de Python usada para crear el servidor web sin frameworks externos.
- **sqlite3:** librería estándar de Python usada para trabajar con SQLite.
- **urllib.parse:** librería estándar usada para procesar rutas, formularios y URL.
- **SQLite:** base de datos liviana para almacenar las URL.
- **HTML, CSS y JavaScript:** cliente web de la aplicación.
- **Nginx:** proxy reverso para exponer la aplicación desde la máquina virtual.
- **systemd:** servicio de Linux para mantener la aplicación en ejecución.


## 5. Estructura del proyecto

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

El archivo principal es `app.py`. Allí se encuentra el servidor web, las rutas, la conexión con SQLite y el cliente web embebido.

## 6. Funcionamiento general

La aplicación expone las siguientes rutas:

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Muestra el cliente web |
| POST | `/link` | Recibe una URL y crea un enlace corto |
| GET | `/<id>` | Redirecciona al enlace original |
| GET | `/health` | Permite validar que la aplicación está activa |

El flujo principal es:

1. El usuario abre la aplicación desde el navegador.
2. El usuario escribe una URL válida.
3. El cliente web envía la URL mediante `POST /link`.
4. El servidor valida la URL.
5. El servidor genera un identificador corto.
6. La relación `id - URL original` se guarda en SQLite.
7. El servidor responde con código HTTP `201 Created` y el encabezado `Location`.
8. El cliente web muestra la URL corta generada.
9. Al abrir la URL corta, el servidor redirecciona a la URL original.

## 7. Cómo modificar el programa

Para modificar la aplicación se debe editar el archivo:

```txt
app.py
```

Algunos cambios comunes son:

- Cambiar los estilos visuales dentro de la constante `INDEX_HTML`.
- Modificar la longitud del identificador generado en la función `generate_id()`.
- Cambiar la base de datos mediante la variable de entorno `LINKER_DB`.
- Cambiar el puerto mediante la variable de entorno `PORT`.

## 8. Cómo ejecutar localmente

No es necesario crear ambiente virtual ni instalar dependencias externas. Ejecutar la aplicación:

```bash
python app.py
```

Abrir en el navegador:

```txt
http://localhost:8080
```

También se puede usar el script:

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

## 9. Instrucciones de despliegue

La aplicación se despliega en una máquina virtual Linux. El script `install_vm.sh` instala Python 3 y Nginx, crea el servicio de systemd y configura Nginx como proxy reverso.

Desde la VM, ejecutar:

```bash
chmod +x scripts/install_vm.sh
DOMAIN=2.n-la-c.app ./scripts/install_vm.sh
```

Para desplegar desde la máquina local hacia la VM:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

El script realiza las siguientes tareas:

1. Copia los archivos a la máquina virtual.
2. Ejecuta el instalador remoto.
3. Configura el servicio de Python con systemd.
4. Configura Nginx.
5. Crea y activa el servicio `linker-python`.

## 10. URL de despliegue

La aplicación desplegada debe estar disponible en:

```txt
https://2.n-la-c.app
```

## 11. Scripts incluidos

### `scripts/run_local.sh`

Ejecuta la aplicación localmente. Crea el ambiente virtual, instala dependencias y levanta el servidor.

Invocación:

```bash
./scripts/run_local.sh
```

### `scripts/install_vm.sh`

Instala la aplicación en una máquina virtual Linux.

Invocación:

```bash
DOMAIN=2.n-la-c.app ./scripts/install_vm.sh
```

### `scripts/deploy.sh`

Despliega la aplicación desde la máquina local hacia la VM.

Invocación:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

## 13. Consideraciones de seguridad y operación

La aplicación valida que la URL ingresada use los esquemas `http` o `https`. Además, las consultas a SQLite se realizan usando parámetros, evitando concatenar directamente los valores enviados por el usuario.

La base de datos usada por defecto es `linker.db`. En un escenario productivo se recomienda agregar autenticación administrativa, logs, métricas, backups de la base de datos y límites de uso por cliente.

## 14. Conclusiones

Este proyecto demuestra cómo construir una aplicación web mínima para acortar URL usando Python. La solución conserva la simplicidad del ejercicio original, pero agrega una interfaz web clara, persistencia en SQLite, scripts de despliegue y una configuración básica para ejecutarse en una máquina virtual.
