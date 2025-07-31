from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run():
    app.run(host="0.0.0.0", port=8080)  # Mở port public

def keep_alive():
    t = Thread(target=run)
    t.start()
