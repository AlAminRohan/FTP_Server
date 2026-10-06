from flask import (Flask, request, redirect, url_for, render_template,
                   send_from_directory, flash, abort)
from pathlib import Path
from werkzeug.utils import secure_filename
import os
import shutil

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
UPLOAD_ROOT = UPLOAD_DIR.resolve()
MAX_FILE_SIZE = 5000 * 1024 * 1024  # 5000 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
app.config["MAX_FORM_PARTS"] = 1_000_000  # allow folders with many files


def human_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


@app.template_filter("filesize")
def filesize_filter(size):
    return human_size(size)


def safe_path(rel=""):
    """Resolve a relative path and make sure it stays inside UPLOAD_DIR."""
    path = (UPLOAD_ROOT / (rel or "")).resolve()
    if path != UPLOAD_ROOT and UPLOAD_ROOT not in path.parents:
        abort(404)
    return path


def rel_of(path):
    rel = path.resolve().relative_to(UPLOAD_ROOT).as_posix()
    return "" if rel == "." else rel


@app.route("/", defaults={"subpath": ""})
@app.route("/browse/<path:subpath>")
def index(subpath):
    folder = safe_path(subpath)
    if not folder.is_dir():
        abort(404)

    entries = []
    for path in folder.iterdir():
        try:
            st = path.stat()
        except OSError:
            continue  # broken symlink, permission problem, etc.

        if path.is_dir():
            try:
                count = sum(1 for _ in path.iterdir())
            except OSError:
                count = 0
            entries.append({"name": path.name, "rel": rel_of(path), "is_dir": True,
                            "size": 0, "count": count, "mtime": st.st_mtime})
        elif path.is_file():
            entries.append({"name": path.name, "rel": rel_of(path), "is_dir": False,
                            "size": st.st_size, "count": 0, "mtime": st.st_mtime})

    # Folders first (A-Z), then files (newest first)
    folders = sorted((e for e in entries if e["is_dir"]), key=lambda e: e["name"].lower())
    files = sorted((e for e in entries if not e["is_dir"]), key=lambda e: e["mtime"], reverse=True)

    current = rel_of(folder)
    parts = current.split("/") if current else []
    crumbs = [{"name": p, "path": "/".join(parts[:i + 1])} for i, p in enumerate(parts)]
    parent = "/".join(parts[:-1])

    return render_template("index.html", files=folders + files, current=current,
                           crumbs=crumbs, parent=parent)


@app.route("/upload", methods=["POST"])
def upload():
    folder = safe_path(request.form.get("current", ""))
    if not folder.is_dir():
        abort(404)
    current = rel_of(folder)
    saved = 0

    for file in request.files.getlist("files"):
        if not file or not file.filename:
            continue

        # Folder uploads send names like "Photos/2024/a.jpg".
        # Clean every part so nothing can escape the uploads folder.
        raw_parts = file.filename.replace("\\", "/").split("/")
        parts = [secure_filename(x) for x in raw_parts if x not in ("", ".", "..")]
        parts = [x for x in parts if x]
        if not parts:
            continue

        target_dir = folder.joinpath(*parts[:-1])
        target_dir.mkdir(parents=True, exist_ok=True)

        # Avoid overwriting an existing file.
        target = target_dir / parts[-1]
        stem, suffix = target.stem, target.suffix
        counter = 1
        while target.exists():
            target = target_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        file.save(target)
        saved += 1

    flash(f"{saved} file(s) uploaded successfully." if saved else "No files selected.",
          "success" if saved else "error")
    return redirect(url_for("index", subpath=current))


@app.route("/mkdir", methods=["POST"])
def make_folder():
    folder = safe_path(request.form.get("current", ""))
    if not folder.is_dir():
        abort(404)
    current = rel_of(folder)

    name = secure_filename(request.form.get("folder_name", "").strip())
    if not name:
        flash("Invalid folder name.", "error")
    elif (folder / name).exists():
        flash(f'"{name}" already exists.', "error")
    else:
        (folder / name).mkdir()
        flash(f'Folder "{name}" created.', "success")
    return redirect(url_for("index", subpath=current))


@app.route("/download/<path:filename>")
def download(filename):
    path = safe_path(filename)
    if not path.is_file():
        abort(404)
    return send_from_directory(UPLOAD_ROOT, rel_of(path), as_attachment=True)


@app.route("/view/<path:filename>")
def view_file(filename):
    path = safe_path(filename)
    if not path.is_file():
        abort(404)
    return send_from_directory(UPLOAD_ROOT, rel_of(path), as_attachment=False)


@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    path = safe_path(filename)
    if path == UPLOAD_ROOT or not path.exists():
        flash("File not found.", "error")
        return redirect(url_for("index", subpath=""))

    parent = rel_of(path.parent)
    name = path.name
    if path.is_dir():
        shutil.rmtree(path)
        flash(f'Folder "{name}" deleted.', "success")
    else:
        path.unlink()
        flash(f'"{name}" deleted.', "success")
    return redirect(url_for("index", subpath=parent))


@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum size is 5000 MB.", "error")
    return redirect(url_for("index", subpath=""))


if __name__ == "__main__":
    print("Mini File Transfer Server")
    print("Open http://<PC-IP>:8000 from your phone.")
    app.run(host="0.0.0.0", port=8000, debug=False)