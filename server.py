"""
AIGCXUSIR Gallery Server
"""

import os, json, hashlib, hmac, time, re
from functools import wraps
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__, static_folder=".", static_url_path="")
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

BASE_DIR = Path(__file__).parent.resolve()
MEDIA_DIR = BASE_DIR / "media"
MEDIA_JSON = BASE_DIR / "media.json"
UPLOAD_PASSWORD = "aigcxusir2026"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov", ".avi"}
MEDIA_DIR.mkdir(exist_ok=True)

def safe_filename(original_name):
    """保留原始文件名，只去掉路径分隔符等危险字符"""
    name = os.path.basename(original_name)
    name = re.sub(r'[/\\:*?"<>|]', '_', name)
    if not name:
        name = "untitled"
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    base = name[:-(len(ext))] if ext else name
    c = 0
    while (MEDIA_DIR / name).exists():
        c += 1
        name = base + "_" + str(c) + ext
    return name

def require_password(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-upload-password", "")
        expected = hashlib.sha256(UPLOAD_PASSWORD.encode()).hexdigest()
        actual = hashlib.sha256(token.encode()).hexdigest()
        if not hmac.compare_digest(actual, expected):
            return jsonify({"error": "密码错误"}), 401
        return f(*args, **kwargs)
    return decorated

def rebuild_media_json():
    items = []
    for f in sorted(os.listdir(MEDIA_DIR)):
        ext = os.path.splitext(f)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            items.append({"type": "image", "file": f})
        elif ext in (".mp4", ".webm", ".mov", ".avi"):
            items.append({"type": "video", "file": f})
    with open(MEDIA_JSON, "w", encoding="utf-8") as fp:
        json.dump(items, fp, ensure_ascii=False, indent=2)
    return items

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(BASE_DIR, path)

@app.route("/api/media", methods=["GET"])
def get_media():
    if MEDIA_JSON.exists():
        with open(MEDIA_JSON, "r", encoding="utf-8") as fp:
            return jsonify(json.load(fp))
    return jsonify(rebuild_media_json())

@app.route("/api/upload", methods=["POST"])
@require_password
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名无效"}), 400
    filename = safe_filename(file.filename)
    if filename is None:
        return jsonify({"error": "不支持的文件格式（仅支持 jpg/png/gif/webp/mp4/webm/mov/avi）"}), 400
    save_path = MEDIA_DIR / filename
    file.save(save_path)
    items = rebuild_media_json()
    t = "image" if os.path.splitext(filename)[1].lower() in (".jpg",".jpeg",".png",".gif",".webp") else "video"
    return jsonify({"message": "上传成功", "file": filename, "type": t, "total": len(items)})

@app.route("/api/delete", methods=["POST"])
@require_password
def delete_file():
    data = request.get_json(silent=True) or {}
    fn = data.get("file", "")
    if not fn:
        return jsonify({"error": "未指定文件"}), 400
    fn = os.path.basename(fn)
    fp = MEDIA_DIR / fn
    if not fp.exists():
        return jsonify({"error": "文件不存在"}), 404
    os.remove(fp)
    return jsonify({"message": "删除成功", "total": len(rebuild_media_json())})

@app.route("/api/verify", methods=["POST"])
def verify_password():
    data = request.get_json(silent=True) or {}
    expected = hashlib.sha256(UPLOAD_PASSWORD.encode()).hexdigest()
    actual = hashlib.sha256(data.get("password","").encode()).hexdigest()
    if hmac.compare_digest(actual, expected):
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

if __name__ == "__main__":
    print("AIGCXUSIR Gallery Server")
    items = rebuild_media_json()
    print(f"  Media: {len(items)} files")
    print(f"  Password: ******")
    print(f"  Open: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
