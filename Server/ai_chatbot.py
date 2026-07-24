import csv
from pathlib import Path
from statistics import mean

import requests


class CsvDataError(ValueError):
    """CSVがAI分析に利用できない場合のエラー。"""


class OllamaConnectionError(RuntimeError):
    """Ollamaへ接続できない場合のエラー。"""


class OllamaResponseError(RuntimeError):
    """Ollamaから正常な回答を取得できない場合のエラー。"""


class CsvAnalysisChatBot:
    FIELD_ALIASES = {
        "timestamp": ("timestamp", "datetime", "time", "日時", "時刻"),
        "client_id": ("client_id", "client", "端末id", "クライアントid"),
        "temperature": ("temp", "temperature", "温度", "室温"),
        "humidity": ("humid", "humidity", "湿度"),
        "co2": ("co2", "co2_ppm", "二酸化炭素"),
        "light": (
            "light_percent",
            "light",
            "lux",
            "照度",
            "光量",
        ),
    }
    REQUIRED_FIELDS = ("temperature", "humidity")
    METRICS = (
        ("temperature", "温度", "℃"),
        ("humidity", "湿度", "%"),
        ("co2", "CO2", "ppm"),
        ("light", "光量", ""),
    )

    def __init__(
        self,
        data_dir,
        model="gemma3:4b",
        ollama_url="http://127.0.0.1:11434/api/chat",
        request_timeout=180,
    ):
        self.data_dir = Path(data_dir).resolve()
        self.model = model
        self.ollama_url = ollama_url
        self.request_timeout = request_timeout

    def _csv_path(self, filename):
        if not isinstance(filename, str):
            raise CsvDataError("CSVファイル名が不正です。")

        name = Path(filename).name
        if (
            name != filename
            or not name.startswith("data-")
            or not name.endswith(".csv")
        ):
            raise CsvDataError("CSVファイル名が不正です。")

        path = (self.data_dir / name).resolve()
        if path.parent != self.data_dir or not path.is_file():
            raise FileNotFoundError(f"{name} が見つかりません。")
        return path

    @classmethod
    def _resolve_columns(cls, fieldnames):
        normalized = {name.strip().lower(): name for name in fieldnames}
        columns = {}
        for field, aliases in cls.FIELD_ALIASES.items():
            columns[field] = next(
                (normalized[alias.lower()] for alias in aliases if alias.lower() in normalized),
                None,
            )

        missing = [
            field
            for field in cls.REQUIRED_FIELDS
            if columns.get(field) is None
        ]
        if missing:
            labels = {
                "temperature": "温度（temp）",
                "humidity": "湿度（humid）",
            }
            raise CsvDataError(
                "AI分析に必要な列がありません: "
                + ", ".join(labels[field] for field in missing)
            )
        return columns

    @staticmethod
    def _optional_text(row, column):
        if column is None:
            return None
        value = str(row.get(column, "") or "").strip()
        return value or None

    @staticmethod
    def _number(row, column, line_number, required=False):
        if column is None:
            return None
        value = str(row.get(column, "") or "").strip()
        if not value:
            if required:
                raise CsvDataError(f"{line_number}行目に空のセンサー値があります。")
            return None
        try:
            return float(value)
        except ValueError as error:
            raise CsvDataError(
                f"{line_number}行目に数値ではないセンサー値があります。"
            ) from error

    def load_rows(self, filename):
        with self._csv_path(filename).open(
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:
            reader = csv.DictReader(csv_file)
            columns = self._resolve_columns(reader.fieldnames or [])
            rows = []

            for line_number, raw_row in enumerate(reader, start=2):
                if not any(str(value or "").strip() for value in raw_row.values()):
                    continue
                rows.append(
                    {
                        "timestamp": self._optional_text(
                            raw_row,
                            columns["timestamp"],
                        )
                        or f"{line_number - 1}件目",
                        "client_id": self._optional_text(
                            raw_row,
                            columns["client_id"],
                        ),
                        "temperature": self._number(
                            raw_row,
                            columns["temperature"],
                            line_number,
                            required=True,
                        ),
                        "humidity": self._number(
                            raw_row,
                            columns["humidity"],
                            line_number,
                            required=True,
                        ),
                        "co2": self._number(
                            raw_row,
                            columns["co2"],
                            line_number,
                        ),
                        "light": self._number(
                            raw_row,
                            columns["light"],
                            line_number,
                        ),
                    }
                )

        if not rows:
            raise CsvDataError("AI分析に利用できるデータ行がありません。")
        return rows

    @classmethod
    def _summary(cls, rows):
        first = rows[0]
        latest = rows[-1]
        lines = [
            f"分析件数: {len(rows)}件",
            f"先頭時刻: {first['timestamp']}",
            f"最新時刻: {latest['timestamp']}",
        ]

        for key, label, unit in cls.METRICS:
            values = [row[key] for row in rows if row[key] is not None]
            if not values:
                lines.append(f"{label}: CSVに列または値なし")
                continue
            suffix = unit
            lines.append(
                f"{label}: 最新 {values[-1]:.2f}{suffix}, "
                f"平均 {mean(values):.2f}{suffix}, "
                f"最小 {min(values):.2f}{suffix}, "
                f"最大 {max(values):.2f}{suffix}, "
                f"区間変化 {values[-1] - values[0]:+.2f}{suffix}"
            )
        return "\n".join(lines)

    @classmethod
    def _history(cls, rows):
        history_lines = []
        for row in rows:
            values = []
            if row["client_id"]:
                values.append(f"client_id={row['client_id']}")
            for key, label, unit in cls.METRICS:
                if row[key] is not None:
                    values.append(f"{label}={row[key]:.2f}{unit}")
            history_lines.append(f"- {row['timestamp']}: " + ", ".join(values))
        return "\n".join(history_lines)

    @staticmethod
    def _conversation_messages(conversation):
        messages = []
        if not isinstance(conversation, list):
            return messages

        for item in conversation[-10:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content:
                messages.append(
                    {
                        "role": role,
                        "content": str(content)[:3000],
                    }
                )
        return messages

    def chat(self, user_message, csv_filename, conversation=None):
        rows = self.load_rows(csv_filename)[-30:]
        system_prompt = (
            "あなたは室内環境CSVの分析アシスタントです。"
            "提供されたCSV要約・履歴と会話履歴だけを根拠に、日本語で結論から"
            "簡潔に回答してください。取得されていない値や、データだけでは特定"
            "できない原因を断定してはいけません。改善策は根拠とともに提案してください。"
        )
        user_prompt = (
            f"質問:\n{user_message}\n\n"
            f"対象CSV:\n{csv_filename}\n\n"
            f"直近最大30件の集計:\n{self._summary(rows)}\n\n"
            f"直近最大30件の履歴:\n{self._history(rows)}"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._conversation_messages(conversation))
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=(5, self.request_timeout),
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            raise OllamaConnectionError("Ollamaへ接続できません。") from error
        except requests.RequestException as error:
            raise OllamaResponseError("Ollamaとの通信に失敗しました。") from error

        if not response.ok:
            raise OllamaResponseError(
                f"Ollama APIがエラーを返しました（HTTP {response.status_code}）。"
            )

        try:
            answer = str(response.json()["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError) as error:
            raise OllamaResponseError("Ollamaの応答形式が不正です。") from error

        if not answer:
            raise OllamaResponseError("Ollamaから空の回答が返されました。")
        return answer
