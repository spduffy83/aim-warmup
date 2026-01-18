from pynput import keyboard
from pynput.keyboard import Key, KeyCode

class HotkeyManager:
    def __init__(self, toggle_callback):
        self.toggle_callback = toggle_callback
        self.current_keys = set()
        
        # Define the hotkey combination: Ctrl+Shift+A
        self.HOTKEY_COMBINATION = {
            Key.ctrl_l,
            Key.shift,
            KeyCode.from_char('a')
        }
        
        # Start listener
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        
    def on_press(self, key):
        """Handle key press"""
        # Normalize the key
        if isinstance(key, KeyCode):
            key = KeyCode.from_char(key.char.lower()) if key.char else key
        
        self.current_keys.add(key)
        
        # Check if hotkey combination is pressed (must match exactly)
        if self.current_keys == self.HOTKEY_COMBINATION:
            self.toggle_callback()
            
    def on_release(self, key):
        """Handle key release"""
        # Normalize the key
        if isinstance(key, KeyCode):
            key = KeyCode.from_char(key.char.lower()) if key.char else key
            
        if key in self.current_keys:
            self.current_keys.remove(key)
            
    def stop(self):
        """Stop the listener"""
        self.listener.stop()
