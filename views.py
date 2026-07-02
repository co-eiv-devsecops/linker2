from pathlib import Path


VIEW_DIR = Path(__file__).resolve().parent / "views"


def render_index():
    return (VIEW_DIR / "index.html").read_text(encoding="utf-8")
