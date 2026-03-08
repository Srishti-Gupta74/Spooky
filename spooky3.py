from google import genai
import pyautogui
import PIL.Image
import time
import pyttsx3
import speech_recognition as sr
import pytesseract
import cv2
import numpy as np
import re
import random
import threading
import keyboard
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================
# FIREBASE SETUP
# ==========================

cred = credentials.Certificate("spooky-2514e-firebase-adminsdk-fbsvc-c0a13d7787.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================
# TESSERACT PATH
# ==========================

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ==========================
# VOICE ENGINE (interruptible with SPACE)
# ==========================

_tts_engine = None
_tts_lock = threading.Lock()
_tts_interrupted = False


def _on_word(name, location, length):
    """Callback fired on each word — checks if interrupted."""
    global _tts_interrupted, _tts_engine
    if _tts_interrupted:
        if _tts_engine:
            _tts_engine.stop()


def speak(text):
    """Speak text and print simultaneously — press SPACE to interrupt."""
    global _tts_engine, _tts_interrupted

    _tts_interrupted = False
    spoken_complete = threading.Event()

    # Print text simultaneously in a separate thread
    def _print_thread():
        print("\n🔊 Spooky: ", end='', flush=True)
        words = text.split()
        for i, word in enumerate(words):
            if _tts_interrupted:
                print("...", flush=True)
                return
            print(word, end='', flush=True)
            if i < len(words) - 1:
                print(' ', end='', flush=True)
            # Pace the text output to roughly match speech
            time.sleep(0.18)
        print(flush=True)

    def _speak_thread():
        global _tts_engine
        try:
            with _tts_lock:
                _tts_engine = pyttsx3.init('sapi5')

                # More natural voice settings
                _tts_engine.setProperty('rate', 160)
                _tts_engine.setProperty('volume', 1.0)

                voices = _tts_engine.getProperty('voices')

                # Try to find a more natural voice
                # Prefer Microsoft Zira (female) or David (male)
                selected_voice = None
                for v in voices:
                    if 'zira' in v.name.lower():
                        selected_voice = v.id
                        break
                if not selected_voice:
                    for v in voices:
                        if 'david' in v.name.lower():
                            selected_voice = v.id
                            break
                if not selected_voice:
                    selected_voice = voices[1].id if len(voices) > 1 else voices[0].id

                _tts_engine.setProperty('voice', selected_voice)
                _tts_engine.connect('started-word', _on_word)
                _tts_engine.say(text)
                _tts_engine.runAndWait()
                _tts_engine.stop()
                _tts_engine = None
        except Exception as e:
            print(f"\nTTS Error: {e}")
            _tts_engine = None
        finally:
            spoken_complete.set()

    # Start both threads at the same time
    print_thread = threading.Thread(target=_print_thread, daemon=True)
    tts_thread = threading.Thread(target=_speak_thread, daemon=True)

    print_thread.start()
    tts_thread.start()

    # Poll for Space key press while TTS is running
    while not spoken_complete.is_set():
        if keyboard.is_pressed('space'):
            _tts_interrupted = True
            print("\n⏹️ Speech interrupted!")
            with _tts_lock:
                if _tts_engine:
                    try:
                        _tts_engine.stop()
                    except:
                        pass
            break
        spoken_complete.wait(timeout=0.05)

    tts_thread.join(timeout=2)
    print_thread.join(timeout=2)
    time.sleep(0.3)

    return not _tts_interrupted

# ==========================
# SPEECH RECOGNITION
# ==========================

recognizer = sr.Recognizer()

def listen_to_user():

    try:

        print("\n🎤 Listening for your question...")

        with sr.Microphone() as source:

            recognizer.adjust_for_ambient_noise(source, duration=1)

            audio = recognizer.listen(
                source,
                timeout=15,
                phrase_time_limit=20
            )

        text = recognizer.recognize_google(audio)

        print("User said:", text)

        return text

    except sr.WaitTimeoutError:
        print("No speech detected.")
        return None

    except sr.UnknownValueError:
        speak("Sorry, I didn't understand that.")
        return None

    except Exception as e:
        print("Speech error:", e)
        return None

# ==========================
# QUICK OCR CHECK
# ==========================

def quick_ocr_check(image_path):

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(gray).lower()

    keywords = [
        "urgent","verify","account","locked",
        "login","bank","click","suspended",
        "security","password","confirm","alert"
    ]

    for k in keywords:
        if k in text:
            return True

    return False

# ==========================
# VISUAL ALERT - runs in a separate thread
# ==========================

def highlight_threat(image_path):
    """Show the threat highlight in a separate thread so it doesn't block TTS."""
    def _show_alert():
        img = cv2.imread(image_path)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

        data = pytesseract.image_to_data(
            gray,
            output_type=pytesseract.Output.DICT
        )

        keywords = [
            "urgent","verify","account","locked",
            "login","bank","click","suspended",
            "security","password","confirm","alert"
        ]

        for i, word in enumerate(data["text"]):

            text = re.sub(r'[^a-zA-Z]', '', str(word)).lower()

            if any(k in text for k in keywords):

                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                cv2.rectangle(img,(x,y),(x+w,y+h),(0,0,255),3)

        overlay = img.copy()

        cv2.rectangle(
            overlay,
            (0,0),
            (img.shape[1], img.shape[0]),
            (0,0,255),
            -1
        )

        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)

        cv2.putText(
            img,
            "POSSIBLE PHISHING DETECTED",
            (60,120),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255,255,255),
            4
        )

        cv2.putText(
            img,
            "Do not enter your credentials",
            (60,200),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255,255,255),
            3
        )

        window = "Spooky Security Alert"

        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

        cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(window, cv2.WND_PROP_TOPMOST, 1)

        cv2.imshow(window, img)

        cv2.waitKey(5000)

        cv2.destroyAllWindows()
        cv2.waitKey(1)

    alert_thread = threading.Thread(target=_show_alert, daemon=True)
    alert_thread.start()
    alert_thread.join()
    time.sleep(0.5)

