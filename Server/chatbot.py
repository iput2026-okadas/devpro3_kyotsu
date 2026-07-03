from environment_advisor import analyze_environment

class EnvironmentChatBot:

    def __init__(self, temp, hum, co2, light):
        self.temp = temp
        self.hum = hum
        self.co2 = co2
        self.light = light

        self.causes, self.solutions = analyze_environment(
            temp,
            hum,
            co2,
            light
        )

    def reply(self, message):

        message = message.lower()

        if "気温" in message or "暑い" in message:
            return f"現在の室温は{self.temp:.1f}℃です。"

        elif "湿度" in message:
            return f"現在の湿度は{self.hum:.1f}%です。"

        elif "co2" in message:
            return f"現在のCO2濃度は{self.co2}ppmです。"

        elif "明る" in message:
            return f"照度は{self.light}%です。"

        elif "原因" in message:

            return "考えられる原因\n・" + "\n・".join(self.causes)

        elif "解決" in message or "どうすれば" in message:

            return "おすすめの対策\n・" + "\n・".join(self.solutions)

        elif "状態" in message:

            return (
                f"""現在の室内環境

気温：{self.temp:.1f}℃
湿度：{self.hum:.1f}%
CO2：{self.co2}ppm
照度：{self.light}%

考えられる原因
・""" +
                "\n・".join(self.causes)
            )

        else:
            return (
                "質問例\n"
                "・現在の状態は？\n"
                "・原因を教えて\n"
                "・解決策は？\n"
                "・気温は？\n"
                "・湿度は？\n"
                "・CO2は？"
            )