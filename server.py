from flask import Flask, request, jsonify
import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy.signal import butter, lfilter
import speech_recognition as sr
import pygame
import asyncio
import time
import os
import edge_tts
import requests
from flask_cors import CORS

# -------------------------------------------------------------------
# ESP CONFIG
# -------------------------------------------------------------------
ESP_IP = "10.67.75.7"

def send_to_esp(command):
    try:
        url = f"http://{ESP_IP}/command?msg={command}"
        requests.get(url, timeout=1)
        print("Sent:", command)
    except:
        print("⚠️ ESP ഉപകരണവുമായി ബന്ധപ്പെടാൻ കഴിഞ്ഞില്ല")

# -------------------------------------------------------------------
# AUDIO FILTERS
# -------------------------------------------------------------------
LOWCUT = 300
HIGHCUT = 3400
FS = 16000
ORDER = 5
DURATION = 4

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass(data):
    b, a = butter_bandpass(LOWCUT, HIGHCUT, FS, ORDER)
    return lfilter(b, a, data)

# -------------------------------------------------------------------
# RECORD AUDIO + FILTER
# -------------------------------------------------------------------
def listen_filtered():
    audio = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype='float32')
    sd.wait()
    filtered = apply_bandpass(audio.flatten())
    sf.write("filtered.wav", filtered, FS)
    return "filtered.wav"

# -------------------------------------------------------------------
# SPEECH TO TEXT
# -------------------------------------------------------------------
def recognize_speech(path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data, language="ml-IN")
    except:
        return ""

# -------------------------------------------------------------------
# TEXT TO SPEECH
# -------------------------------------------------------------------
async def speak_async(text):

    voice = "ml-IN-SobhanaNeural"

    tts = edge_tts.Communicate(text, voice)
    await tts.save("speak.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("speak.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

    pygame.mixer.music.unload()
    pygame.mixer.quit()

def speak(text):
    asyncio.run(speak_async(text))

# -------------------------------------------------------------------
# FLASK WEB SERVER
# -------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({"status": "Malayalam Voice Assistant API Running"})


@app.route("/speak")
def api_speak():
    text = request.args.get("text", "")
    speak(text)
    return jsonify({"spoken": text})


@app.route("/command")
def api_command():
    text = request.args.get("text", "")

    if "ലൈറ്റ് ഓൺ" in text:
        speak("ശരി സാർ, ലൈറ്റ് ഓൺ ആക്കിയിട്ടുണ്ട്.")
        send_to_esp("light_on")

    elif "ലൈറ്റ് ഓഫ്" in text:
        speak("ലൈറ്റ് ഓഫ് ആക്കിയിട്ടുണ്ട് സാർ.")
        send_to_esp("light_off")

    elif "നിർത്തൂ" in text or "വിട" in text:
        speak("ശരി സാർ, ഞാൻ പോകുന്നു.")
    else:
        speak("എനിക്ക് ശരിയായി പിടികിട്ടിയില്ല സാർ.")

    return jsonify({"command": text})


@app.route("/listen")
def api_listen():
    path = listen_filtered()
    text = recognize_speech(path)
    return jsonify({"text": text})


@app.route("/wake")
def api_wake():
    speak("""
നമസ്കാരം.  
ഈ AI അസിസ്റ്റന്റ് ഇപ്പോൾ പ്രവർത്തന സജ്ജമാണ്.  
വിവരങ്ങൾ അന്വേഷിക്കൽ, ഓൺലൈൻ സേവനങ്ങൾ കൈകാര്യം ചെയ്യൽ, നിങ്ങളുടെ ദിനചര്യ ജോലികൾ ലളിതമാക്കൽ തുടങ്ങിയവയ്ക്ക് ഞാൻ സഹായിക്കും.  
ദയവായി നിങ്ങളുടെ നിർദേശം നൽകുക.
""")
    return jsonify({"status": "Wake response sent"})


# Run Flask Server
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
