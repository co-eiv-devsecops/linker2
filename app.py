from flask import Flask, request, redirect, abort
import sqlite3, uuid

app = Flask(__name__)
db = sqlite3.connect("linker2.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS shorturl (id TEXT PRIMARY KEY, url TEXT)")

@app.route("/<id>")
def get_link(id):
    cur = db.execute("SELECT url FROM shorturl WHERE id=?", (id,))
    row = cur.fetchone()
    return redirect(row[0], 301) if row else abort(404)

@app.route("/link", methods=["POST"])
def create_link():
    url = request.form.get("url")
    if url and (url.startswith("http://") or url.startswith("https://")):
        short_id = uuid.uuid4().hex[:8]
        db.execute("INSERT INTO shorturl (id, url) VALUES (?, ?)", (short_id, url))
        db.commit()
        return {"id": short_id, "url": url}
    return {"error": "Invalid or missing URL"}, 400

if __name__ == "__main__":
    app.run()