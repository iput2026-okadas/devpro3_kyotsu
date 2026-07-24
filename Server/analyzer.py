import pandas as pd
from pathlib import Path


class EnvironmentAnalyzer:

    def __init__(self, csv_path="data/sensor.csv"):

        self.csv_path = Path(csv_path)

    ############################################################
    # CSV読み込み
    ############################################################

    def load_data(self):

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"{self.csv_path} が存在しません。"
            )

        df = pd.read_csv(self.csv_path)

        df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df

    ############################################################
    # 最新データ取得
    ############################################################

    def latest(self):

        df = self.load_data()

        latest = df.iloc[-1]

        return {

            "timestamp": str(latest["timestamp"]),

            "temperature": float(latest["temp"]),

            "humidity": float(latest["humid"]),

            "light": float(latest["light"])

        }

    ############################################################
    # 過去データ取得
    ############################################################

    def history(self, rows=30):

        df = self.load_data()

        return df.tail(rows)

    ############################################################
    # 温度変化量
    ############################################################

    def temperature_change(self):

        df = self.history()

        return round(

            df.iloc[-1]["temp"] -

            df.iloc[0]["temp"],

            2

        )

    ############################################################
    # 湿度変化量
    ############################################################

    def humidity_change(self):

        df = self.history()

        return round(

            df.iloc[-1]["humid"] -

            df.iloc[0]["humid"],

            2

        )

    ############################################################
    # 照度変化量
    ############################################################

    def light_change(self):

        df = self.history()

        return round(

            df.iloc[-1]["light"] -

            df.iloc[0]["light"],

            2

        )

    ############################################################
    # 平均値
    ############################################################

    def averages(self):

        df = self.history()

        return {

            "temperature":

                round(df["temp"].mean(),2),

            "humidity":

                round(df["humid"].mean(),2),

            "light":

                round(df["light"].mean(),2)

        }

    ############################################################
    # 最大値
    ############################################################

    def maximum(self):

        df = self.history()

        return {

            "temperature":

                float(df["temp"].max()),

            "humidity":

                float(df["humid"].max()),

            "light":

                float(df["light"].max())

        }

    ############################################################
    # 最小値
    ############################################################

    def minimum(self):

        df = self.history()

        return {

            "temperature":

                float(df["temp"].min()),

            "humidity":

                float(df["humid"].min()),

            "light":

                float(df["light"].min())

        }

    ############################################################
    # AIへ渡すデータ
    ############################################################

    def analysis_data(self):

        latest = self.latest()

        avg = self.averages()

        maximum = self.maximum()

        minimum = self.minimum()

        history = self.history()

        return {

            "latest": latest,

            "average": avg,

            "maximum": maximum,

            "minimum": minimum,

            "temperature_change":

                self.temperature_change(),

            "humidity_change":

                self.humidity_change(),

            "light_change":

                self.light_change(),

            "history":

                history.to_dict(orient="records")

        }


if __name__ == "__main__":

    analyzer = EnvironmentAnalyzer()

    result = analyzer.analysis_data()

    from pprint import pprint

    pprint(result)