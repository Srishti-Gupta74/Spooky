from google import genai
from dotenv import load_dotenv
import os
load_dotenv()
import pyautogui
import PIL.Image
import time
import pyttsx3
import speech_recognition as sr
import pytesseract
import cv2
import re
import random
import threading
import keyboard
from pathlib import Path
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import urllib.parse

# ==========================
# FIREBASE SETUP
# ==========================

RUNTIME_DIR = Path.home() / ".spooky" / "runtime"
CURRENT_VIEW_PATH = RUNTIME_DIR / "current_view.png"
TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
_keyboard_warning_shown = False


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def ensure_runtime_ready():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not TESSERACT_PATH.exists():
        raise RuntimeError(
            f"Tesseract not found at {TESSERACT_PATH}. Install it or update the configured path."
        )


def build_firestore_client():
    credentials_path = Path(require_env("FIREBASE_CREDENTIALS_PATH")).expanduser()
    if not credentials_path.exists():
        raise RuntimeError(f"Firebase credentials file not found: {credentials_path}")

    cred = credentials.Certificate(str(credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


def build_gemini_client():
    return genai.Client(
        api_key=require_env("GEMINI_API_KEY"),
        http_options={'api_version': 'v1'}
    )


ensure_runtime_ready()
db = build_firestore_client()
client = build_gemini_client()

# ==========================
# TESSERACT PATH
# ==========================

pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)

# ==========================
# VOICE ENGINE (interruptible with SPACE)
# ==========================

_tts_engine = None
_tts_lock = threading.Lock()
_tts_interrupted = False


def _on_word(name, location, length):
    global _tts_interrupted, _tts_engine
    if _tts_interrupted:
        if _tts_engine:
            _tts_engine.stop()


def is_space_pressed():
    global _keyboard_warning_shown
    try:
        return keyboard.is_pressed('space')
    except Exception as error:
        if not _keyboard_warning_shown:
            print(f"Keyboard hook unavailable: {error}")
            _keyboard_warning_shown = True
        return False


def speak(text):
    global _tts_engine, _tts_interrupted

    _tts_interrupted = False
    spoken_complete = threading.Event()

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
            time.sleep(0.18)
        print(flush=True)

    def _speak_thread():
        global _tts_engine
        try:
            with _tts_lock:
                _tts_engine = pyttsx3.init('sapi5')
                _tts_engine.setProperty('rate', 160)
                _tts_engine.setProperty('volume', 1.0)
                voices = _tts_engine.getProperty('voices')
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

    print_thread = threading.Thread(target=_print_thread, daemon=True)
    tts_thread = threading.Thread(target=_speak_thread, daemon=True)
    print_thread.start()
    tts_thread.start()

    while not spoken_complete.is_set():
        if is_space_pressed():
            _tts_interrupted = True
            print("\n⏹️ Speech interrupted!")
            with _tts_lock:
                if _tts_engine:
                    try:
                        _tts_engine.stop()
                    except Exception:
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
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=20)
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
# OCR CHECK — 3 LAYERS
# ==========================

# Tier 1: Single match triggers Gemini
KEYWORDS_TIER1 = [
    "urgent", "verify", "account", "locked", "suspended",
    "login", "bank", "password", "confirm", "alert",
    "security", "unauthorized", "breach", "compromised",
    "credential", "authenticate", "sign-in", "signin",
]

# Tier 2: Need 2+ matches to trigger Gemini
KEYWORDS_TIER2 = [
    "free", "winner", "won", "prize", "chosen", "selected",
    "congratulations", "claim", "reward", "gift", "bonus",
    "limited", "offer", "exclusive", "loyalty", "survey",
    "earn", "redeem", "act now", "expires", "guaranteed",
    "risk-free", "click here", "get started", "collect",
    "you have been", "special", "approved", "eligible",
]

# Suspicious URL patterns
SUSPICIOUS_URL_PATTERNS = [
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',        # IP as URL
    r'secure.*login', r'login.*secure',
    r'verify.*account', r'account.*verify',
    r'update.*payment', r'payment.*update',
    r'[a-z]+-[a-z]+-\d+\.com',                      # fake domains e.g. secure-login-382.com
    r'[a-z]+\.(xyz|tk|ml|ga|cf|gq|top|click|online)', # suspicious TLDs
]


