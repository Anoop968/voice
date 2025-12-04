import tkinter as tk
import math
import threading
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
        print("⚠️ Could not reach ESP")

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
# TEXT TO SPEECH (EDGE-TTS)
# -------------------------------------------------------------------
async def speak_async(text):
    voice = "ml-IN-MidhunNeural"

    tts = edge_tts.Communicate(text, voice)
    await tts.save("speak.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("speak.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

    pygame.mixer.music.unload()
    pygame.mixer.quit()
    os.remove("speak.mp3")


def speak(text):
    asyncio.run(speak_async(text))

# -------------------------------------------------------------------
# GUI + ASSISTANT
# -------------------------------------------------------------------
class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("500x500")
        self.root.configure(bg="#00111a")

        self.canvas = tk.Canvas(root, bg="#00111a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.text_console = tk.Label(root, text="...",
                                     fg="#00ffff", bg="#00111a", font=("Consolas", 12))
        self.text_console.pack(side="bottom", pady=10)

        self.angle = 0
        self.animate_circles()

        threading.Thread(target=self.assistant_loop, daemon=True).start()

    # ----------------------------------------
    # ANIMATION
    # ----------------------------------------
    def animate_circles(self):
        self.canvas.delete("all")
        cx, cy = 250, 220

        for i in range(5):
            radius = 60 + i * 20 + 5 * math.sin(self.angle + i)
            green = int(150 + 50 * math.sin(self.angle + i))
            color = f"#00{green:02x}ff"
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                    outline=color, width=2)

        self.angle += 0.1
        self.root.after(50, self.animate_circles)

    # ----------------------------------------
    # UPDATE CONSOLE TEXT
    # ----------------------------------------
    def update_console(self, text):
        self.text_console.config(text=text)

    # ----------------------------------------
    # ASSISTANT LOOP
    # ----------------------------------------
    def assistant_loop(self):
        self.update_console("Listening for Wake Word: 'ഹായ് അസിസ്റ്റന്റ്' 🔊")

        while True:
            wav_path = listen_filtered()
            text = recognize_speech(wav_path)
            os.remove(wav_path)

            if not text:
                continue

            print("You said:", text)
            self.update_console("You said: " + text)

            # ----------------------------------------
            # WAKE WORD DETECTION
            # ----------------------------------------
            WAKE_WORDS = ["ഹായ്", "അസിസ്റ്റന്റ്", "പോൾ", "സഹായി"]

            if any(word in text for word in WAKE_WORDS):
                speak("""നമസ്കാരം.  
ഈ AI അസിസ്റ്റന്റ് ഇപ്പോൾ പ്രവർത്തന സജ്ജമാണ്.  
വിവരങ്ങൾ അന്വേഷിക്കൽ, ഓൺലൈൻ സേവനങ്ങൾ കൈകാര്യം ചെയ്യൽ, നിങ്ങളുടെ ദിനചര്യ ജോലികൾ ലളിതമാക്കൽ തുടങ്ങിയവയ്ക്ക് ഞാൻ സഹായിക്കും.  
ദയവായി നിങ്ങളുടെ നിർദേശം നൽകുക.""")
                self.update_console("Assistant Ready 🟢")

            # ----------------------------------------
            # COMMANDS
            # ----------------------------------------
            if "ലൈറ്റ് ഓൺ" in text:
                speak("ലൈറ്റ് ഓൺ ആക്കി.")
                send_to_esp("light_on")

            elif "ലൈറ്റ് ഓഫ്" in text:
                speak("ലൈറ്റ് ഓഫ് ആക്കി.")
                send_to_esp("light_off")

            elif "നിർത്തൂ" in text or "വിട" in text:
                speak("വിട. നല്ല ദിവസം!")
                self.update_console("Session Ended")
                break


# -------------------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisGUI(root)
    root.mainloop()
