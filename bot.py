import os
import json, pathlib, threading
from flask import Flask, request
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI, OpenAIError  

# ─── Carga .env - Credenciales ────────────────────────────────────────────
load_dotenv()

#OpenAI
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

#Twilio
twilio_SID = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# ──────────────────────────────────────────────────────────────────────────

# Variables globales
MEM_FILE = pathlib.Path("memory.json")
_lock = threading.Lock()
MAX_TURNS = 10

# Funciones
def load_history(user, n=MAX_TURNS):
    """Devuelve los últimos n mensajes guardados para un usuario."""
    if not MEM_FILE.exists():
        return []
    try:
        data = json.loads(MEM_FILE.read_text())
        return data.get(user, [])[-n:]
    except json.JSONDecodeError:
        # Corrupción accidental => resetea
        return []

def append_message(user, role, content):
    """Añade un mensaje a la memoria y recorta excedentes."""
    with _lock:
        data = {}
        if MEM_FILE.exists():
            try:
                data = json.loads(MEM_FILE.read_text())
            except json.JSONDecodeError:
                pass
        data.setdefault(user, []).append({"role": role, "content": content})
        # recorta
        data[user] = data[user][-MAX_TURNS:]
        MEM_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


#Flask app
app = Flask(__name__)

#Ruta para verificar la salud del servidor
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

#Ruta para mensaje entrante
@app.route("/webhook", methods=["POST"])
def whatsapp_bot():
    user_id = request.values.get("From")
    incoming = request.values.get("Body", "").strip()
    
    # Cargar historial corto
    history = load_history(user_id)
    
    # Construir mensaje para GPT
    messages = [
        {"role": "system",
        "content": "Eres Sky, una asistente en español, clara y directa."},
        *history,
        {"role": "user", "content": incoming}
    ]
    
    # Llamar a OpenAI
    try:
        completition = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        answer = completition.choices[0].message.content
    except OpenAIError as e:
        answer = "Lo siento, hubo un problema interno"
        print("OpenAI Error:", e)
    
    # Guarda ambos mensajes en memoria
    append_message(user_id, "user", incoming)
    append_message(user_id, "assistant", answer)
    
    # Responde a twilio
    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)