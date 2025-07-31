from flask import Flask
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!", 200

def keep_alive():
    port = int(os.environ.get("PORT", 8080))  # Render sẽ cấp PORT đúng
    app.run(host='0.0.0.0', port=port)
