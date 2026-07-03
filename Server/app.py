import csv
from pathlib import Path
from flask import Flask, render_template, request

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

@app.route("/")
def index():
    # 1. data-*.csv ファイルの一覧を新しい順に取得
    csv_files = sorted([p.name for p in DATA_DIR.glob("data-*.csv")], reverse=True)
    
    # 2. 選択されたファイル、または一番新しいファイルをターゲットにする
    selected_file = request.args.get("file") or (csv_files[0] if csv_files else None)
    
    columns, rows = [], []
    error = None
    
    # 平均値を計算するための変数（箱）を用意
    avg_temp = 0
    avg_hum = 0
    
    # 3. ファイルが存在すれば中身を読み込む
    if selected_file:
        selected_path = DATA_DIR / selected_file
        if selected_path.exists():
            with selected_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = list(reader.fieldnames or [])
                rows = list(reader)
                
            # --- 【追加】温度と湿度の平均値を計算する処理 ---
            temperatures = []
            humidities = []
            
            for row in rows:
                try:
                    # 見出し名 "temp" と "humid" から数字を抜き出してリストに集める
                    if row.get("temp") is not None:
                        temperatures.append(float(row["temp"]))
                    if row.get("humid") is not None:
                        humidities.append(float(row["humid"]))
                except (ValueError, TypeError):
                    continue  # ヘッダーや空文字などのエラー対策
            
            # 合計 ÷ データ件数 で平均を出す（データが存在するときだけ）
            if temperatures:
                avg_temp = round(sum(temperatures) / len(temperatures), 1)
            if humidities:
                avg_hum = round(sum(humidities) / len(humidities), 1)
            # -----------------------------------------------
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
        avg_temperature=avg_temp,  # ★新しくHTMLに計算結果をパスする
        avg_humidity=avg_hum       # ★新しくHTMLに計算結果をパスする
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)