#!/usr/bin/env python3
"""Quick diagnostic for speech recognition issues"""

import speech_recognition as sr
import sys

print("🔍 Testing Speech Recognition Setup...")
print("=" * 50)

# Test 1: Check if microphone is available
print("\n1️⃣ Checking microphone availability...")
try:
    mic = sr.Microphone()
    print(f"✅ Microphone found: {sr.Microphone.list_microphone_indexes()}")
except Exception as e:
    print(f"❌ Microphone error: {e}")
    sys.exit(1)

# Test 2: Try listening and recognizing
print("\n2️⃣ Starting microphone test (speak after the beep)...")
recognizer = sr.Recognizer()

try:
    with sr.Microphone() as source:
        print("🎤 Adjusting for ambient noise (please wait 2 seconds)...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print("⏺️ LISTENING NOW - Speak clearly into the microphone...")
        
        # Increase threshold to be more lenient
        audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
        print("✅ Audio captured!")
        
        print("\n3️⃣ Processing audio with Google Speech Recognition...")
        try:
            text = recognizer.recognize_google(audio)
            print(f"✅ RECOGNIZED: '{text}'")
        except sr.UnknownValueError:
            print("❌ Google API couldn't understand the audio (was it clear enough?)")
        except sr.RequestError as e:
            print(f"❌ Google API error (check internet): {e}")
            
except sr.WaitTimeoutError:
    print("❌ Timeout - no speech detected. Check microphone volume/sensitivity.")
except Exception as e:
    print(f"❌ Unexpected error: {type(e).__name__}: {e}")

print("\n" + "=" * 50)
print("Test complete!")
