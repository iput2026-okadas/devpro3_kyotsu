import csv
from pathlib import Path
from flask import Flask, render_template, request

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

@app.route("/")
def index():
    # 1. data-*.csv ファイルの一覧を新しい順に取得
    csv_files = sorted([p.name for p in BASE_DIR.glob("data-*.csv")], reverse=True)
    
    # 2. 選択されたファイル、または一番新しいファイルをターゲットにする
    selected_file = request.args.get("file") or (csv_files[0] if csv_files else None)
    
    columns, rows = [], []
    error = None
    
    # 3. ファイルが存在すれば中身を読み込む
    if selected_file:
        selected_path = BASE_DIR / selected_file
        if selected_path.exists():
            with selected_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = list(reader.fieldnames or [])
                rows = list(reader)
        else:
            error = f"{selected_file} が見つかりません"

    return render_template(
        "index.html",
        csv_files=csv_files,
        selected_file=selected_file,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        error=error,
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)