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
# TEXT TO SPEECH (EDGE-TTS)
# -------------------------------------------------------------------
async def speak_async(text):

    # FEMALE VOICE — Sobhana Neural
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
    os.remove("speak.mp3")

def speak(text):
    asyncio.run(speak_async(text))

# -------------------------------------------------------------------
# GUI + ASSISTANT
# -------------------------------------------------------------------
class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Malayalam Voice Assistant")
        self.root.geometry("500x500")
        self.root.configure(bg="#00111a")

        self.canvas = tk.Canvas(root, bg="#00111a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.text_console = tk.Label(root,
                                     text="🪔 Malayalam Assistant Starting...",
                                     fg="#00ffff", bg="#00111a",
                                     font=("Consolas", 12))
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
            self.canvas.create_oval(cx - radius, cy - radius,
                                    cx + radius, cy + radius,
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

        # Wake word message
        self.update_console("Wake Word കേൾക്കുന്നു: 'ഹായ് അസിസ്റ്റന്റ്' 🔊")

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
                speak("""
നമസ്കാരം മാഷേ! ഞാൻ നിങ്ങളുടെ സ്വന്തം മലയാളം വോയ്‌സ് അസിസ്റ്റന്റാണ്.
എന്ത് സഹായം വേണം എന്നു പറയും, ഞാൻ നോക്കാം ചെയ്യാൻ.
""")
                self.update_console("Assistant Ready 🟢")
                continue

            # ----------------------------------------
            # COMMANDS
            # ----------------------------------------

            # LIGHT ON
            if "ലൈറ്റ് ഓൺ" in text:
                speak("ശരി മാഷേ, ലൈറ്റ് ഓൺ ആക്കിയിട്ടുണ്ട്.")
                send_to_esp("light_on")

            # LIGHT OFF
            elif "ലൈറ്റ് ഓഫ്" in text:
                speak("ലൈറ്റ് ഓഫ് ആക്കിയിട്ടുണ്ട് മാഷേ.")
                send_to_esp("light_off")

            # EXIT
            elif "നിർത്തൂ" in text or "വിട" in text:
                speak("ശരി മാഷേ, ഞാൻ പോകുന്നു. ദിവസം നല്ലതാവട്ടെ. പിന്നെ കാണാം.")
                self.update_console("Session Ended")
                break

            else:
                # UNKNOWN COMMAND
                speak("എനിക്ക് ശരിയായി പിടികിട്ടിയില്ല മാഷേ… ഒന്നു വീണ്ടും പറയും?")
                continue


# -------------------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisGUI(root)
    root.mainloop()
