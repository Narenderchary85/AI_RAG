import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from app.config import DATA_DIR, COLLECTION_NAME
from app.ingest import ingest_file
from app.qa import answer_question

ALLOWED_EXT = {"pdf", "txt", "md", "docx", "doc"}
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error":"no file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error":"empty filename"}), 400
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        dest = os.path.join(DATA_DIR, filename)
        f.save(dest)
        res = ingest_file(dest, collection_name=COLLECTION_NAME)
        return jsonify({"status":"ok", "ingest": res}), 200
    return jsonify({"error":"bad file type"}), 400

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error":"missing question"}), 400
    q = data["question"]
    k = int(data.get("k", 5))
    result = answer_question(q, k=k, collection_name=COLLECTION_NAME)
    sources = [{"page_content": d.page_content, "metadata": getattr(d, "metadata", {})} for d in result.get("source_documents", [])]
    return jsonify({"answer": result.get("result"), "sources": sources})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), debug=False)
