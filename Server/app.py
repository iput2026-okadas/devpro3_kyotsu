import csv
import math
import os
import tempfile
from datetime import datetime
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

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
FORM_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
CLIENT_ID_COLUMNS = ("client-id", "client_id", "clientId", "id")
SENSOR_COLUMNS = ("temp", "humid", "co2", "light_percent")


def csv_files():
    return sorted(
        [path.name for path in DATA_DIR.glob("data-*.csv")],
        reverse=True,
    )


def _resolve_csv_path(file_name, available_files=None):
    if not isinstance(file_name, str):
        return None

    available_files = (
        available_files if available_files is not None else csv_files()
    )
    selected_path = (DATA_DIR / file_name).resolve()
    try:
        selected_path.relative_to(DATA_DIR.resolve())
    except ValueError:
        return None

    if file_name not in available_files or not selected_path.is_file():
        return None
    return selected_path


def _read_csv(csv_path):
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader.fieldnames or []), list(reader)


def _find_client_id_column(columns):
    return next(
        (column for column in CLIENT_ID_COLUMNS if column in columns),
        None,
    )


def _unique_client_ids(rows, client_id_column):
    if client_id_column is None:
        return []

    client_ids = []
    seen_client_ids = set()
    for row in rows:
        value = row.get(client_id_column)
        if value is None:
            continue
        normalized_value = str(value).strip()
        if normalized_value and normalized_value not in seen_client_ids:
            client_ids.append(normalized_value)
            seen_client_ids.add(normalized_value)
    return client_ids


def _average(rows, column):
    values = []
    for row in rows:
        try:
            value = float(row.get(column, ""))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return round(sum(values) / len(values), 1) if values else 0


def _next_record_id(rows):
    record_ids = []
    for row in rows:
        try:
            record_ids.append(int(row.get("id", "")))
        except (TypeError, ValueError):
            continue
    return str(max(record_ids, default=-1) + 1)


def _parse_number(value, label, minimum=None, maximum=None):
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{label}を入力してください")

    try:
        number = float(text)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}は数値で入力してください") from error

    if not math.isfinite(number):
        raise ValueError(f"{label}は有限の数値で入力してください")
    if minimum is not None and number < minimum:
        raise ValueError(f"{label}は{minimum:g}以上で入力してください")
    if maximum is not None and number > maximum:
        raise ValueError(f"{label}は{maximum:g}以下で入力してください")
    return text


def _parse_timestamp(value):
    text = str(value).strip() if value is not None else ""
    try:
        timestamp = datetime.strptime(text, FORM_TIMESTAMP_FORMAT)
    except ValueError as error:
        raise ValueError("timestampを秒まで指定してください") from error
    return timestamp, timestamp.strftime(TIMESTAMP_FORMAT)


def _timestamp_sort_key(row_with_position):
    position, row = row_with_position
    try:
        timestamp = datetime.strptime(
            row.get("timestamp", ""),
            TIMESTAMP_FORMAT,
        )
        return 0, timestamp, position
    except (TypeError, ValueError):
        return 1, datetime.max, position


def _write_csv_atomically(csv_path, columns, rows):
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=csv_path.parent,
        prefix=f".{csv_path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, csv_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


@app.route("/")
def index():
    available_files = csv_files()
    selected_file = request.args.get("file") or (
        available_files[0] if available_files else None
    )

    columns, rows = [], []
    error = None
    client_id_column = None
    client_ids = []

    if selected_file:
        selected_path = _resolve_csv_path(selected_file, available_files)
        if selected_path:
            columns, rows = _read_csv(selected_path)
            client_id_column = _find_client_id_column(columns)
            client_ids = _unique_client_ids(rows, client_id_column)
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
        avg_temperature=_average(rows, "temp"),
        avg_humidity=_average(rows, "humid"),
        avg_co2=_average(rows, "co2"),
        avg_light=_average(rows, "light_percent"),
        client_id_column=client_id_column,
        client_ids=client_ids,
    )


@app.post("/api/data")
def add_csv_data():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="入力内容を読み取れませんでした"), 400

    file_name = payload.get("file")
    csv_path = _resolve_csv_path(file_name)
    if csv_path is None:
        return jsonify(error="選択したCSVが見つかりません"), 404

    columns, rows = _read_csv(csv_path)
    client_id_column = _find_client_id_column(columns)
    if client_id_column is None:
        return jsonify(
            error="このCSVにはclient-id列、client_id列、またはid列がありません"
        ), 400
    if "timestamp" not in columns:
        return jsonify(error="このCSVにはtimestamp列がありません"), 400
    if "temp" not in columns or "humid" not in columns:
        return jsonify(error="このCSVにはtemp列またはhumid列がありません"), 400

    available_client_ids = _unique_client_ids(rows, client_id_column)
    client_id = str(payload.get("client_id", "")).strip()
    if client_id not in available_client_ids:
        return jsonify(
            error="CSVに存在するclient-idを選択してください"
        ), 400

    try:
        timestamp, formatted_timestamp = _parse_timestamp(
            payload.get("timestamp")
        )
        values = {
            "temp": _parse_number(payload.get("temp"), "temp"),
            "humid": _parse_number(
                payload.get("humid"),
                "humid",
                0,
                100,
            ),
            "co2": _parse_number(payload.get("co2"), "co2", 0),
            "light_percent": _parse_number(
                payload.get("light_percent"),
                "light_percent",
                0,
                100,
            ),
        }
    except ValueError as error:
        return jsonify(error=str(error)), 400

    for column in SENSOR_COLUMNS:
        if column not in columns:
            columns.append(column)

    new_row = dict.fromkeys(columns, "")
    new_row[client_id_column] = client_id
    if "id" in columns and client_id_column != "id":
        new_row["id"] = _next_record_id(rows)
    new_row["timestamp"] = formatted_timestamp
    new_row.update(values)

    rows.append(new_row)
    positioned_rows = list(enumerate(rows))
    positioned_rows.sort(key=_timestamp_sort_key)
    rows = [row for _, row in positioned_rows]
    inserted_index = next(
        index for index, row in enumerate(rows) if row is new_row
    )

    _write_csv_atomically(csv_path, columns, rows)

    return jsonify(
        message="データを追加しました",
        inserted_index=inserted_index,
        timestamp=timestamp.strftime(TIMESTAMP_FORMAT),
    ), 201


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
