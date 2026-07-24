import csv
from pathlib import Path
from statistics import mean
import requests
class TemperatureChatBot:
 def __init__(self,data_dir,model="gemma3:4b",ollama_url="http://localhost:11434/api/chat"):
  self.data_dir=Path(data_dir).resolve();self.model=model;self.ollama_url=ollama_url
 def _path(self,filename):
  name=Path(filename).name
  if name!=filename or not name.startswith("data-") or not name.endswith(".csv"):raise ValueError("不正なCSVファイル名です。")
  path=(self.data_dir/name).resolve()
  if path.parent!=self.data_dir or not path.exists():raise FileNotFoundError(f"{name}が見つかりません。")
  return path
 @staticmethod
 def _find(fields,names,required=True):
  n={x.strip().lower():x for x in fields}
  for x in names:
   if x.lower() in n:return n[x.lower()]
  if required:raise ValueError("必要な列がありません: "+",".join(names))
  return None
 def load(self,filename):
  with self._path(filename).open(newline="",encoding="utf-8-sig") as f:
   r=csv.DictReader(f);fields=r.fieldnames or [];tc=self._find(fields,["timestamp","datetime","time","日時","時刻"],False);pc=self._find(fields,["temp","temperature","温度","室温"]);hc=self._find(fields,["humid","humidity","湿度"]);lc=self._find(fields,["light","lux","照度","光量"]);rows=[]
   for i,row in enumerate(r,start=2):
    if not any(str(v or "").strip() for v in row.values()):continue
    try:rows.append({"timestamp":str(row.get(tc,"")) if tc else f"{i-1}件目","temperature":float(row[pc]),"humidity":float(row[hc]),"light":float(row[lc])})
    except (TypeError,ValueError) as e:raise ValueError(f"{i}行目に数値ではない値があります。") from e
  if not rows:raise ValueError("分析可能なデータがありません。")
  return rows
 def chat(self,user_message,csv_filename,conversation=None):
  rows=self.load(csv_filename)[-30:];first,last=rows[0],rows[-1];temps=[x["temperature"] for x in rows];hums=[x["humidity"] for x in rows];lights=[x["light"] for x in rows]
  history="\n".join(f"- {x['timestamp']}: 温度{x['temperature']}℃、湿度{x['humidity']}%、照度{x['light']}lux" for x in rows)
  system="あなたはCSV環境データについて継続対話するチャットボットです。温度・湿度・照度・時刻と会話履歴だけを根拠にし、未取得情報を断定せず、特定不能なら明記してください。日本語で結論から回答してください。"
  prompt=f"質問: {user_message}\n対象CSV: {csv_filename}\n最新値: {last}\n平均: 温度{mean(temps):.2f}、湿度{mean(hums):.2f}、照度{mean(lights):.2f}\n変化: 温度{last['temperature']-first['temperature']:+.2f}、湿度{last['humidity']-first['humidity']:+.2f}、照度{last['light']-first['light']:+.2f}\n履歴:\n{history}"
  messages=[{"role":"system","content":system}]
  if isinstance(conversation,list):
   for item in conversation[-10:]:
    if item.get("role") in ("user","assistant") and item.get("content"):messages.append({"role":item["role"],"content":str(item["content"])[:3000]})
  messages.append({"role":"user","content":prompt})
  try:res=requests.post(self.ollama_url,json={"model":self.model,"messages":messages,"stream":False,"options":{"temperature":0.2}},timeout=(5,180))
  except requests.ConnectionError as e:raise ConnectionError("Ollamaへ接続できません。") from e
  if not res.ok:raise RuntimeError(f"Ollama APIエラー: {res.status_code}")
  answer=str(res.json().get("message",{}).get("content","")).strip()
  if not answer:raise RuntimeError("Ollamaから回答が返りませんでした。")
  return answer
