import tkinter as tk
from src.hotkey_manager import HotkeyManager
from src.aim_exercises import AimExercise
from src.stats_tracker import StatsTracker

class AimWarmupApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aim Warmup")
        self.root.geometry("800x600")
        self.root.configure(bg="#1a1a1a")
        
        # Initialize components
        self.stats = StatsTracker()
        self.aim_exercise = AimExercise(self.root, self.stats)
        
        # Setup hotkey (Ctrl+Shift+A to toggle)
        self.hotkey_manager = HotkeyManager(self.toggle_window)
        
        # Start visible for testing
        self.is_visible = True
        self.root.lift()
        self.root.focus_force()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def toggle_window(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.root.withdraw()  # Hide
            self.is_visible = False
        else:
            self.root.deiconify()  # Show
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
            
    def on_close(self):
        """Clean up and close"""
        self.hotkey_manager.stop()
        self.root.destroy()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AimWarmupApp()
    app.run()