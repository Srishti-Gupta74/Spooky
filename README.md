# 👻 Spooky — Real-Time Phishing Detection Agent

> Built for the **Gemini Live Agent Challenge** on Devpost  
> A multimodal AI cybersecurity guardian that watches your screen and warns you about phishing in real time.

---

## 🧠 What It Does

Spooky is an always-on AI agent that:
- 📸 **Takes periodic screenshots** of your screen
- 🔍 **Runs OCR** to quickly detect suspicious keywords (urgent, verify, bank, password, etc.)
- 🤖 **Sends suspicious screens to Gemini** for deep visual analysis
- 🚨 **Triggers a fullscreen red alert overlay** if phishing is detected
- 🔊 **Speaks a warning aloud** and explains the threat
- 🎤 **Opens a voice Q&A session** — ask Spooky anything about the threat
- 📊 **Logs all threats to Firebase Firestore** with timestamp and analysis
- 🌐 **Remotely controllable** via a Firebase-hosted web dashboard (start/stop Spooky)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Vision & Analysis | Google Gemini API (`gemini-2.5-flash-lite`) |
| Screen Capture | PyAutoGUI |
| OCR | Tesseract + OpenCV |
| Text-to-Speech | pyttsx3 (Windows SAPI5) |
| Speech Recognition | Google Speech Recognition |
| Database | Firebase Firestore |
| Dashboard | Firebase Hosting |
| Key Management | python-dotenv |

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10+
- Windows OS (for SAPI5 TTS)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed at `C:\Program Files\Tesseract-OCR\`
- A Google Gemini API key ([get one here](https://aistudio.google.com))
- A Firebase project with Firestore enabled

### 1. Clone the repo
```bash
git clone https://github.com/Srishti-Gupta74/Spooky.git
cd Spooky
```

### 2. Install dependencies
```bash
pip install google-genai pyautogui pillow pyttsx3 speechrecognition pytesseract opencv-python numpy keyboard firebase-admin python-dotenv
```

### 3. Set up environment variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
FIREBASE_CREDENTIALS_PATH=C:\\Users\\your-user\\.spooky\\firebase-adminsdk.json
```

### 4. Add your Firebase Admin SDK credentials
- Go to Firebase Console → Project Settings → Service Accounts
- Click **Generate new private key**
- Store the downloaded `.json` file outside the repository folder
- Set `FIREBASE_CREDENTIALS_PATH` in your `.env` to its full local path

### 5. Set up Firestore
In your Firebase project, create these Firestore documents:
- Collection: `system` → Document: `status` → Field: `active` (boolean, default: `true`)

### 6. Run Spooky
```bash
python spooky2.py
```

---

## 🎮 Controls

| Action | How |
|--------|-----|
| Stop speech | Press `SPACE` |
| Stop Spooky | Press `Ctrl+C` |
| Resume monitoring | Say **"resume"** during voice Q&A |
| Remote stop/start | Use the web dashboard |

---

## 🌐 Web Dashboard

The `public/` folder contains a Firebase-hosted dashboard where you can:
- Toggle Spooky on/off remotely
- View live threat logs
- See threat statistics and charts

Deploy it with:
```bash
firebase deploy
```

The deployed dashboard entrypoint is `public/index.html`. The old `spooky2.html` debug prototype is not part of the app.

---

## 📁 Project Structure

```
Spooky/
├── spooky2.py          # Main agent (run this)
├── firebase.json       # Firebase Hosting config
├── public/
│   ├── index.html      # Web dashboard
│   └── 404.html
├── .env                # Your secrets (never committed)
├── .env.example        # Template for local environment setup
├── .gitignore
├── .firebaserc
└── README.md
```

---

## 🧪 Reproducible Testing

Follow these steps to verify Spooky works end-to-end on your machine.

### Quick smoke test (no phishing page needed)

1. Complete the [Setup Instructions](#️-setup-instructions) above.
2. Run Spooky:
   ```bash
   python spooky2.py
   ```
3. You should see:
   ```
   👁️ Spooky is online! (Press Ctrl+C to stop)
   💡 Press SPACE at any time to interrupt Spooky's speech.
   🛡️ Active: 3-layer OCR filter + URL analysis + Gemini vision
   ```
4. After ~60 seconds Spooky prints `Check 1: Screen looks safe (OCR)` — confirming the screen-capture → OCR pipeline works.
5. Every 5 checks it runs a forced Gemini deep scan. You will see `🔍 Periodic deep scan...` printed, confirming the Gemini API connection works.

### Trigger a phishing alert manually

1. Open this test phishing-simulation page in your browser (safe, for testing):  
   `https://www.phishtank.com` or simply open a webpage containing the word **"verify your account"**.
2. Leave it visible on screen. Spooky's OCR will detect the keyword and send the screenshot to Gemini within the next scan cycle.
3. Expected output:
   - A red fullscreen alert overlay appears.
   - Spooky speaks a warning aloud.
   - The threat is logged in Firestore under `threat_logs`.
   - The web dashboard shows the new log entry.

### Verify Firebase logging

1. Open [Firebase Console](https://console.firebase.google.com) → your project → Firestore.
2. Navigate to `threat_logs` — new entries appear automatically after each alert.

### Verify remote kill switch

1. Open the hosted dashboard (or run `firebase deploy` and open the URL).
2. Click **Deactivate (Sleep)** — Spooky prints `😴 Spooky is sleeping (website control)` within 5 seconds.
3. Click **Activate Monitoring** — Spooky resumes automatically.

---

## 🔒 Security Notes

- All API keys are stored in `.env` and never committed to this repository
- Firebase Admin SDK credentials are excluded via `.gitignore`
- Firebase Admin SDK credentials should be stored outside the repo entirely, not just gitignored
- Generated screenshots and Firebase cache files should stay local and not be committed
- Firebase web config in `index.html` is intentionally public (secured by Firebase Security Rules)

---

## 👻 Made with ❤️ for the Gemini Live Agent Challenge
`#GeminiLiveAgentChallenge`
