from pathlib import Path
from flask import Flask,jsonify,request
from flask_cors import CORS
from chatbot import TemperatureChatBot
app=Flask(__name__)
CORS(app,resources={r"/*":{"origins":["http://127.0.0.1:5001","http://localhost:5001"]}})
BASE_DIR=Path(__file__).resolve().parent
DATA_DIR=BASE_DIR/"data"
bot=TemperatureChatBot(DATA_DIR)
def files():return sorted([p.name for p in DATA_DIR.glob("data-*.csv")],reverse=True)
def choose(name=None):
 f=files();return name if name in f else (f[0] if f else None)
@app.get("/health")
def health():return jsonify({"status":"ok"})
@app.post("/chat")
def chat():
 d=request.get_json(silent=True) or {};q=str(d.get("message","")).strip();fn=choose(d.get("file"))
 if not q:return jsonify({"response":"質問を入力してください。"}),400
 if not fn:return jsonify({"response":"dataフォルダにdata-*.csvを配置してください。"}),404
 try:return jsonify({"response":bot.chat(q,fn,d.get("conversation",[])),"selected_file":fn})
 except ConnectionError:return jsonify({"response":"Ollamaへ接続できません。"}),503
 except (ValueError,FileNotFoundError,RuntimeError) as e:return jsonify({"response":str(e)}),400
if __name__=="__main__":
 DATA_DIR.mkdir(exist_ok=True);app.run(debug=True,host="0.0.0.0",port=5002)
