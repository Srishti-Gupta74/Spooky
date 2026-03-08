from google import genai
import pyautogui
import PIL.Image
import time
import pyttsx3 

# 1. INITIALIZE THE VOICE ENGINE
engine = pyttsx3.init()
engine.setProperty('rate', 170)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)

# 2. SETUP CLIENT
# Using a dictionary for http_options is the most stable way to avoid import errors
client = genai.Client(
    api_key="AIzaSyBVyLdoNvjiCY_b_edrCakgIWKQOVfPzjc", 
    http_options={'api_version': 'v1'}
)

print("👁️ Spooky is online! (Press Ctrl+C to stop)")

try:
    for i in range(10):
        # 1. Capture the screen
        screenshot = pyautogui.screenshot()
        screenshot.save("current_view.png")
        img = PIL.Image.open("current_view.png")

        # 2. Analyze with Gemini 2.5 Flash-Lite
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                "You are Spooky, a security guardian. "
                "CRITICAL: Ignore VS Code and all Python code text. "
                "Look ONLY at browsers. If safe, say 'Clear'. "
                "If you see a scam or phishing link, give a 3-word warning.", 
                img
            ]
        )

        analysis = response.text
        print(f"Check {i+1}: {analysis}")
        
        # 3. VOICE LOGIC: Only talk if it's NOT 'Clear'
        # This prevents the 'hanging' problem you had earlier!
        # 4. CONDITIONAL INTERACTION
       # 4. CONDITIONAL INTERACTION (Voice + Type)
        if "Clear" not in analysis:
            # Spooky speaks the warning out loud
            engine.say(analysis + ". Type your question below if you want to know why.")
            engine.runAndWait()
            
            # You type your interaction (Real-time input)
            user_input = input("Spooky is waiting for your question: ")
            
            if user_input:
                try:
                    # AI explains based on the visual context
                    chat_response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=[f"User asked: {user_input} about this screen.", img]
                    )
                    print(f"Spooky Explains: {chat_response.text}")
                    engine.say(chat_response.text)
                    engine.runAndWait()
                except Exception as e:
                    # If the 503 error happens, Spooky will say this instead of crashing
                    error_msg = "The server is a bit busy. Please try asking again in a moment."
                    print(error_msg)
                    engine.say(error_msg)
                    engine.runAndWait()
                    # ... after engine.runAndWait() ...
            print("🛡️ Threat consultation complete. Resuming background watch...")
        else:
            print("--- System Secure (Silent Mode) ---")
        
        # 4. Wait 15 seconds (Best for Flash-Lite free tier limits)
        time.sleep(15)

except KeyboardInterrupt:
    print("\n👻 Spooky is going back to sleep.")

