from flask import Flask, request, redirect, url_for, render_template, send_from_directory, flash
from pathlib import Path
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 5000 * 1024 * 1024  # 5000 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


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


@app.route("/")
def index():
    files = []
    for path in sorted(UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            files.append({
                "name": path.name,
                "size": path.stat().st_size,
                "mtime": path.stat().st_mtime,
            })
    return render_template("index.html", files=files)


@app.route("/upload", methods=["POST"])
def upload():
    uploaded_files = request.files.getlist("files")
    saved = 0

    for file in uploaded_files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        if not filename:
            continue

        # Avoid overwriting an existing file.
        target = UPLOAD_DIR / filename
        stem, suffix = target.stem, target.suffix
        counter = 1
        while target.exists():
            target = UPLOAD_DIR / f"{stem} ({counter}){suffix}"
            counter += 1

        file.save(target)
        saved += 1

    flash(f"{saved} file(s) uploaded successfully." if saved else "No files selected.", "success" if saved else "error")
    return redirect(url_for("index"))


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)



@app.route("/view/<path:filename>")
def view_file(filename):
    return send_from_directory(
        UPLOAD_DIR,
        filename,
        as_attachment=False
    )

@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    path = UPLOAD_DIR / filename
    if path.is_file() and path.parent.resolve() == UPLOAD_DIR.resolve():
        path.unlink()
        flash(f'"{path.name}" deleted.', "success")
    else:
        flash("File not found.", "error")
    return redirect(url_for("index"))



@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum size is 5000 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    print("Mini File Transfer Server")
    print("Open http://<PC-IP>:8000 from your phone.")
    app.run(host="0.0.0.0", port=8000, debug=False)
