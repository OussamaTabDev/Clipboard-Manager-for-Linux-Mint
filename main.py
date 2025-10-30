import pyperclip as pc
from collections import deque
import time
import threading

# Configuration
max_size = 100
clip_history = deque(maxlen=max_size)

# Store the initial clipboard content so we don't save it
initial_clipboard = ""

def watch_clipboard():
    global initial_clipboard
    # Read current clipboard once at start
    try:
        initial_clipboard = pc.paste()
    except:
        initial_clipboard = ""

    last_saved = initial_clipboard  # don't save this

    print(" Clipboard history started. Monitoring new copies...\n")
    
    while True:
        try:
            current = pc.paste()
            
            # Only save if:
            # - it's not empty
            # - it's different from last saved
            # - it's not already in history (optional dedup)
            if current and current != last_saved:
                # Optional: skip if already in history (remove if you want duplicates)
                if current not in clip_history:
                    clip_history.append(current)
                    preview = (current[:47] + '...') if len(current) > 50 else current
                    print(f"✅ Saved: {repr(preview)}")
                last_saved = current

        except Exception as e:
            print(f"⚠️ Clipboard error: {e}")

        time.sleep(0.3)  # check ~3 times per second

# --- Control functions ---
def get_max_size():
    return max_size

def set_max_size(new_size):
    global max_size, clip_history
    if new_size <= 0:
        raise ValueError("Max size must be > 0")
    max_size = new_size
    # Rebuild deque with new max length (keeps most recent items)
    clip_history = deque(clip_history, maxlen=max_size)
    print(f"📌 Max size updated to {max_size}")

def get_history():
    return list(clip_history)

def clear_history():
    clip_history.clear()
    print("🗑️ History cleared")

