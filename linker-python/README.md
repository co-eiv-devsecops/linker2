# Linker Python

Implementación en Python del ejercicio **Linker**, una aplicación web para acortar URL desarrollada utilizando únicamente librerías estándar de Python.

La aplicación utiliza:

- `http.server` para el servidor web.
- `sqlite3` para la persistencia.
- `urllib.parse` para el procesamiento de rutas, formularios y URL.
- `secrets` para generar identificadores aleatorios.

---

# Tecnologías utilizadas

- Python 3
- SQLite
- Nginx
- systemd
- JavaScript
- HTML5
- CSS3

---

# Estructura del proyecto

```text
linker-python/
├── app.py
├── linker.db
├── requirements.txt
├── README.md
└── scripts/
    ├── run_local.sh
    ├── install_vm.sh
    └── deploy.sh
```

---

# Obtener el código fuente

Clonar el repositorio:

```bash
git clone https://github.com/co-eiv-devsecops/linker2.git
```

Ingresar al proyecto:

```bash
cd linker2
```

Cambiar a la rama correspondiente:

```bash
git checkout feat/newLinker2
```

Entrar al directorio de la aplicación:

```bash
cd linker-python
```

---

# Requisitos

- Python 3.12 o superior
- Git

No es necesario instalar dependencias externas, ya que el proyecto utiliza únicamente librerías estándar de Python.

Verificar la versión de Python:

```bash
python3 --version
```

---

# Modificar y ejecutar el programa

El archivo principal de la aplicación es:

```text
app.py
```

Después de realizar cualquier modificación basta con ejecutar nuevamente:

```bash
python3 app.py
```

También puede utilizarse el script incluido:

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

La aplicación estará disponible en:

```text
http://localhost:8080
```

---

# Cambiar el puerto

Es posible cambiar el puerto utilizando la variable de entorno `PORT`.

Ejemplo:

```bash
PORT=9090 python3 app.py
```

---

# Endpoints

| Método | Ruta | Descripción |
|---------|------|-------------|
| GET | `/` | Interfaz web |
| POST | `/link` | Crea una URL corta |
| GET | `/<id>` | Redirecciona a la URL original |
| GET | `/health` | Verifica el estado de la aplicación |

---

# Ejemplo de uso

Crear una URL corta:

```bash
curl -X POST http://localhost:8080/link \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "url=https://www.python.org"
```

Consultar el estado del servicio:

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

---

# Despliegue en Oracle Cloud

Clonar el proyecto:

```bash
git clone https://github.com/co-eiv-devsecops/linker2.git
cd linker2
git checkout feat/newLinker2
cd linker-python
```

El proyecto puede desplegarse utilizando el script:

```bash
TEAM_NUMBER=2 SERVER_USER=ubuntu ./scripts/deploy.sh
```

Durante el despliegue se realizan las siguientes tareas:

- Instalación de Python 3.
- Configuración de Nginx.
- Creación del servicio `systemd`.
- Inicio automático de la aplicación.
- Publicación del servicio en el puerto 8080.

El servicio utilizado es:

```text
/etc/systemd/system/linker.service
```

Para recargar el servicio después de una modificación:

```bash
sudo systemctl daemon-reload
sudo systemctl restart linker
```

Verificar el estado:

```bash
sudo systemctl status linker
```

---

# Verificación del despliegue

Comprobar que la aplicación está ejecutándose:

```bash
curl http://localhost:8080/health
```

Verificar la página principal:

```bash
curl http://localhost:8080/
```

---

# Acceso a la aplicación

Una vez desplegada, la aplicación queda disponible en:

```text
https://2.n-la-c.app
```

---