def quick_ocr_check(image_path):
    """
    3-layer OCR pre-filter:
    Layer 1 — Tier 1 high-confidence keywords (single match triggers)
    Layer 2 — Tier 2 scam keywords (2+ matches trigger)
    Layer 3 — Suspicious URL patterns in visible text
    Returns: (triggered: bool, reason: str)
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"Unable to read screenshot: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray).lower()

    # Layer 1
    for k in KEYWORDS_TIER1:
        if k in text:
            return True, f"keyword: '{k}'"

    # Layer 2
    tier2_matches = [k for k in KEYWORDS_TIER2 if k in text]
    if len(tier2_matches) >= 2:
        return True, f"scam keywords: {tier2_matches[:3]}"

    # Layer 3
    for pattern in SUSPICIOUS_URL_PATTERNS:
        if re.search(pattern, text):
            return True, "suspicious URL pattern in text"

    return False, ""


# ==========================
# URL EXTRACTOR + CHECKER
# ==========================

def extract_visible_urls(image_path):
    """Extract URLs and domains visible in the screenshot via OCR."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"Unable to read screenshot: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text, re.IGNORECASE)
    domains = re.findall(
        r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|edu|gov|io|app|web|xyz|tk|ml|top|click|online|info|biz)\b',
        text, re.IGNORECASE
    )
    return list(set(urls + domains))


def is_suspicious_url(url):
    """Check URL for suspicious signals without any external API."""
    url_lower = url.lower()
    signals = []

    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url_lower):
        signals.append("IP address URL")

    if re.search(r'\.(xyz|tk|ml|ga|cf|gq|top|click|online)($|/)', url_lower):
        signals.append("suspicious TLD")

    lookalikes = [
        'paypa1', 'g00gle', 'micosoft', 'arnazon', 'faceb00k',
        'app1e', 'netfl1x', 'secure-login', 'verify-account',
        'update-payment', 'account-suspended'
    ]
    for fake in lookalikes:
        if fake in url_lower:
            signals.append(f"lookalike: {fake}")

    try:
        domain = urllib.parse.urlparse(url).netloc
        if domain.count('.') >= 3:
            signals.append("excessive subdomains")
    except ValueError:
        pass

    if re.search(r'(paypal|google|apple|amazon|microsoft|netflix|bank)\d', url_lower):
        signals.append("brand name with numbers")

    return signals


# ==========================
# VISUAL ALERT
# ==========================

def highlight_threat(image_path):
    def _show_alert():
        img = cv2.imread(str(image_path))
        if img is None:
            raise RuntimeError(f"Unable to read screenshot: {image_path}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

        all_keywords = KEYWORDS_TIER1 + KEYWORDS_TIER2
        for i, word in enumerate(data["text"]):
            t = re.sub(r'[^a-zA-Z]', '', str(word)).lower()
            if any(k in t for k in all_keywords):
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)

        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), -1)
        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
        cv2.putText(img, "POSSIBLE PHISHING DETECTED", (60, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        cv2.putText(img, "Do not enter your credentials", (60, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

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
# GEMINI ANALYSIS FUNCTIONS
# ==========================

def gemini_analyze(image_path, url_context=""):
    url_hint = f"\nURLs detected on screen: {url_context}" if url_context else ""
    prompt = f"""
You are Spooky, an expert cybersecurity AI guardian.

Analyze this screenshot for ANY of these threats:
1. Phishing — fake login pages, credential harvesting forms
2. Scams — fake prizes, lottery wins, fake giveaways, fake brand loyalty programs
3. Social engineering — urgency tactics, fear tactics, too-good-to-be-true offers
4. Brand impersonation — fake Google, Apple, Microsoft, bank, PayPal pages
5. Malicious popups or browser hijacking
6. Suspicious forms asking for personal or financial info
{url_hint}

IGNORE: VS Code, terminals, code editors, IDEs, file explorers, programming windows.
FOCUS ON: Browser pages, popups, emails, messages, web content.

Also analyze VISUAL elements:
- Fake or misused brand logos
- Red/orange urgency call-to-action buttons
- Prize imagery combined with brand logos
- Countdown timers
- Forms requesting sensitive information

Respond with ONLY:
- The single word: Clear  (if nothing suspicious)
- A 1-2 sentence threat warning (if anything suspicious found)

Be aggressive — a false positive is safer than a missed threat.
"""
    with PIL.Image.open(image_path) as img:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt, img]
        )
    return (response.text or "").strip()


def gemini_explain(image_path):
    with PIL.Image.open(image_path) as img:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                "In one clear sentence, explain why this screen is dangerous and what the attacker is trying to steal or achieve.",
                img
            ]
        )
    return (response.text or "").strip()


