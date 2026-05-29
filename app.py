import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from bot import lookup_phone

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-this-in-production")
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lookup', methods=['POST'])
def lookup():
    phone = request.form.get('phone', '').strip()
    if not phone:
        return jsonify({"error": "Phone number is required"}), 400
    
    result = lookup_phone(phone)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
