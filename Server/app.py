import csv
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

try:
    from .ai_chatbot import (
        CsvAnalysisChatBot,
        CsvDataError,
        OllamaConnectionError,
        OllamaResponseError,
    )
except ImportError:
    from ai_chatbot import (
        CsvAnalysisChatBot,
        CsvDataError,
        OllamaConnectionError,
        OllamaResponseError,
    )

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHATBOT = CsvAnalysisChatBot(
    DATA_DIR,
    model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
    ollama_url=os.getenv(
        "OLLAMA_URL",
        "http://127.0.0.1:11434/api/chat",
    ),
)


def csv_files():
    return sorted(
        [path.name for path in DATA_DIR.glob("data-*.csv")],
        reverse=True,
    )


@app.route("/")
def index():
    # 1. data-*.csv ファイルの一覧を新しい順に取得
    available_files = csv_files()

    # 2. 選択されたファイル、または一番新しいファイルをターゲットにする
    selected_file = request.args.get("file") or (
        available_files[0] if available_files else None
    )
    
    columns, rows = [], []
    error = None
    
    # 平均値を計算するための変数（箱）を用意
    avg_temp = 0
    avg_hum = 0
    
    # 3. ファイルが存在すれば中身を読み込む
    if selected_file:
        selected_path = (DATA_DIR / selected_file).resolve()
        try:
            selected_path.relative_to(DATA_DIR.resolve())
            is_safe_path = (
                selected_file in available_files
                and selected_path.is_file()
            )
        except ValueError:
            is_safe_path = False

        if is_safe_path:
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
        csv_files=available_files,
        selected_file=selected_file,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        error=error,
        avg_temperature=avg_temp,
        avg_humidity=avg_hum,
    )


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "質問を入力してください。"}), 400
    if len(message) > 1000:
        return jsonify({"error": "質問は1000文字以内で入力してください。"}), 400

    available_files = csv_files()
    selected_file = payload.get("file")
    if selected_file is None and available_files:
        selected_file = available_files[0]
    if selected_file not in available_files:
        return jsonify({"error": "選択されたCSVが見つかりません。"}), 404

    try:
        answer = CHATBOT.chat(
            message.strip(),
            selected_file,
            payload.get("conversation"),
        )
    except FileNotFoundError:
        return jsonify({"error": "選択されたCSVが見つかりません。"}), 404
    except CsvDataError as error:
        return jsonify({"error": str(error)}), 422
    except OllamaConnectionError as error:
        return jsonify({"error": str(error)}), 503
    except OllamaResponseError as error:
        return jsonify({"error": str(error)}), 502

    return jsonify(
        {
            "response": answer,
            "selected_file": selected_file,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
