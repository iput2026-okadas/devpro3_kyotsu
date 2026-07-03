def analyze_environment(temp, humidity, co2, light):
    causes = []
    solutions = []

    # -----------------------
    # 温度
    # -----------------------
    if temp >= 30:
        causes.append("室温が非常に高い")
        solutions.append("エアコンを使用する")
        solutions.append("直射日光を遮る")
        solutions.append("換気を行う")

    elif temp >= 27:
        causes.append("室温がやや高い")
        solutions.append("冷房を使用する")

    elif temp <= 15:
        causes.append("室温が低い")
        solutions.append("暖房を使用する")

    # -----------------------
    # 湿度
    # -----------------------
    if humidity >= 70:
        causes.append("湿度が高い")
        solutions.append("除湿機を使用する")
        solutions.append("換気を行う")

    elif humidity <= 40:
        causes.append("湿度が低い")
        solutions.append("加湿器を使用する")
        solutions.append("室内干しを行う")

    # -----------------------
    # CO2
    # -----------------------
    if co2 >= 1500:
        causes.append("CO2濃度が非常に高い")
        solutions.append("窓を開けて換気する")
        solutions.append("人数を減らす")

    elif co2 >= 1000:
        causes.append("CO2濃度が高い")
        solutions.append("換気を行う")

    # -----------------------
    # 照度
    # -----------------------
    if light <= 20:
        causes.append("室内が暗い")
        solutions.append("照明を点灯する")
        solutions.append("カーテンを開ける")

    elif light >= 90:
        causes.append("室内が明るすぎる")
        solutions.append("カーテンを閉める")

    # -----------------------
    # 複合判定
    # -----------------------
    if temp >= 28 and humidity >= 70:
        causes.append("蒸し暑い環境")
        solutions.append("冷房と除湿を同時に使用する")

    if temp >= 30 and co2 >= 1000:
        causes.append("高温かつ換気不足")
        solutions.append("換気しながら冷房を使用する")

    if humidity >= 70 and co2 >= 1000:
        causes.append("空気がこもっている")
        solutions.append("窓を開けて空気を入れ替える")

    if not causes:
        causes.append("室内環境は快適")
        solutions.append("現在の環境を維持する")

    return causes, list(dict.fromkeys(solutions))