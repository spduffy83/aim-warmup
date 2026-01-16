import tkinter as tk
import random
import time

class AimExercise:
    def __init__(self, root, stats_tracker):
        self.root = root
        self.stats = stats_tracker
        self.target_size = 40
        self.is_active = False
        self.target_spawn_time = 0
        
        # Create UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the exercise UI"""
        # Title
        title = tk.Label(
            self.root,
            text="Aim Warmup Trainer",
            font=("Arial", 24, "bold"),
            bg="#1a1a1a",
            fg="#ffffff"
        )
        title.pack(pady=20)
        
        # Stats display
        self.stats_label = tk.Label(
            self.root,
            text="Press START to begin",
            font=("Arial", 14),
            bg="#1a1a1a",
            fg="#00ff00"
        )
        self.stats_label.pack(pady=10)
        
        # Canvas for targets
        self.canvas = tk.Canvas(
            self.root,
            width=700,
            height=400,
            bg="#2a2a2a",
            highlightthickness=0
        )
        self.canvas.pack(pady=20)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg="#1a1a1a")
        button_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            button_frame,
            text="START",
            command=self.start_exercise,
            font=("Arial", 12, "bold"),
            bg="#00aa00",
            fg="white",
            width=10,
            relief=tk.FLAT
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame,
            text="STOP",
            command=self.stop_exercise,
            font=("Arial", 12, "bold"),
            bg="#aa0000",
            fg="white",
            width=10,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = tk.Button(
            button_frame,
            text="RESET STATS",
            command=self.reset_stats,
            font=("Arial", 12),
            bg="#555555",
            fg="white",
            width=12,
            relief=tk.FLAT
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
    def start_exercise(self):
        """Start the aim exercise"""
        self.is_active = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.spawn_target()
        
    def stop_exercise(self):
        """Stop the aim exercise"""
        self.is_active = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.canvas.delete("all")
        self.update_stats_display()
        
    def reset_stats(self):
        """Reset statistics"""
        self.stats.reset()
        self.update_stats_display()
        
    def spawn_target(self):
        """Spawn a new target at random position"""
        if not self.is_active:
            return
            
        self.canvas.delete("all")
        
        # Random position
        x = random.randint(self.target_size, 700 - self.target_size)
        y = random.randint(self.target_size, 400 - self.target_size)
        
        # Draw target (red circle)
        self.canvas.create_oval(
            x - self.target_size,
            y - self.target_size,
            x + self.target_size,
            y + self.target_size,
            fill="#ff0000",
            outline="#ffffff",
            width=2,
            tags="target"
        )
        
        # Store target position and spawn time
        self.target_pos = (x, y)
        self.target_spawn_time = time.time()
        
    def on_canvas_click(self, event):
        """Handle canvas click"""
        if not self.is_active:
            return
            
        # Calculate distance from target center
        dx = event.x - self.target_pos[0]
        dy = event.y - self.target_pos[1]
        distance = (dx**2 + dy**2) ** 0.5
        
        # Check if hit
        if distance <= self.target_size:
            reaction_time = time.time() - self.target_spawn_time
            self.stats.record_hit(reaction_time)
            self.update_stats_display()
            self.spawn_target()
        else:
            self.stats.record_miss()
            self.update_stats_display()
            
    def update_stats_display(self):
        """Update the statistics display"""
        accuracy = self.stats.get_accuracy()
        avg_time = self.stats.get_average_reaction_time()
        
        stats_text = f"Hits: {self.stats.hits} | Misses: {self.stats.misses} | Accuracy: {accuracy:.1f}%"
        if avg_time > 0:
            stats_text += f" | Avg Time: {avg_time:.3f}s"
            
        self.stats_label.config(text=stats_text)