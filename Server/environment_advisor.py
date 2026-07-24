def analyze_environment(temp, humidity, co2, light):
    causes = []
    solutions = []

    if temp >= 30:
        causes.append("室温が非常に高い")
        solutions.append("エアコンを使用する")
    elif temp >= 27:
        causes.append("室温がやや高い")
        solutions.append("扇風機を使用する")

    if humidity >= 70:
        causes.append("湿度が高い")
        solutions.append("除湿する")

    if co2 >= 1000:
        causes.append("CO2濃度が高い")
        solutions.append("換気する")

    if light <= 20:
        causes.append("室内が暗い")
        solutions.append("照明をつける")

    if not causes:
        causes.append("快適な環境")
        solutions.append("現在の環境を維持する")

    return causes, solutions