def gemini_chat(image_path, user_question):
    with PIL.Image.open(image_path) as img:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                f"""You are Spooky, a cybersecurity AI assistant.
The user is viewing a suspicious page and asked: "{user_question}"
Answer in 2 sentences max. Be clear, direct and helpful.""",
                img
            ]
        )
    return (response.text or "").strip()


def get_system_active():
    try:
        status = db.collection("system").document("status").get()
        return status.to_dict().get("active", True) if status.exists else True
    except Exception as error:
        print(f"Firestore status check failed: {error}")
        return True


def save_current_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot.save(CURRENT_VIEW_PATH)
    screenshot.close()
    return CURRENT_VIEW_PATH


# ==========================
# STARTUP
# ==========================

print("\n👁️ Spooky is online! (Press Ctrl+C to stop)")
print("💡 Press SPACE at any time to interrupt Spooky's speech.")
print("🛡️ Active: 3-layer OCR filter + URL analysis + Gemini vision\n")

last_threat = False

# ==========================
# MAIN LOOP
# ==========================

try:
    check_count = 0

    while True:

        # Remote kill switch
        active = get_system_active()

        if not active:
            print("😴 Spooky is sleeping (website control)")
            time.sleep(5)
            continue

        check_count += 1

        # Screenshot
        current_view = save_current_screenshot()

        # Layer 1+2+3: OCR pre-check
        suspicious, ocr_reason = quick_ocr_check(current_view)

        # Periodic forced deep scan every 5 checks (catches visual-only scams)
        force_deep_scan = (check_count % 5 == 0)

        if not suspicious and not force_deep_scan:
            print(f"\nCheck {check_count}: Screen looks safe (OCR)")
            time.sleep(60)
            continue

        if force_deep_scan and not suspicious:
            print(f"\nCheck {check_count}: 🔍 Periodic deep scan...")
        else:
            print(f"\nCheck {check_count}: ⚠ OCR triggered ({ocr_reason}) → Gemini...")

        # URL analysis
        urls = extract_visible_urls(current_view)
        url_warnings = []
        for url in urls[:5]:
            signals = is_suspicious_url(url)
            if signals:
                url_warnings.append(f"{url}: {', '.join(signals)}")
                print(f"🔗 Suspicious URL: {url} → {signals}")

        url_context = "; ".join(url_warnings)

        # Gemini deep analysis
        try:
            analysis = gemini_analyze(current_view, url_context)
        except Exception as e:
            print(f"Gemini error: {e}")
            time.sleep(60)
            continue

        print(f"\nGemini: {analysis}")

        # URL override: if URL analysis flagged something, don't let Gemini clear it
        if url_warnings and "Clear" in analysis:
            analysis = f"Suspicious URLs detected on screen: {url_context}"
            print("⚠ URL analysis override: flagging despite Gemini Clear")

        if "Clear" not in analysis and not last_threat:

            highlight_threat(current_view)
            time.sleep(1)
            speak("Warning. Potential threat detected on your screen.")

            spoken_explanation = "Explanation unavailable"
            try:
                spoken_explanation = gemini_explain(current_view)
                speak(spoken_explanation)
            except Exception as e:
                print("Explanation error:", e)

            speak("Would you like to ask me something, or should I resume monitoring?")

            # Log to Firestore with richer data
            db.collection("threat_logs").add({
                "timestamp": datetime.utcnow(),
                "type": "phishing",
                "analysis": analysis,
                "explanation": spoken_explanation,
                "ocr_trigger": ocr_reason,
                "suspicious_urls": url_warnings,
                "location": random.choice([
                    "USA", "India", "China", "Russia",
                    "Germany", "Brazil", "UK", "Singapore"
                ])
            })

            # Voice Q&A
            while True:
                user_input = listen_to_user()

                if not user_input:
                    speak("Please ask your question, or say resume.")
                    continue

                if "resume" in user_input.lower():
                    speak("Okay. Resuming monitoring.")
                    break

                try:
                    answer = gemini_chat(current_view, user_input)
                    speak(answer)
                    speak("Ask another question, or say resume.")
                except Exception as e:
                    print(f"Chat error: {e}")
                    speak("The AI server is busy. Please try again.")

            print("\n🛡️ Threat consultation complete.")
            last_threat = True

        else:
            print("\n--- System Secure ---")
            last_threat = False

        # Wait with kill switch check each second
        for _ in range(60):
            active = get_system_active()
            if not active:
                print("😴 Spooky stopped by dashboard")
                break
            time.sleep(1)

except KeyboardInterrupt:
    print("\n👻 Spooky is going back to sleep.")
finally:
    try:
        CURRENT_VIEW_PATH.unlink(missing_ok=True)
    except OSError:
        pass
