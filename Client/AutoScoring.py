import pandas as pd
import math
import os

SOURCE_CSV = "temperature_humidity.csv"
OUTPUT_CSV = "ai_dataset.csv"

IDEAL_TEMP = 23.5
IDEAL_HUM = 50.0


def calculate_comfort(temp, humidity):
    temp_diff = abs(temp - IDEAL_TEMP)
    hum_diff = abs(humidity - IDEAL_HUM)

    score = math.sqrt(
        temp_diff ** 2 +
        (hum_diff / 5) ** 2
    )

    if score <= 1.5:
        return 5
    elif score <= 3:
        return 4
    elif score <= 6:
        return 3
    elif score <= 9:
        return 2
    else:
        return 1


# AI用CSVが無ければ作成
if not os.path.exists(OUTPUT_CSV):

    df = pd.DataFrame(
        columns=[
            "id",
            "timestamp",
            "temp",
            "humid",
            "comfort"
        ]
    )

    df.to_csv(OUTPUT_CSV, index=False)


# 元データ読込
source = pd.read_csv(SOURCE_CSV)

# AI用読込
ai = pd.read_csv(OUTPUT_CSV)


# まだ追加されていないデータだけ取得
new_data = source[~source["id"].isin(ai["id"])].copy()

if len(new_data) > 0:

    new_data["comfort"] = new_data.apply(
        lambda row: calculate_comfort(
            row["temp"],
            row["humid"]
        ),
        axis=1
    )

    ai = pd.concat(
        [ai, new_data],
        ignore_index=True
    )

    ai.to_csv(
        OUTPUT_CSV,
        index=False
    )

    print(f"{len(new_data)}件追加しました。")

else:
    print("追加するデータはありません。")