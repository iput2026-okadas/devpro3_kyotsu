# prompt_builder.py

from datetime import datetime


class PromptBuilder:

    def __init__(self):
        pass

    def build(self, analysis_data, user_message):

        latest = analysis_data["latest"]
        average = analysis_data["average"]
        maximum = analysis_data["maximum"]
        minimum = analysis_data["minimum"]

        temp_change = analysis_data["temperature_change"]
        humid_change = analysis_data["humidity_change"]
        light_change = analysis_data["light_change"]

        history = analysis_data["history"]

        history_text = ""

        for row in history:

            history_text += (
                f"{row['timestamp']} "
                f"温度:{row['temp']}℃ "
                f"湿度:{row['humid']}% "
                f"照度:{row['light']}lux\n"
            )

        prompt = f"""
あなたは室内環境を分析するAIです。

あなたの仕事は
「現在の温度になった原因」
を説明することです。

推測ではなく、
与えられたデータを根拠にしてください。

=============================
【ユーザーからの質問】
{user_message}
=============================

【最新データ】

測定時刻
{latest['timestamp']}

温度
{latest['temperature']}℃

湿度
{latest['humidity']}%

照度
{latest['light']} lux

=============================

【平均】

平均温度
{average['temperature']}℃

平均湿度
{average['humidity']}%

平均照度
{average['light']} lux

=============================

【最大値】

温度
{maximum['temperature']}℃

湿度
{maximum['humidity']}%

照度
{maximum['light']} lux

=============================

【最小値】

温度
{minimum['temperature']}℃

湿度
{minimum['humidity']}%

照度
{minimum['light']} lux

=============================

【変化量】

温度変化
{temp_change}℃

湿度変化
{humid_change}%

照度変化
{light_change} lux

=============================

【過去データ】

{history_text}

=============================

回答ルール

1.
必ず最初に結論を書く

2.
次に根拠を書く

3.
温度
湿度
照度
の変化を考慮する

4.
過去データとの比較を行う

5.
改善方法も提案する

6.
回答は300文字以内

7.
箇条書きを使用してよい

8.
データにない内容は断定しない

9.
分かりやすい日本語で回答する
"""

        return prompt


if __name__ == "__main__":

    from analyzer import EnvironmentAnalyzer

    analyzer = EnvironmentAnalyzer()

    analysis = analyzer.analysis_data()

    builder = PromptBuilder()

    prompt = builder.build(
        analysis,
        "なぜ暑いですか？"
    )

    print(prompt)