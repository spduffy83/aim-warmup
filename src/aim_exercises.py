import tkinter as tk
import random
import time
import math
from pynput.mouse import Controller as MouseController

class AimExercise:
    def __init__(self, root, stats_tracker, screen_width, screen_height, 
                 h_dpi=1000, h_cm_per_360=31.058,
                 v_dpi=1000, v_cm_per_360=31.058):
        self.root = root
        self.stats = stats_tracker
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.target_size = 25  # Base target size
        self.target_min_size = 15  # Minimum size when pulsing
        self.target_max_size = 35  # Maximum size when pulsing
        self.target_lifetime = 3.0  # Seconds before target disappears
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
        
        # Sensitivity matching toggle
        self.match_sensitivities = False  # Default to independent
        self.original_v_counts_per_degree = self.v_counts_per_degree
        
        # Virtual camera yaw/pitch (in degrees)
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Multiple targets - list of (yaw, pitch, spawn_time)
        self.targets = []
        self.num_targets = 5  # Number of simultaneous targets
        
        # Game mode
        self.game_mode = None  # Will be 'random', 'shapes', or 'tracking'
        
        # Shape tracking mode variables
        self.current_shape = []  # List of target positions for current shape
        self.current_shape_index = 0  # Which target in the shape to hit next
        self.shapes_completed = 0
        self.total_shapes = 10
        self.shape_types = ['square', 'triangle', 'circle', 'diamond', 'pentagon']
        
        # Tracking mode variables
        self.tracking_targets = []  # List of tracking target objects
        self.tracking_score = 0
        self.tracking_time_on_target = 0.0
        self.tracking_total_time = 0.0
        self.tracking_start_time = 0
        self.tracking_duration = 60  # 60 second rounds
        
        # Track if mouse was locked before losing focus
        self.mouse_was_locked = False
        
        # Crosshair trail for tracking visualization
        self.trail_points = []  # List of (yaw, pitch, timestamp)
        self.trail_fade_time = 0.5  # Seconds before trail fades completely
        self.last_trail_time = 0  # Track when we last added a trail point
        
        # Path efficiency tracking
        self.last_hit_yaw = 0.0  # Position where last target was hit
        self.last_hit_pitch = 0.0
        self.path_points = []  # List of (yaw, pitch) points during movement
        self.path_efficiencies = []  # List of efficiency percentages for averaging
        self.has_last_hit = False  # Whether we have a previous hit to measure from
        
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
            text="FPS Aim Trainer - Select Your Mode",
            font=("Arial", 24, "bold"),
            bg="#1a1a1a",
            fg="#ffffff"
        )
        self.title.pack(pady=20)
        
        # Mode selection frame
        self.mode_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.mode_frame.pack(pady=20)
        
        # Random targets mode button
        self.random_mode_btn = tk.Button(
            self.mode_frame,
            text="RANDOM TARGETS\n\nClick 5 targets appearing randomly",
            command=lambda: self.select_mode('random'),
            font=("Arial", 14, "bold"),
            bg="#0066cc",
            fg="white",
            width=25,
            height=5,
            relief=tk.FLAT
        )
        self.random_mode_btn.pack(side=tk.LEFT, padx=15)
        
        # Shape tracking mode button
        self.shapes_mode_btn = tk.Button(
            self.mode_frame,
            text="SHAPE TRACKING\n\nFollow geometric patterns\nComplete 10 shapes",
            command=lambda: self.select_mode('shapes'),
            font=("Arial", 14, "bold"),
            bg="#cc6600",
            fg="white",
            width=25,
            height=5,
            relief=tk.FLAT
        )
        self.shapes_mode_btn.pack(side=tk.LEFT, padx=15)
        
        # Tracking practice mode button
        self.tracking_mode_btn = tk.Button(
            self.mode_frame,
            text="TRACKING PRACTICE\n\nKeep crosshair on moving targets\n60 second rounds",
            command=lambda: self.select_mode('tracking'),
            font=("Arial", 14, "bold"),
            bg="#00aa66",
            fg="white",
            width=25,
            height=5,
            relief=tk.FLAT
        )
        self.tracking_mode_btn.pack(side=tk.LEFT, padx=15)
        
        # Control buttons (initially hidden)
        self.button_frame = tk.Frame(self.root, bg="#1a1a1a")
        
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
        
        self.back_btn = tk.Button(
            self.button_frame,
            text="CHANGE MODE",
            command=self.back_to_mode_select,
            font=("Arial", 12),
            bg="#555555",
            fg="white",
            width=12,
            height=1,
            relief=tk.FLAT
        )
        self.back_btn.pack(side=tk.LEFT, padx=10)
        
        # Sensitivity toggle button
        self.sens_toggle_btn = tk.Button(
            self.button_frame,
            text="MATCH Y SENS",
            command=self.toggle_sensitivity_match,
            font=("Arial", 12),
            bg="#0066aa",
            fg="white",
            width=12,
            height=1,
            relief=tk.FLAT
        )
        self.sens_toggle_btn.pack(side=tk.LEFT, padx=10)
        
        # Stats display
        self.stats_label = tk.Label(
            self.root,
            text="Select a mode to begin",
            font=("Arial", 14),
            bg="#1a1a1a",
            fg="#00ff00"
        )
        self.stats_label.pack(pady=5)
        
        # Canvas for targets (will fill screen when game starts)
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height - 200,
            bg="#2a2a2a",
            highlightthickness=0,
            cursor="none"
        )
        self.canvas.bind("<Button-1>", self.on_shoot)
        
        # Don't pack canvas yet - it will be packed when mode is selected
        
        # Bind focus events to handle tabbing out
        self.root.bind("<FocusOut>", self.on_focus_lost)
        self.root.bind("<FocusIn>", self.on_focus_gained)
        
        # Store initial canvas height
        self.canvas_height_inactive = self.screen_height - 200
        
    def select_mode(self, mode):
        """Select game mode"""
        self.game_mode = mode
        
        # Hide mode selection
        self.mode_frame.pack_forget()
        
        # Update title
        if mode == 'random':
            self.title.config(text="Random Targets Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Press START to begin | ESC to exit")
        elif mode == 'shapes':
            self.title.config(text="Shape Tracking Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Complete 10 shapes | Press START to begin | ESC to exit")
        elif mode == 'tracking':
            self.title.config(text="Tracking Practice Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Keep crosshair on targets to degrade them | 60 seconds | ESC to exit")
        
        # Show control buttons
        self.button_frame.pack(pady=10)
        
        # Show canvas
        self.canvas.pack(pady=5)
        
    def back_to_mode_select(self):
        """Return to mode selection"""
        if self.is_active:
            self.stop_exercise()
        
        self.game_mode = None
        self.button_frame.pack_forget()
        self.canvas.pack_forget()
        self.title.config(text="FPS Aim Trainer - Select Your Mode", font=("Arial", 24, "bold"))
        self.stats_label.config(text="Select a mode to begin")
        self.mode_frame.pack(pady=20)
    
    def toggle_sensitivity_match(self):
        """Toggle between matched and independent sensitivities"""
        self.match_sensitivities = not self.match_sensitivities
        
        if self.match_sensitivities:
            # Match Y sensitivity to X (same cm/360 feel accounting for different DPI)
            # X: 1000 DPI at 29.39 cm/360 = certain counts_per_degree
            # Y: 1250 DPI needs to achieve the same counts_per_degree
            # So we just use the same counts_per_degree value
            self.v_counts_per_degree = self.h_counts_per_degree
            
            self.sens_toggle_btn.config(
                text="Y = X SENS ✓",
                bg="#00aa00"
            )
        else:
            # Restore original vertical sensitivity
            self.v_counts_per_degree = self.original_v_counts_per_degree
            self.sens_toggle_btn.config(
                text="MATCH Y SENS",
                bg="#0066aa"
            )
        
    def start_exercise(self):
        """Start the aim exercise"""
        if self.game_mode is None:
            return
            
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
        self.path_efficiencies = []  # Reset path tracking
        self.path_points = []
        self.has_last_hit = False
        
        # Reset shape mode variables
        self.shapes_completed = 0
        self.current_shape_index = 0
        
        # Store last mouse position for delta calculation
        pos = self.mouse.position
        self.last_mouse_x = pos[0]
        self.last_mouse_y = pos[1]
        
        # Spawn initial targets based on mode
        if self.game_mode == 'random':
            for _ in range(self.num_targets):
                self.spawn_target()
        elif self.game_mode == 'shapes':
            self.spawn_shape()
        elif self.game_mode == 'tracking':
            self.tracking_start_time = time.time()
            self.tracking_time_on_target = 0.0
            self.tracking_total_time = 0.0
            self.tracking_targets = []
            self.spawn_tracking_target()
            self.spawn_tracking_target()  # Start with 2 targets
        
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
                    
                    # Track path for efficiency calculation (always recording in random mode)
                    if self.game_mode == 'random' and self.has_last_hit:
                        self.path_points.append((self.yaw, self.pitch))
                
                # Recenter mouse to lock position only if window has focus
                if self.root.focus_displayof() is not None:
                    self.mouse.position = (self.center_x, self.center_y)
                    self.last_mouse_x = self.center_x
                    self.last_mouse_y = self.center_y
            
            # Always redraw the scene (even when unlocked)
            self.draw_scene()
            
            # Update tracking targets if in tracking mode
            if self.game_mode == 'tracking' and self.mouse_locked:
                current_time = time.time()
                delta_time = 0.016  # Approximately 60fps
                self.update_tracking_targets(delta_time)
                
                # Check if time is up
                elapsed = current_time - self.tracking_start_time
                if elapsed >= self.tracking_duration:
                    self.stop_exercise()
                    return
            
            # Schedule next check
            self.root.after(1, self.lock_mouse_loop)
    
    def spawn_shape(self):
        """Spawn a geometric shape pattern"""
        if not self.is_active:
            return
        
        # Choose random shape type
        shape_type = random.choice(self.shape_types)
        
        # Random center position on screen
        center_screen_x = self.canvas_width // 2 + random.uniform(-300, 300)
        center_screen_y = self.canvas_height // 2 + random.uniform(-250, 250)
        
        # Shape size in pixels (larger shapes)
        shape_size = random.uniform(300, 500)
        
        # Generate target positions based on shape type
        shape_targets = []
        
        if shape_type == 'square':
            # 4 corners of a square
            offsets = [
                (-shape_size/2, -shape_size/2),
                (shape_size/2, -shape_size/2),
                (shape_size/2, shape_size/2),
                (-shape_size/2, shape_size/2)
            ]
        elif shape_type == 'triangle':
            # 3 points of equilateral triangle
            offsets = [
                (0, -shape_size * 0.6),
                (-shape_size/2, shape_size * 0.3),
                (shape_size/2, shape_size * 0.3)
            ]
        elif shape_type == 'circle':
            # 8 points around a circle
            offsets = []
            for i in range(8):
                angle = (i * 360 / 8) * (math.pi / 180)
                offsets.append((
                    math.cos(angle) * shape_size/2,
                    math.sin(angle) * shape_size/2
                ))
        elif shape_type == 'diamond':
            # 4 points of diamond
            offsets = [
                (0, -shape_size/2),
                (shape_size/2, 0),
                (0, shape_size/2),
                (-shape_size/2, 0)
            ]
        elif shape_type == 'pentagon':
            # 5 points of pentagon
            offsets = []
            for i in range(5):
                angle = (i * 360 / 5 - 90) * (math.pi / 180)
                offsets.append((
                    math.cos(angle) * shape_size/2,
                    math.sin(angle) * shape_size/2
                ))
        
        # Convert screen offsets to world angles
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2
        
        for offset_x, offset_y in offsets:
            screen_x = center_screen_x + offset_x
            screen_y = center_screen_y + offset_y
            
            # Convert to angular offset
            pixel_offset_x = screen_x - center_x
            pixel_offset_y = screen_y - center_y
            
            yaw_offset = pixel_offset_x / self.pixels_per_degree
            pitch_offset = -pixel_offset_y / self.pixels_per_degree
            
            target_yaw = self.yaw + yaw_offset
            target_pitch = self.pitch + pitch_offset
            target_pitch = max(-89, min(89, target_pitch))
            
            shape_targets.append((target_yaw, target_pitch, time.time()))
        
        self.current_shape = shape_targets
        self.current_shape_index = 0
        self.targets = [self.current_shape[0]]  # Start with first target
            
    def calculate_path_efficiency(self, target_yaw, target_pitch):
        """Calculate how efficiently the cursor moved from last hit to this target"""
        if len(self.path_points) < 2 or not self.has_last_hit:
            return None  # Not enough data
        
        # Calculate direct distance from last hit to this target
        yaw_diff = target_yaw - self.last_hit_yaw
        # Handle yaw wraparound
        while yaw_diff > 180:
            yaw_diff -= 360
        while yaw_diff < -180:
            yaw_diff += 360
            
        direct_distance = math.sqrt(
            yaw_diff ** 2 +
            (target_pitch - self.last_hit_pitch) ** 2
        )
        
        if direct_distance < 0.1:  # Target was very close, skip
            return None
        
        # Calculate actual path length traveled
        actual_distance = 0.0
        for i in range(1, len(self.path_points)):
            yaw1, pitch1 = self.path_points[i - 1]
            yaw2, pitch2 = self.path_points[i]
            
            # Handle yaw wraparound
            seg_yaw_diff = yaw2 - yaw1
            while seg_yaw_diff > 180:
                seg_yaw_diff -= 360
            while seg_yaw_diff < -180:
                seg_yaw_diff += 360
            
            segment_distance = math.sqrt(seg_yaw_diff ** 2 + (pitch2 - pitch1) ** 2)
            actual_distance += segment_distance
        
        # Efficiency = direct / actual * 100 (100% = perfect straight line)
        if actual_distance > 0:
            efficiency = (direct_distance / actual_distance) * 100
            return min(efficiency, 100.0)  # Cap at 100%
        return None
    
    def record_hit_position(self):
        """Record the current position as a hit location"""
        self.last_hit_yaw = self.yaw
        self.last_hit_pitch = self.pitch
        self.has_last_hit = True
        self.path_points = [(self.yaw, self.pitch)]  # Start fresh path from this hit
    
    def get_average_path_efficiency(self):
        """Get average path efficiency across all tracked movements"""
        if not self.path_efficiencies:
            return 0.0
        return sum(self.path_efficiencies) / len(self.path_efficiencies)
    
    def spawn_tracking_target(self):
        """Spawn a moving target for tracking mode"""
        if not self.is_active:
            return
        
        # Random starting position within visible area
        safe_width = self.canvas_width * 0.7
        safe_height = self.canvas_height * 0.7
        
        screen_x = (self.canvas_width // 2) + random.uniform(-safe_width/2, safe_width/2)
        screen_y = (self.canvas_height // 2) + random.uniform(-safe_height/2, safe_height/2)
        
        # Convert to angular position
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2
        
        yaw_offset = (screen_x - center_x) / self.pixels_per_degree
        pitch_offset = -(screen_y - center_y) / self.pixels_per_degree
        
        target_yaw = self.yaw + yaw_offset
        target_pitch = self.pitch + pitch_offset
        
        # Random velocity (degrees per second)
        speed = random.uniform(15, 35)  # Degrees per second
        angle = random.uniform(0, 2 * math.pi)
        vel_yaw = math.cos(angle) * speed
        vel_pitch = math.sin(angle) * speed
        
        # Target properties: yaw, pitch, vel_yaw, vel_pitch, health (0-100), size
        target = {
            'yaw': target_yaw,
            'pitch': target_pitch,
            'vel_yaw': vel_yaw,
            'vel_pitch': vel_pitch,
            'health': 100.0,
            'size': 40,
            'last_update': time.time()
        }
        
        self.tracking_targets.append(target)
    
    def update_tracking_targets(self, delta_time):
        """Update tracking target positions and check for crosshair overlap"""
        targets_to_remove = []
        
        for target in self.tracking_targets:
            # Update position based on velocity
            target['yaw'] += target['vel_yaw'] * delta_time
            target['pitch'] += target['vel_pitch'] * delta_time
            
            # Bounce off screen edges (in angular space)
            max_yaw_offset = (self.canvas_width * 0.4) / self.pixels_per_degree
            max_pitch_offset = (self.canvas_height * 0.4) / self.pixels_per_degree
            
            # Calculate offset from current view
            yaw_diff = target['yaw'] - self.yaw
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            pitch_diff = target['pitch'] - self.pitch
            
            # Bounce horizontally
            if abs(yaw_diff) > max_yaw_offset:
                target['vel_yaw'] *= -1
                # Nudge back into bounds
                if yaw_diff > 0:
                    target['yaw'] = self.yaw + max_yaw_offset
                else:
                    target['yaw'] = self.yaw - max_yaw_offset
            
            # Bounce vertically
            if abs(pitch_diff) > max_pitch_offset:
                target['vel_pitch'] *= -1
                if pitch_diff > 0:
                    target['pitch'] = self.pitch + max_pitch_offset
                else:
                    target['pitch'] = self.pitch - max_pitch_offset
            
            # Clamp pitch
            target['pitch'] = max(-89, min(89, target['pitch']))
            
            # Check if crosshair is on target
            yaw_diff = target['yaw'] - self.yaw
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            pitch_diff = target['pitch'] - self.pitch
            
            angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
            target_angular_size = target['size'] / self.pixels_per_degree
            
            if angular_distance <= target_angular_size:
                # Crosshair is on target - degrade health
                damage_rate = 50.0  # Health per second while on target
                target['health'] -= damage_rate * delta_time
                self.tracking_time_on_target += delta_time
                
                if target['health'] <= 0:
                    targets_to_remove.append(target)
            
            # Randomly change direction occasionally
            if random.random() < 0.02:  # 2% chance per frame
                angle = random.uniform(0, 2 * math.pi)
                speed = math.sqrt(target['vel_yaw']**2 + target['vel_pitch']**2)
                target['vel_yaw'] = math.cos(angle) * speed
                target['vel_pitch'] = math.sin(angle) * speed
        
        # Remove destroyed targets and spawn new ones
        for target in targets_to_remove:
            self.tracking_targets.remove(target)
            self.spawn_tracking_target()
        
        self.tracking_total_time += delta_time
            
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
        
        # Draw background grid pattern for spatial reference
        grid_color = "#353535"  # Very faint grid
        grid_spacing_degrees = 10  # Grid lines every 10 degrees
        
        # Calculate grid offset based on camera position
        yaw_offset = (self.yaw % grid_spacing_degrees) * self.pixels_per_degree
        pitch_offset = (self.pitch % grid_spacing_degrees) * self.pixels_per_degree
        
        # Draw vertical grid lines
        for x in range(-self.canvas_width, self.canvas_width * 2, int(grid_spacing_degrees * self.pixels_per_degree)):
            line_x = x - yaw_offset
            if 0 <= line_x <= self.canvas_width:
                self.canvas.create_line(
                    line_x, 0, line_x, self.canvas_height,
                    fill=grid_color,
                    width=1,
                    tags="grid"
                )
        
        # Draw horizontal grid lines
        for y in range(-self.canvas_height, self.canvas_height * 2, int(grid_spacing_degrees * self.pixels_per_degree)):
            line_y = y + pitch_offset
            if 0 <= line_y <= self.canvas_height:
                self.canvas.create_line(
                    0, line_y, self.canvas_width, line_y,
                    fill=grid_color,
                    width=1,
                    tags="grid"
                )
        
        # Draw stats overlay at top
        if self.is_active:
            accuracy = self.stats.get_accuracy()
            avg_time = self.stats.get_average_reaction_time()
            
            if self.game_mode == 'random':
                stats_text = f"Hits: {self.stats.hits} | Misses: {self.stats.misses} | Accuracy: {accuracy:.1f}%"
                avg_efficiency = self.get_average_path_efficiency()
                if avg_efficiency > 0:
                    stats_text += f" | Path Efficiency: {avg_efficiency:.1f}%"
            elif self.game_mode == 'shapes':
                stats_text = f"Shape: {self.shapes_completed + 1}/{self.total_shapes} | Target: {self.current_shape_index + 1}/{len(self.current_shape)} | Hits: {self.stats.hits} | Misses: {self.stats.misses}"
            elif self.game_mode == 'tracking':
                elapsed = time.time() - self.tracking_start_time
                remaining = max(0, self.tracking_duration - elapsed)
                tracking_accuracy = 0
                if self.tracking_total_time > 0:
                    tracking_accuracy = (self.tracking_time_on_target / self.tracking_total_time) * 100
                targets_destroyed = len([t for t in self.tracking_targets if t['health'] <= 0])
                stats_text = f"Time: {remaining:.1f}s | Tracking Accuracy: {tracking_accuracy:.1f}% | On Target: {self.tracking_time_on_target:.1f}s"
            
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
        
        # Draw crosshair in center (your aim point) - REMOVED, using third-party crosshair
        # Crosshair code removed
        
        # Draw all targets
        targets_on_screen = []
        for idx, (target_yaw, target_pitch, spawn_time) in enumerate(self.targets):
            yaw_diff = target_yaw - self.yaw
            pitch_diff = target_pitch - self.pitch
            
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            target_screen_x = center_x + (yaw_diff * self.pixels_per_degree)
            target_screen_y = center_y - (pitch_diff * self.pixels_per_degree)
            
            # Calculate target age
            target_age = current_time - spawn_time
            
            # For random mode: check if target expired
            if self.game_mode == 'random' and target_age >= self.target_lifetime:
                # Target expired, don't add to on_screen list (will be removed)
                self.stats.record_miss()  # Count as miss
                continue
            
            # Calculate shrinking size for random mode
            if self.game_mode == 'random':
                # Start at max size and shrink to min over lifetime
                shrink_progress = target_age / self.target_lifetime  # 0 to 1 over lifetime
                current_target_size = self.target_max_size - (self.target_max_size - self.target_min_size) * shrink_progress
            else:
                current_target_size = self.target_size
            
            margin = current_target_size + 10
            if (-margin <= target_screen_x <= self.canvas_width + margin and 
                -margin <= target_screen_y <= self.canvas_height + margin):
                
                targets_on_screen.append((target_yaw, target_pitch, spawn_time))
                
                # In shapes mode, make active target brighter
                if self.game_mode == 'shapes' and idx == 0:
                    target_color = "#ff4444"  # Bright red for active
                    outline_color = "#ffaa00"  # Orange outline instead of yellow
                    outline_width = 4
                elif self.game_mode == 'random':
                    # Fade from purple to blue over lifetime
                    shrink_progress = target_age / self.target_lifetime  # 0 to 1
                    # Purple (148, 0, 211) to Blue (0, 100, 255)
                    red = int(148 * (1 - shrink_progress))
                    green = int(100 * shrink_progress)
                    blue = int(211 + (255 - 211) * shrink_progress)
                    target_color = f'#{red:02x}{green:02x}{blue:02x}'
                    outline_color = "#ffffff"
                    outline_width = 3
                else:
                    target_color = "#ff0000"
                    outline_color = "#ffffff"
                    outline_width = 3
                
                # Draw target
                self.canvas.create_oval(
                    target_screen_x - current_target_size,
                    target_screen_y - current_target_size,
                    target_screen_x + current_target_size,
                    target_screen_y + current_target_size,
                    fill=target_color,
                    outline=outline_color,
                    width=outline_width,
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
        
        # In shapes mode, also draw the full shape outline (ghost targets)
        if self.game_mode == 'shapes' and self.current_shape:
            for idx, (target_yaw, target_pitch, _) in enumerate(self.current_shape):
                # Skip already hit targets and current target
                if idx < self.current_shape_index:
                    continue
                if idx == self.current_shape_index:
                    continue  # Already drawn above
                
                yaw_diff = target_yaw - self.yaw
                pitch_diff = target_pitch - self.pitch
                
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                
                target_screen_x = center_x + (yaw_diff * self.pixels_per_degree)
                target_screen_y = center_y - (pitch_diff * self.pixels_per_degree)
                
                # Draw ghost target
                if (0 <= target_screen_x <= self.canvas_width and 
                    0 <= target_screen_y <= self.canvas_height):
                    self.canvas.create_oval(
                        target_screen_x - self.target_size,
                        target_screen_y - self.target_size,
                        target_screen_x + self.target_size,
                        target_screen_y + self.target_size,
                        outline="#666666",
                        width=2,
                        tags="ghost_target"
                    )
        
        # Update targets list (for random mode to respawn)
        if self.game_mode == 'random':
            self.targets = targets_on_screen
            while len(self.targets) < self.num_targets:
                self.spawn_target()
        
        # Draw tracking targets
        if self.game_mode == 'tracking':
            for target in self.tracking_targets:
                yaw_diff = target['yaw'] - self.yaw
                pitch_diff = target['pitch'] - self.pitch
                
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                
                target_screen_x = center_x + (yaw_diff * self.pixels_per_degree)
                target_screen_y = center_y - (pitch_diff * self.pixels_per_degree)
                
                # Only draw if on screen
                if (0 <= target_screen_x <= self.canvas_width and 
                    0 <= target_screen_y <= self.canvas_height):
                    
                    # Calculate color based on health (green at 100, yellow at 50, red at 0)
                    health = target['health']
                    if health > 50:
                        # Green to yellow (100->50)
                        ratio = (health - 50) / 50
                        red = int(255 * (1 - ratio))
                        green = 255
                    else:
                        # Yellow to red (50->0)
                        ratio = health / 50
                        red = 255
                        green = int(255 * ratio)
                    target_color = f'#{red:02x}{green:02x}00'
                    
                    # Size based on health (shrinks as health decreases)
                    current_size = target['size'] * (0.5 + 0.5 * (health / 100))
                    
                    # Draw target
                    self.canvas.create_oval(
                        target_screen_x - current_size,
                        target_screen_y - current_size,
                        target_screen_x + current_size,
                        target_screen_y + current_size,
                        fill=target_color,
                        outline="#ffffff",
                        width=2,
                        tags="tracking_target"
                    )
                    
                    # Draw health bar above target
                    bar_width = 50
                    bar_height = 6
                    bar_x = target_screen_x - bar_width / 2
                    bar_y = target_screen_y - current_size - 15
                    
                    # Background
                    self.canvas.create_rectangle(
                        bar_x, bar_y,
                        bar_x + bar_width, bar_y + bar_height,
                        fill="#333333",
                        outline="#ffffff",
                        tags="tracking_target"
                    )
                    
                    # Health fill
                    fill_width = (health / 100) * bar_width
                    if fill_width > 0:
                        self.canvas.create_rectangle(
                            bar_x, bar_y,
                            bar_x + fill_width, bar_y + bar_height,
                            fill=target_color,
                            outline="",
                            tags="tracking_target"
                        )
            
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
        
        if self.game_mode == 'random':
            self.handle_random_mode_shot()
        else:  # shapes mode
            self.handle_shapes_mode_shot()
    
    def handle_random_mode_shot(self):
        """Handle shooting in random targets mode"""
        hit_target = None
        min_distance = float('inf')
        
        # Check each target to see if any were hit
        for i, (target_yaw, target_pitch, spawn_time) in enumerate(self.targets):
            yaw_diff = target_yaw - self.yaw
            pitch_diff = target_pitch - self.pitch
            
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
            
            # Calculate current shrinking size
            target_age = time.time() - spawn_time
            shrink_progress = target_age / self.target_lifetime  # 0 to 1 over lifetime
            current_target_size = self.target_max_size - (self.target_max_size - self.target_min_size) * shrink_progress
            target_angular_size = current_target_size / self.pixels_per_degree
            
            if angular_distance <= target_angular_size:
                if angular_distance < min_distance:
                    min_distance = angular_distance
                    hit_target = (i, spawn_time)
        
        if hit_target is not None:
            target_index, spawn_time = hit_target
            target_yaw, target_pitch, _ = self.targets[target_index]
            reaction_time = time.time() - spawn_time
            self.stats.record_hit(reaction_time)
            
            # Calculate path efficiency from last hit to this hit
            if self.has_last_hit:
                efficiency = self.calculate_path_efficiency(target_yaw, target_pitch)
                if efficiency is not None:
                    self.path_efficiencies.append(efficiency)
            
            # Record this hit position for next path measurement
            self.record_hit_position()
            
            del self.targets[target_index]
            self.spawn_target()
            self.update_stats_display()
        else:
            self.stats.record_miss()
            self.update_stats_display()
    
    def handle_shapes_mode_shot(self):
        """Handle shooting in shape tracking mode"""
        if not self.targets:
            return
        
        # Only check the current target in sequence
        target_yaw, target_pitch, spawn_time = self.targets[0]
        
        yaw_diff = target_yaw - self.yaw
        pitch_diff = target_pitch - self.pitch
        
        while yaw_diff > 180:
            yaw_diff -= 360
        while yaw_diff < -180:
            yaw_diff += 360
        
        angular_distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
        target_angular_size = self.target_size / self.pixels_per_degree
        
        if angular_distance <= target_angular_size:
            # Hit the correct target
            reaction_time = time.time() - spawn_time
            self.stats.record_hit(reaction_time)
            
            # Move to next target in shape
            self.current_shape_index += 1
            
            if self.current_shape_index >= len(self.current_shape):
                # Completed the shape
                self.shapes_completed += 1
                
                if self.shapes_completed >= self.total_shapes:
                    # Finished all shapes
                    self.stop_exercise()
                    return
                
                # Spawn new shape
                self.spawn_shape()
            else:
                # Move to next target in current shape
                self.targets = [self.current_shape[self.current_shape_index]]
            
            self.update_stats_display()
        else:
            # Missed
            self.stats.record_miss()
            self.update_stats_display()
    
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
        
    def cleanup(self):
        """Cleanup resources"""
        self.mouse_locked = False
        self.is_active = False
