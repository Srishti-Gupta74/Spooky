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
FIREBASE_CREDENTIALS_PATH=path/to/your/firebase-adminsdk.json
```

### 4. Add your Firebase Admin SDK credentials
- Go to Firebase Console → Project Settings → Service Accounts
- Click **Generate new private key**
- Save the downloaded `.json` file in the project folder
- Set `FIREBASE_CREDENTIALS_PATH` in your `.env` to its filename

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

---

## 📁 Project Structure

```
Spooky/
├── spooky2.py          # Main agent (run this)
├── public/
│   ├── index.html      # Web dashboard
│   └── 404.html
├── .env                # Your secrets (never committed)
├── .gitignore
├── .firebaserc
└── firebase.json
```

---

## 🔒 Security Notes

- All API keys are stored in `.env` and never committed to this repository
- Firebase Admin SDK credentials are excluded via `.gitignore`
- Firebase web config in `index.html` is intentionally public (secured by Firebase Security Rules)

---

## 👻 Made with ❤️ for the Gemini Live Agent Challenge
`#GeminiLiveAgentChallenge`
