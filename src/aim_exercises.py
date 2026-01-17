import tkinter as tk
import random
import time
import math
from pynput.mouse import Controller as MouseController

class AimExercise:
    def __init__(self, root, stats_tracker, screen_width, screen_height, 
                 h_dpi=1000, h_cm_per_360=29.39,
                 v_dpi=1250, v_cm_per_360=18.81):
        self.root = root
        self.stats = stats_tracker
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.target_size = 50
        self.is_active = False
        self.target_spawn_time = 0
        self.mouse_locked = False
        
        # Horizontal sensitivity calculations
        h_inches_per_360 = h_cm_per_360 / 2.54
        h_counts_per_360 = h_inches_per_360 * h_dpi
        self.h_counts_per_degree = h_counts_per_360 / 360.0
        
        # Vertical sensitivity calculations
        v_inches_per_360 = v_cm_per_360 / 2.54
        v_counts_per_360 = v_inches_per_360 * v_dpi
        self.v_counts_per_degree = v_counts_per_360 / 360.0
        
        # Virtual camera yaw/pitch (in degrees)
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Multiple targets - list of (yaw, pitch, spawn_time)
        self.targets = []
        self.num_targets = 5  # Number of simultaneous targets
        
        # Track if mouse was locked before losing focus
        self.mouse_was_locked = False
        
        # Crosshair trail for tracking visualization
        self.trail_points = []  # List of (yaw, pitch, timestamp)
        self.trail_fade_time = 0.5  # Seconds before trail fades completely
        self.last_trail_time = 0  # Track when we last added a trail point
        
        # Mouse controller
        self.mouse = MouseController()
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        
        # FOV settings for projection
        self.fov = 90  # Field of view in degrees
        self.pixels_per_degree = screen_width / self.fov
        
        # Create UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the exercise UI"""
        # Title
        self.title = tk.Label(
            self.root,
            text="FPS Aim Trainer - Move mouse to aim, Click to shoot",
            font=("Arial", 20, "bold"),
            bg="#1a1a1a",
            fg="#ffffff"
        )
        self.title.pack(pady=10)
        
        # Control buttons at top
        self.button_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.button_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            self.button_frame,
            text="START",
            command=self.start_exercise,
            font=("Arial", 12, "bold"),
            bg="#00aa00",
            fg="white",
            width=10,
            height=1,
            relief=tk.FLAT
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(
            self.button_frame,
            text="STOP",
            command=self.stop_exercise,
            font=("Arial", 12, "bold"),
            bg="#aa0000",
            fg="white",
            width=10,
            height=1,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        self.reset_btn = tk.Button(
            self.button_frame,
            text="RESET STATS",
            command=self.reset_stats,
            font=("Arial", 12),
            bg="#555555",
            fg="white",
            width=12,
            height=1,
            relief=tk.FLAT
        )
        self.reset_btn.pack(side=tk.LEFT, padx=10)
        
        # Stats display
        self.stats_label = tk.Label(
            self.root,
            text="Press START to begin | ESC to exit",
            font=("Arial", 14),
            bg="#1a1a1a",
            fg="#00ff00"
        )
        self.stats_label.pack(pady=5)
        
        # Canvas for targets (will fill screen when game starts)
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height - 150,
            bg="#2a2a2a",
            highlightthickness=0,
            cursor="none"
        )
        self.canvas.pack(pady=5)
        self.canvas.bind("<Button-1>", self.on_shoot)
        
        # Bind focus events to handle tabbing out
        self.root.bind("<FocusOut>", self.on_focus_lost)
        self.root.bind("<FocusIn>", self.on_focus_gained)
        
        # Store initial canvas height
        self.canvas_height_inactive = self.screen_height - 150
        
    def start_exercise(self):
        """Start the aim exercise"""
        self.is_active = True
        self.mouse_locked = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Hide UI elements
        self.title.pack_forget()
        self.button_frame.pack_forget()
        self.stats_label.pack_forget()
        
        # Expand canvas to full screen
        self.canvas.pack_forget()
        self.canvas.config(height=self.screen_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas_width = self.screen_width
        self.canvas_height = self.screen_height
        
        # Reset camera angles
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Clear targets and trail
        self.targets = []
        self.trail_points = []
        
        # Store last mouse position for delta calculation
        pos = self.mouse.position
        self.last_mouse_x = pos[0]
        self.last_mouse_y = pos[1]
        
        # Spawn initial targets
        for _ in range(self.num_targets):
            self.spawn_target()
        
        self.lock_mouse_loop()
        
    def stop_exercise(self):
        """Stop the aim exercise"""
        self.is_active = False
        self.mouse_locked = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # Show UI elements again
        self.canvas.pack_forget()
        self.title.pack(pady=10)
        self.button_frame.pack(pady=10)
        self.stats_label.pack(pady=5)
        
        # Restore canvas size
        self.canvas.config(height=self.canvas_height_inactive)
        self.canvas.pack(pady=5)
        self.canvas_width = self.screen_width
        self.canvas_height = self.canvas_height_inactive
        
        self.canvas.delete("all")
        self.update_stats_display()
        
    def reset_stats(self):
        """Reset statistics"""
        self.stats.reset()
        self.update_stats_display()
        
    def lock_mouse_loop(self):
        """Continuously recenter mouse and update view"""
        if self.is_active:
            if self.mouse_locked:
                # Get current mouse position
                pos = self.mouse.position
                current_x, current_y = pos[0], pos[1]
                
                # Calculate delta (mouse movement)
                delta_x = current_x - self.last_mouse_x
                delta_y = current_y - self.last_mouse_y
                
                # Update camera angles with separate horizontal/vertical sensitivity
                self.yaw += delta_x / self.h_counts_per_degree
                self.pitch -= delta_y / self.v_counts_per_degree
                
                # Clamp pitch to prevent over-rotation
                self.pitch = max(-89, min(89, self.pitch))
                
                # Normalize yaw to 0-360
                self.yaw = self.yaw % 360
                
                # Add trail point every few milliseconds
                current_time = time.time()
                if current_time - self.last_trail_time > 0.01:  # Every 10ms
                    self.trail_points.append((self.yaw, self.pitch, current_time))
                    self.last_trail_time = current_time
                
                # Recenter mouse to lock position only if window has focus
                if self.root.focus_displayof() is not None:
                    self.mouse.position = (self.center_x, self.center_y)
                    self.last_mouse_x = self.center_x
                    self.last_mouse_y = self.center_y
            
            # Always redraw the scene (even when unlocked)
            self.draw_scene()
            
            # Schedule next check
            self.root.after(1, self.lock_mouse_loop)
            
    def spawn_target(self):
        """Spawn a new target at random position within visible screen bounds"""
        if not self.is_active:
            return
        
        # Spawn target at a fixed position relative to current view
        # Calculate safe bounds (80% of screen to ensure fully visible)
        safe_width = self.canvas_width * 0.8
        safe_height = self.canvas_height * 0.8
        
        # Random screen position
        screen_x = (self.canvas_width // 2) + random.uniform(-safe_width/2, safe_width/2)
        screen_y = (self.canvas_height // 2) + random.uniform(-safe_height/2, safe_height/2)
        
        # Convert screen position to angular offset from center
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2
        
        pixel_offset_x = screen_x - center_x
        pixel_offset_y = screen_y - center_y
        
        # Convert pixels to degrees
        yaw_offset = pixel_offset_x / self.pixels_per_degree
        pitch_offset = -pixel_offset_y / self.pixels_per_degree
        
        # Calculate target world position
        target_yaw = self.yaw + yaw_offset
        target_pitch = self.pitch + pitch_offset
        
        # Clamp pitch to reasonable bounds
        target_pitch = max(-89, min(89, target_pitch))
        
        # Add to targets list: (yaw, pitch, spawn_time)
        self.targets.append((target_yaw, target_pitch, time.time()))
        
    def draw_scene(self):
        """Draw the crosshair, trail, and targets based on camera view"""
        self.canvas.delete("all")
        
        current_time = time.time()
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2
        
        # Draw stats overlay at top
        if self.is_active:
            accuracy = self.stats.get_accuracy()
            avg_time = self.stats.get_average_reaction_time()
            stats_text = f"Hits: {self.stats.hits} | Misses: {self.stats.misses} | Accuracy: {accuracy:.1f}%"
            if avg_time > 0:
                stats_text += f" | Avg Time: {avg_time:.3f}s"
            
            # Add message if mouse is unlocked
            if not self.mouse_locked and self.mouse_was_locked:
                stats_text += " | CLICK TO REACTIVATE MOUSE LOCK"
            
            self.canvas.create_text(
                center_x,
                30,
                text=stats_text,
                font=("Arial", 16, "bold"),
                fill="#00ff00",
                tags="stats"
            )
        
        # Remove old trail points (older than fade time)
        self.trail_points = [
            (yaw, pitch, t) for yaw, pitch, t in self.trail_points 
            if current_time - t < self.trail_fade_time
        ]
        
        # Draw trail with fading effect
        if len(self.trail_points) > 1:
            for i in range(len(self.trail_points) - 1):
                yaw1, pitch1, t1 = self.trail_points[i]
                yaw2, pitch2, t2 = self.trail_points[i + 1]
                
                # Convert trail points from world space to screen space
                yaw_diff1 = yaw1 - self.yaw
                pitch_diff1 = pitch1 - self.pitch
                yaw_diff2 = yaw2 - self.yaw
                pitch_diff2 = pitch2 - self.pitch
                
                # Normalize yaw differences
                while yaw_diff1 > 180:
                    yaw_diff1 -= 360
                while yaw_diff1 < -180:
                    yaw_diff1 += 360
                while yaw_diff2 > 180:
                    yaw_diff2 -= 360
                while yaw_diff2 < -180:
                    yaw_diff2 += 360
                
                # Convert to screen coordinates
                x1 = center_x + (yaw_diff1 * self.pixels_per_degree)
                y1 = center_y - (pitch_diff1 * self.pixels_per_degree)
                x2 = center_x + (yaw_diff2 * self.pixels_per_degree)
                y2 = center_y - (pitch_diff2 * self.pixels_per_degree)
                
                # Calculate fade based on age
                age = current_time - t1
                opacity = max(0, 1 - (age / self.trail_fade_time))
                
                # Convert opacity to color (cyan/blue trail)
                blue_value = int(200 + (55 * opacity))
                green_value = int(150 + (105 * opacity))
                color = f'#{0:02x}{green_value:02x}{blue_value:02x}'
                
                # Only draw if on screen
                if (0 <= x1 <= self.canvas_width and 0 <= y1 <= self.canvas_height and
                    0 <= x2 <= self.canvas_width and 0 <= y2 <= self.canvas_height):
                    self.canvas.create_line(
                        x1, y1, x2, y2,
                        fill=color,
                        width=int(2 + opacity * 2),
                        tags="trail"
                    )
        
        # Draw crosshair in center (your aim point)
        crosshair_size = 15
        
        self.canvas.create_line(
            center_x - crosshair_size, center_y,
            center_x + crosshair_size, center_y,
            fill="#00ff00",
            width=2
        )
        self.canvas.create_line(
            center_x, center_y - crosshair_size,
            center_x, center_y + crosshair_size,
            fill="#00ff00",
            width=2
        )
        self.canvas.create_oval(
            center_x - 2, center_y - 2,
            center_x + 2, center_y + 2,
            fill="#00ff00"
        )
        
        # Draw all targets
        targets_on_screen = []
        for target_yaw, target_pitch, spawn_time in self.targets:
            # Calculate target position relative to camera
            yaw_diff = target_yaw - self.yaw
            pitch_diff = target_pitch - self.pitch
            
            # Normalize yaw difference to -180 to 180
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            # Convert angular difference to screen pixels
            target_screen_x = center_x + (yaw_diff * self.pixels_per_degree)
            target_screen_y = center_y - (pitch_diff * self.pixels_per_degree)
            
            # Check if target is within screen bounds
            margin = self.target_size + 10
            if (-margin <= target_screen_x <= self.canvas_width + margin and 
                -margin <= target_screen_y <= self.canvas_height + margin):
                
                targets_on_screen.append((target_yaw, target_pitch, spawn_time))
                
                # Draw target
                self.canvas.create_oval(
                    target_screen_x - self.target_size,
                    target_screen_y - self.target_size,
                    target_screen_x + self.target_size,
                    target_screen_y + self.target_size,
                    fill="#ff0000",
                    outline="#ffffff",
                    width=3,
                    tags="target"
                )
                
                # Draw target center dot
                self.canvas.create_oval(
                    target_screen_x - 5,
                    target_screen_y - 5,
                    target_screen_x + 5,
                    target_screen_y + 5,
                    fill="#ffffff",
                    tags="target"
                )
        
        # Update targets list to only include on-screen targets
        self.targets = targets_on_screen
        
        # Ensure we always have the target number of targets
        while len(self.targets) < self.num_targets:
            self.spawn_target()
        
    def on_shoot(self, event):
        """Handle shooting (clicking)"""
        # If mouse was unlocked due to focus loss, re-lock it on click
        if self.is_active and not self.mouse_locked and self.mouse_was_locked:
            self.mouse_locked = True
            self.mouse_was_locked = False
            self.mouse.position = (self.center_x, self.center_y)
            self.last_mouse_x = self.center_x
            self.last_mouse_y = self.center_y
            return  # Don't process this click as a shot
        
        if not self.is_active:
            return
        
        hit_target = None
        min_distance = float('inf')
        
        # Check each target to see if any were hit
        for i, (target_yaw, target_pitch, spawn_time) in enumerate(self.targets):
            # Calculate angular distance from crosshair to this target
            yaw_diff = target_yaw - self.yaw
            pitch_diff = target_pitch - self.pitch
            
            # Normalize yaw difference
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            # Calculate angular distance in degrees
            angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
            
            # Target angular size (approximate)
            target_angular_size = self.target_size / self.pixels_per_degree
            
            # Check if hit (within target angular size)
            if angular_distance <= target_angular_size:
                # Find the closest target if multiple hits
                if angular_distance < min_distance:
                    min_distance = angular_distance
                    hit_target = (i, spawn_time)
        
        # Process the hit
        if hit_target is not None:
            target_index, spawn_time = hit_target
            reaction_time = time.time() - spawn_time
            self.stats.record_hit(reaction_time)
            
            # Remove the hit target
            del self.targets[target_index]
            
            # Spawn a new target to maintain count
            self.spawn_target()
            
            self.update_stats_display()
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
        
        # Only update label when not in active gameplay (stats drawn in draw_scene when active)
        if not self.is_active:
            self.stats_label.config(text=stats_text)
        
    def on_focus_lost(self, event):
        """Handle window losing focus (tabbing out)"""
        if self.is_active:
            # Temporarily unlock mouse when window loses focus
            self.mouse_locked = False
            self.mouse_was_locked = True  # Remember it was locked
            
    def on_focus_gained(self, event):
        """Handle window gaining focus (tabbing back in)"""
        # Don't auto-relock, let user click to reactivate
        pass
    
    def cleanup(self):
        """Cleanup resources"""
        self.mouse_locked = False
        self.is_active = False