import json
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

DATABASE = os.environ.get("LINKER_DB", "linker.db")
PORT = int(os.environ.get("PORT", "8080"))


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS short_url (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL
            )
            """
        )


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def generate_id():
    return secrets.token_urlsafe(4).replace("-", "_")


class LinkerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_html(INDEX_HTML)
            return

        if path == "/health":
            self.send_json({"status": "ok", "app": "linker-python"})
            return

        short_id = path.strip("/")
        if not short_id or "/" in short_id:
            self.send_error(404, "Not Found")
            return

        with get_connection() as connection:
            row = connection.execute(
                "SELECT url FROM short_url WHERE id = ?",
                (short_id,),
            ).fetchone()

        if row is None:
            self.send_error(404, "Short URL not found")
            return

        self.send_response(301)
        self.send_header("Location", row["url"])
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/link":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)
        url = params.get("url", [""])[0].strip()

        if not is_valid_url(url):
            self.send_text("Invalid or missing URL", status=400)
            return

        with get_connection() as connection:
            while True:
                short_id = generate_id()
                exists = connection.execute(
                    "SELECT 1 FROM short_url WHERE id = ?",
                    (short_id,),
                ).fetchone()
                if not exists:
                    break

            connection.execute(
                "INSERT INTO short_url (id, url) VALUES (?, ?)",
                (short_id, url),
            )

        short_url = self.public_base_url() + "/" + short_id
        self.send_response(201)
        self.send_header("Location", short_url)
        self.end_headers()

    def public_base_url(self):
        host = self.headers.get("Host", f"localhost:{PORT}")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        return f"{proto}://{host}"

    def send_html(self, content, status=200):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, data, status=200):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_text(self, content, status=200):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))


INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Linker Python</title>
    <style>
        :root {
            color-scheme: light;
            font-family: Arial, Helvetica, sans-serif;
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --bg: #f3f6fb;
            --card: #ffffff;
            --text: #172033;
            --muted: #64748b;
            --error: #b91c1c;
            --success: #166534;
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, .18), transparent 30%),
                linear-gradient(135deg, #f8fafc, var(--bg));
            color: var(--text);
            padding: 24px;
        }

        main {
            width: min(760px, 100%);
            background: var(--card);
            padding: 36px;
            border-radius: 24px;
            box-shadow: 0 24px 70px rgba(15, 23, 42, .12);
        }

        .badge {
            display: inline-flex;
            padding: 6px 12px;
            border-radius: 999px;
            background: #dbeafe;
            color: #1e40af;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 16px;
        }

        h1 {
            margin: 0 0 10px;
            font-size: clamp(32px, 6vw, 56px);
            line-height: 1;
        }

        p {
            margin: 0 0 28px;
            color: var(--muted);
            font-size: 17px;
            line-height: 1.5;
        }

        form {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 12px;
        }

        input {
            width: 100%;
            padding: 16px 18px;
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            font-size: 16px;
            outline: none;
        }

        input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, .12);
        }

        button {
            border: none;
            padding: 0 24px;
            border-radius: 14px;
            background: var(--primary);
            color: white;
            font-weight: 700;
            font-size: 16px;
            cursor: pointer;
        }

        button:hover { background: var(--primary-dark); }

        #result {
            margin-top: 24px;
            padding: 18px;
            border-radius: 16px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            display: none;
        }

        #result strong {
            display: block;
            margin-bottom: 8px;
        }

        #short-link {
            color: var(--primary);
            font-weight: 700;
            word-break: break-all;
        }

        .error { color: var(--error); }
        .success { color: var(--success); }

        footer {
            margin-top: 28px;
            color: var(--muted);
            font-size: 13px;
        }

        @media (max-width: 620px) {
            main { padding: 26px; }
            form { grid-template-columns: 1fr; }
            button { padding: 16px; }
        }
    </style>
</head>
<body>
    <main>
        <span class="badge">Cloud · Python · SQLite</span>
        <h1>Linker Python</h1>
        <p>
            Servicio simple para acortar URL. Escribe una dirección completa,
            genera un enlace corto y compártelo.
        </p>

        <form id="form">
            <input id="url" name="url" type="url" placeholder="https://ejemplo.com/recurso" required autofocus />
            <button id="button" type="submit">Acortar</button>
        </form>

        <section id="result">
            <strong id="message"></strong>
            <a id="short-link" href="#" target="_blank" rel="noopener"></a>
        </section>

        <footer>
            Aplicación basada en el ejercicio Linker.
        </footer>
    </main>

    <script>
        const form = document.getElementById('form');
        const urlInput = document.getElementById('url');
        const result = document.getElementById('result');
        const message = document.getElementById('message');
        const shortLink = document.getElementById('short-link');
        const button = document.getElementById('button');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            result.style.display = 'none';
            message.className = '';
            shortLink.textContent = '';
            shortLink.href = '#';
            button.disabled = true;
            button.textContent = 'Creando...';

            const data = new URLSearchParams();
            data.append('url', urlInput.value);

            try {
                const response = await fetch('/link', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
                    },
                    body: data
                });

                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(error || 'No fue posible crear el enlace.');
                }

                const location = response.headers.get('Location');
                message.textContent = 'Enlace creado correctamente:';
                message.className = 'success';
                shortLink.textContent = location;
                shortLink.href = location;
                result.style.display = 'block';
                form.reset();
                urlInput.focus();
            } catch (error) {
                message.textContent = error.message;
                message.className = 'error';
                result.style.display = 'block';
            } finally {
                button.disabled = false;
                button.textContent = 'Acortar';
            }
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    init_database()
    server = HTTPServer(("0.0.0.0", PORT), LinkerHandler)
    print(f"Linker Python running on http://0.0.0.0:{PORT}")
    server.serve_forever()
