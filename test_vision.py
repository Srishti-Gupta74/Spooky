import pyautogui

# This takes a screenshot and saves it to your folder
screenshot = pyautogui.screenshot()
screenshot.save("test_view.png")
print("I can see your screen! Check the folder for 'test_view.png'.")
