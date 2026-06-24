import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

np.random.seed(42)
num_samples = 500

d_co2 = np.random.uniform(-50, 400, num_samples)
d_lux = np.random.uniform(-1000, 5000, num_samples)
d_humid = np.random.uniform(-15, 15, num_samples)

reasons = []
for co2, lux, humid in zip(d_co2, d_lux, d_humid):
    if lux > 2000 and humid < -2:
        reasons.append(0)  # 日差し
    elif co2 > 150:
        reasons.append(1)  # 人の入室
    elif humid < -5 or humid > 5:
        reasons.append(2)  # エアコン
    else:
        reasons.append(3)  # 自然変化

df = pd.DataFrame({
    'delta_co2': d_co2,
    'delta_lux': d_lux,
    'delta_humid': d_humid,
    'cause': reasons
})

X = df[['delta_co2', 'delta_lux', 'delta_humid']]
y = df['cause']

ai_model = DecisionTreeClassifier(max_depth=3, random_state=42)
ai_model.fit(X, y)

print("AIの学習が完了しました！")

def predict_temperature_cause(current_diff_co2, current_diff_lux, current_diff_humid):
    """
    現在の変化量をAIに入力し、気温変化の原因を出力する関数
    """
    input_data = pd.DataFrame([{
        'delta_co2': current_diff_co2,
        'delta_lux': current_diff_lux,
        'delta_humid': current_diff_humid
    }])
    
    predicted_code = ai_model.predict(input_data)[0]
    

    confidence = np.max(ai_model.predict_proba(input_data)) * 100
    
    cause_map = {
        0: "【日差し】窓から強い光（直射日光）が差し込んだため、室温が上昇しました。",
        1: "【人の在室】CO2濃度が上昇しています。人が部屋に入った（または滞在している）ことによる体温・呼気が原因です。",
        2: "【空調設備】湿度の急変動が検知されました。エアコンや除湿・加湿器が作動したことが原因の可能性が高いです。",
        3: "【自然変化】周囲のデータに大きな異常はありません。外気温に引っ張られる形で緩やかに変化しました。"
    }
    
    print(f"\n[AI推測結果] (確信度: {confidence:.1f}%)")
    print(cause_map[predicted_code])

#テスト運転 
print("\n--- テストケース1：部屋に人がたくさん入ってきた時 ---")
predict_temperature_cause(current_diff_co2=250, current_diff_lux=10, current_diff_humid=2)

print("\n--- テストケース2：カーテンを開けて日光が入った時 ---")
predict_temperature_cause(current_diff_co2=5, current_diff_lux=3500, current_diff_humid=-4)