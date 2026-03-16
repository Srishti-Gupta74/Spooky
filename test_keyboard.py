#!/usr/bin/env python3
"""Test keyboard input fallback for speech recognition"""

import speech_recognition as sr

print("Testing keyboard input fallback...")
print("-" * 50)

# Simulate the listen_to_user function
try:
    import pyaudio
    print("✅ PyAudio available - would use microphone")
except ImportError:
    print("⚠️ PyAudio not available - using keyboard fallback")
    print("\nEnter your response when prompted:")
    text = input("You: ").strip()
    if text:
        print(f"Received: '{text}'")
    else:
        print("No input received")
