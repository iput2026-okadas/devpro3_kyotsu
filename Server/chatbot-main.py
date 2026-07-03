from environment_advisor import analyze_environment

temperature = 29.8
humidity = 76
co2 = 1350
light = 18

causes, solutions = analyze_environment(
    temperature,
    humidity,
    co2,
    light
)

print("【原因】")
for c in causes:
    print("-", c)

print("\n【解決策】")
for s in solutions:
    print("-", s)