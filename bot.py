import os
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

#Flask app
app = Flask(__name__)

#Ruta para verificar la salud del servidor
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

#Ruta para mensaje entrante
@app.route("/webhook", methods=["POST"])
def whatsapp_echo():
    incoming = request.values.get("Body", "").strip()
    
    resp = MessagingResponse()
    reply = resp.message()
    
    try:
        completition = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                "content": "Eres Sky, una asistente en español, clara y directa."},
                {"role": "user", "content": incoming}
            ]
        )
        reply.body(completition.choices[0].message.content)
        return str(resp)
    except OpenAIError as e:
        print("OpenAI ERROR:", e)
        reply.body("Lo siento, ocurrió un problema interno")
        return str(resp)
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)