# ==========================
# GEMINI CLIENT
# ==========================

client = genai.Client(
    api_key="AIzaSyBWsL5bhJ8dzsQamw1_m7JTXwsWPO5cJgk",
    http_options={'api_version': 'v1'}
)

print("\n👁️ Spooky is online! (Press Ctrl+C to stop)")
print("💡 Press SPACE at any time to interrupt Spooky's speech.")

last_threat = False

# ==========================
# MAIN LOOP
# ==========================

try:

    check_count = 0

    while True:

        check_count += 1

        screenshot = pyautogui.screenshot()
        screenshot.save("current_view.png")
        screenshot.close()

        suspicious = quick_ocr_check("current_view.png")

        if not suspicious:

            print(f"\nCheck {check_count}: Screen looks safe (OCR)")
            time.sleep(60)
            continue

        print("\n⚠ Suspicious text detected. Sending to Gemini...")

        img = PIL.Image.open("current_view.png")

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                """
You are Spooky, a cybersecurity guardian.

Ignore VS Code, terminals, and programming windows.

Focus ONLY on browser pages.

If safe respond exactly:
Clear

If phishing detected respond with a short warning.
""",
                img
            ]
        )

        analysis = response.text.strip()

        img.close()

        print(f"\nCheck {check_count}: {analysis}")

        if "Clear" not in analysis and not last_threat:

            highlight_threat("current_view.png")

            time.sleep(1)

            speak("Warning. Potential phishing detected.")

            spoken_explanation = "Explanation unavailable"

            try:

                img = PIL.Image.open("current_view.png").copy()

                explanation_response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=[
                        "Explain why this screen contains a phishing attempt in one short sentence.",
                        img
                    ]
                )

                spoken_explanation = explanation_response.text.strip()

                speak(spoken_explanation)

            except Exception as e:
                print("Explanation error:", e)

            speak("Would you like to ask something else, or should I resume monitoring?")

            db.collection("threat_logs").add({
                "timestamp": datetime.utcnow(),
                "type": "phishing",
                "analysis": analysis,
                "explanation": spoken_explanation,
                "location": random.choice([
                    "USA","India","China","Russia",
                    "Germany","Brazil","UK","Singapore"
                ])
            })

            # ==========================
            # CONVERSATION LOOP
            # ==========================

            while True:

                user_input = listen_to_user()

                if not user_input:

                    speak("Please ask your question again, or say resume.")
                    continue

                if "resume" in user_input.lower():

                    speak("Okay. I will resume monitoring.")
                    break

                try:

                    img = PIL.Image.open("current_view.png").copy()

                    chat_response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=[
                            f"""
User asked: {user_input}

Explain why the detected content may be dangerous.
Limit to 2 sentences.
""",
                            img
                        ]
                    )

                    answer = chat_response.text.strip()

                    speak(answer)

                    speak("Ask another question, or say resume.")

                except Exception as e:

                    print(f"Chat error: {e}")

                    speak("The AI server is busy. Please try again later.")

            print("\n🛡️ Threat consultation complete.")

            last_threat = True

        else:

            print("\n--- System Secure ---")
            last_threat = False

        time.sleep(60)

except KeyboardInterrupt:

    print("\n👻 Spooky is going back to sleep.")
