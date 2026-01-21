import tkinter as tk
import random
import time
import math
from pynput.mouse import Controller as MouseController

# Try to import pygame for sound effects
try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False
    print("pygame not found - sounds disabled. Install with: pip install pygame")

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
        
        # Store DPI values for recalculation
        self.h_dpi = h_dpi
        self.v_dpi = v_dpi
        
        # Sensitivity presets (cm per 360) with Fortnite sens labels
        self.sensitivity_presets = {
            1: {'cm360': 31.058, 'fn_sens': '5.3%'},
            2: {'cm360': 29.22, 'fn_sens': '5.6%'},
            3: {'cm360': 27.73, 'fn_sens': '5.9%'},
            4: {'cm360': 26.39, 'fn_sens': '6.2%'},
            5: {'cm360': 25.72, 'fn_sens': '6.4%'},
            6: {'cm360': 24.57, 'fn_sens': '6.7%'}
        }
        self.current_preset = 6  # Default to preset 6 (Fortnite 6.7%) - fastest
        
        # Y sensitivity offset options (added to X Fortnite sens %)
        # Higher Fortnite % = faster (less cm/360)
        self.y_sens_options = {
            0: {'label': 'Same', 'offset': None},  # None means match X
            1: {'label': '+1.0', 'offset': 1.0},
            2: {'label': '+1.3', 'offset': 1.3},
            3: {'label': '+1.6', 'offset': 1.6},
            4: {'label': '+1.9', 'offset': 1.9},
            5: {'label': '+2.2', 'offset': 2.2},
            6: {'label': '+2.5', 'offset': 2.5}
        }
        self.current_y_option = 0  # Default to "Same as X"
        
        # Constant for Fortnite sens to cm/360 conversion
        # Fortnite_sens% * cm_per_360 ≈ 164.6
        self.fn_sens_constant = 164.6
        
        # Apply initial sensitivity
        self.apply_sensitivity(self.sensitivity_presets[self.current_preset]['cm360'])
        
        # Virtual camera yaw/pitch (in degrees)
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Multiple targets - list of (yaw, pitch, spawn_time)
        self.targets = []
        self.num_targets = 5  # Number of simultaneous targets
        
        # Game mode
        self.game_mode = None  # Will be 'random' or 'tracking'
        
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
        
        # Hit precision tracking (how close to center)
        self.hit_precisions = []  # List of precision percentages (100% = center)
        
        # Mouse controller
        self.mouse = MouseController()
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        
        # FOV settings for projection
        self.fov = 90  # Field of view in degrees
        self.pixels_per_degree = screen_width / self.fov
        
        # Generate sound effects
        self.sounds = {}
        if SOUND_ENABLED:
            try:
                self.generate_sounds()
            except Exception as e:
                print(f"Sound generation failed: {e} - sounds disabled")
                self.sounds = {}
        
        # Create UI
        self.setup_ui()
    
    def apply_sensitivity(self, cm_per_360):
        """Apply sensitivity setting with optional Y offset"""
        # Horizontal sensitivity calculations
        h_inches_per_360 = cm_per_360 / 2.54
        h_counts_per_360 = h_inches_per_360 * self.h_dpi
        self.h_counts_per_degree = h_counts_per_360 / 360.0
        
        # Vertical sensitivity calculations (apply Y offset if set)
        y_option = self.y_sens_options[self.current_y_option]
        if y_option['offset'] is None:
            # Same as X
            v_cm_per_360 = cm_per_360
        else:
            # Get current X Fortnite sens %
            x_fn_sens = float(self.sensitivity_presets[self.current_preset]['fn_sens'].replace('%', ''))
            # Add offset to get Y Fortnite sens %
            y_fn_sens = x_fn_sens + y_option['offset']
            # Convert to cm/360 (higher % = less cm = faster)
            v_cm_per_360 = self.fn_sens_constant / y_fn_sens
        
        v_inches_per_360 = v_cm_per_360 / 2.54
        v_counts_per_360 = v_inches_per_360 * self.v_dpi
        self.v_counts_per_degree = v_counts_per_360 / 360.0
    
    def generate_sounds(self):
        """Generate procedural sound effects"""
        import numpy as np
        import struct
        
        sample_rate = 22050
        
        def make_sound_from_wave(wave_data):
            """Convert numpy wave to pygame Sound using bytes"""
            # Normalize and convert to 16-bit signed integers
            wave_int = (wave_data * 32767).astype(np.int16)
            # Convert to bytes
            raw_bytes = wave_int.tobytes()
            # Create sound from buffer
            return pygame.mixer.Sound(buffer=raw_bytes)
        
        # Fire sound - short click/pop
        duration = 0.05
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        fire_wave = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 60) * 0.5
        self.sounds['fire'] = make_sound_from_wave(fire_wave)
        self.sounds['fire'].set_volume(0.3)
        
        # Hit sound - satisfying pop with harmonics
        duration = 0.15
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        hit_wave = (np.sin(2 * np.pi * 600 * t) + 
                    0.5 * np.sin(2 * np.pi * 900 * t) +
                    0.3 * np.sin(2 * np.pi * 1200 * t))
        hit_wave = hit_wave * np.exp(-t * 20) * 0.3
        self.sounds['hit'] = make_sound_from_wave(hit_wave)
        self.sounds['hit'].set_volume(0.3)
        
        # Miss/expire sound - descending tone
        duration = 0.2
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        freq = 400 - 200 * t / duration  # Descending from 400 to 200 Hz
        miss_wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10) * 0.3
        self.sounds['miss'] = make_sound_from_wave(miss_wave)
        self.sounds['miss'].set_volume(0.3)
        
        # Tracking target destroyed - rising triumphant sound
        duration = 0.25
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        freq = 500 + 300 * t / duration  # Rising from 500 to 800 Hz
        destroy_wave = (np.sin(2 * np.pi * freq * t) + 
                        0.4 * np.sin(2 * np.pi * freq * 1.5 * t))
        destroy_wave = destroy_wave * np.exp(-t * 8) * 0.3
        self.sounds['destroy'] = make_sound_from_wave(destroy_wave)
        self.sounds['destroy'].set_volume(0.3)
    
    def play_sound(self, sound_name):
        """Play a sound effect (only when game has focus)"""
        if SOUND_ENABLED and sound_name in self.sounds and self.mouse_locked:
            self.sounds[sound_name].play()
    
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
        
        # Sensitivity preset buttons frame (X - horizontal)
        self.sens_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.sens_label = tk.Label(
            self.sens_frame,
            text="X Sens:",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.sens_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create 6 sensitivity preset buttons
        self.sens_buttons = {}
        for preset_num, preset_data in self.sensitivity_presets.items():
            btn = tk.Button(
                self.sens_frame,
                text=f"{preset_data['fn_sens']}",
                command=lambda p=preset_num: self.set_sensitivity_preset(p),
                font=("Arial", 11, "bold"),
                bg="#00aa00" if preset_num == self.current_preset else "#444444",
                fg="white",
                width=6,
                height=1,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.sens_buttons[preset_num] = btn
        
        # Y sensitivity multiplier buttons frame
        self.y_sens_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.y_sens_label = tk.Label(
            self.y_sens_frame,
            text="Y Sens:",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.y_sens_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create Y sensitivity option buttons
        self.y_sens_buttons = {}
        for option_num, option_data in self.y_sens_options.items():
            btn = tk.Button(
                self.y_sens_frame,
                text=option_data['label'],
                command=lambda o=option_num: self.set_y_sensitivity(o),
                font=("Arial", 11, "bold"),
                bg="#00aa00" if option_num == self.current_y_option else "#444444",
                fg="white",
                width=6,
                height=1,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.y_sens_buttons[option_num] = btn
        
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
        
        # Bind M key to return to mode selection
        self.root.bind("<m>", lambda e: self.back_to_mode_select())
        self.root.bind("<M>", lambda e: self.back_to_mode_select())
        
        # Store initial canvas height
        self.canvas_height_inactive = self.screen_height - 200
    
    def set_sensitivity_preset(self, preset_num):
        """Set the sensitivity to a preset value"""
        self.current_preset = preset_num
        cm_value = self.sensitivity_presets[preset_num]['cm360']
        self.apply_sensitivity(cm_value)
        
        # Update button colors
        for num, btn in self.sens_buttons.items():
            if num == preset_num:
                btn.config(bg="#00aa00")  # Highlight selected
            else:
                btn.config(bg="#444444")  # Default color
    
    def set_y_sensitivity(self, option_num):
        """Set the Y sensitivity multiplier"""
        self.current_y_option = option_num
        # Re-apply sensitivity with new Y multiplier
        cm_value = self.sensitivity_presets[self.current_preset]['cm360']
        self.apply_sensitivity(cm_value)
        
        # Update button colors
        for num, btn in self.y_sens_buttons.items():
            if num == option_num:
                btn.config(bg="#00aa00")  # Highlight selected
            else:
                btn.config(bg="#444444")  # Default color
        
    def select_mode(self, mode):
        """Select game mode"""
        self.game_mode = mode
        
        # Hide mode selection
        self.mode_frame.pack_forget()
        
        # Update title
        if mode == 'random':
            self.title.config(text="Random Targets Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Press START to begin | M for menu | ESC to exit")
        elif mode == 'tracking':
            self.title.config(text="Tracking Practice Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Keep crosshair on targets | 60 seconds | M for menu | ESC to exit")
        
        # Show control buttons
        self.button_frame.pack(pady=10)
        
        # Show sensitivity frames
        self.sens_frame.pack(pady=5)
        self.y_sens_frame.pack(pady=5)
        
        # Show canvas
        self.canvas.pack(pady=5)
        
    def back_to_mode_select(self):
        """Return to mode selection"""
        if self.is_active:
            self.stop_exercise()
        
        self.game_mode = None
        self.button_frame.pack_forget()
        self.sens_frame.pack_forget()
        self.y_sens_frame.pack_forget()
        self.canvas.pack_forget()
        self.title.config(text="FPS Aim Trainer - Select Your Mode", font=("Arial", 24, "bold"))
        self.stats_label.config(text="Select a mode to begin")
        self.mode_frame.pack(pady=20)
        
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
        self.sens_frame.pack_forget()
        self.y_sens_frame.pack_forget()
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
        self.hit_precisions = []  # Reset hit precision tracking
        
        # Store last mouse position for delta calculation
        pos = self.mouse.position
        self.last_mouse_x = pos[0]
        self.last_mouse_y = pos[1]
        
        # Spawn initial targets based on mode
        if self.game_mode == 'random':
            for _ in range(self.num_targets):
                self.spawn_target()
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
        self.sens_frame.pack(pady=5)
        self.y_sens_frame.pack(pady=5)
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
        self.path_efficiencies = []
        self.hit_precisions = []
        self.has_last_hit = False
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
    
    def get_average_hit_precision(self):
        """Get average hit precision (100% = center of target)"""
        if not self.hit_precisions:
            return 0.0
        return sum(self.hit_precisions) / len(self.hit_precisions)
    
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
        
        # Horizontal velocity (left or right)
        speed = random.uniform(0.9, 2.4)  # Degrees per second
        direction = random.choice([-1, 1])  # Left or right
        vel_yaw = direction * speed
        vel_pitch = random.uniform(-0.3, 0.3)  # Slight vertical drift
        
        # Target properties: yaw, pitch, vel_yaw, vel_pitch, health (0-400), size
        target = {
            'yaw': target_yaw,
            'pitch': target_pitch,
            'vel_yaw': vel_yaw,
            'vel_pitch': vel_pitch,
            'health': 400.0,
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
            
            # Randomly swap horizontal direction
            if random.random() < 0.004:  # 0.4% chance per frame
                target['vel_yaw'] *= -1  # Reverse horizontal direction
                target['vel_pitch'] = random.uniform(-0.3, 0.3)  # New slight vertical drift
        
        # Remove destroyed targets and spawn new ones
        for target in targets_to_remove:
            # Play destroy sound
            self.play_sound('destroy')
            
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
                    stats_text += f" | Path: {avg_efficiency:.1f}%"
                avg_precision = self.get_average_hit_precision()
                if avg_precision > 0:
                    stats_text += f" | Precision: {avg_precision:.1f}%"
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
            
            # Show current sensitivity (X and Y)
            current_fn_sens = self.sensitivity_presets[self.current_preset]['fn_sens']
            x_fn_val = float(current_fn_sens.replace('%', ''))
            y_option = self.y_sens_options[self.current_y_option]
            if y_option['offset'] is None:
                y_display = "Same"
            else:
                y_fn_val = x_fn_val + y_option['offset']
                y_display = f"{y_fn_val:.1f}%"
            stats_text += f" | X: {current_fn_sens} Y: {y_display}"
            
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
                # Play miss sound
                self.play_sound('miss')
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
                
                if self.game_mode == 'random':
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
                    
                    # Calculate color based on health (green at 400, yellow at 200, red at 0)
                    health = target['health']
                    if health > 200:
                        # Green to yellow (400->200)
                        ratio = (health - 200) / 200
                        red = int(255 * (1 - ratio))
                        green = 255
                    else:
                        # Yellow to red (200->0)
                        ratio = health / 200
                        red = 255
                        green = int(255 * ratio)
                    target_color = f'#{red:02x}{green:02x}00'
                    
                    # Size based on health (shrinks as health decreases)
                    current_size = target['size'] * (0.5 + 0.5 * (health / 400))
                    
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
                    fill_width = (health / 400) * bar_width
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
        
        # Play fire sound
        self.play_sound('fire')
        
        if self.game_mode == 'random':
            self.handle_random_mode_shot()
    
    def handle_random_mode_shot(self):
        """Handle shooting in random targets mode"""
        hit_target = None
        min_distance = float('inf')
        hit_target_angular_size = 0
        
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
                    hit_target_angular_size = target_angular_size
        
        if hit_target is not None:
            target_index, spawn_time = hit_target
            target_yaw, target_pitch, _ = self.targets[target_index]
            reaction_time = time.time() - spawn_time
            self.stats.record_hit(reaction_time)
            
            # Calculate hit precision (100% = center, 0% = edge)
            if hit_target_angular_size > 0:
                precision = (1 - (min_distance / hit_target_angular_size)) * 100
                self.hit_precisions.append(precision)
            
            # Play hit sound
            self.play_sound('hit')
            
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
