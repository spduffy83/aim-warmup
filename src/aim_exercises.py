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
        self.target_size = 35  # Base target size (at spawn)
        self.target_min_size = 5  # Minimum size before disappearing
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
        self.current_preset = 1  # Default to preset 1 (Fortnite 5.3%)
        
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
        self.current_y_option = 6  # Default to "+2.5"
        
        # Constant for Fortnite sens to cm/360 conversion
        # Fortnite_sens% * cm_per_360 ≈ 164.6
        self.fn_sens_constant = 164.6
        
        # Current sensitivity values (will be set properly after UI creation)
        self.current_x_sens = 5.3
        self.current_y_sens = 7.6  # Default Y sensitivity
        
        # Virtual camera yaw/pitch (in degrees)
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Multiple targets - list of {yaw, pitch, spawn_time}
        self.targets = []
        self.num_targets = 3  # Number of simultaneous targets
        
        # Game mode
        self.game_mode = None  # Will be 'random' or 'tracking'
        
        # Tracking mode variables
        self.tracking_targets = []  # List of tracking target objects
        self.tracking_score = 0
        self.tracking_time_on_target = 0.0
        self.tracking_total_time = 0.0
        self.tracking_start_time = 0
        self.tracking_duration = 60  # 60 second rounds
        
        # Session timer (counts up while active and focused)
        self.session_timer = 0.0  # Total elapsed time in seconds
        self.last_timer_update = 0  # Timestamp of last timer update
        
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
        self.x_efficiencies = []  # X-axis (yaw) efficiency percentages
        self.y_efficiencies = []  # Y-axis (pitch) efficiency percentages
        self.has_last_hit = False  # Whether we have a previous hit to measure from
        
        # Final approach analysis tracking
        self.x_overshoots = []  # List of X overshoot counts per target
        self.y_overshoots = []  # List of Y overshoot counts per target
        self.x_micro_adjustments = []  # List of X micro-adjustment counts
        self.y_micro_adjustments = []  # List of Y micro-adjustment counts
        self.approach_analysis_window = 0.3  # Analyze last 30% of path
        
        # Last shot analysis (for debug display)
        self.last_shot_type = ""  # "HIT" or "MISS"
        self.last_shot_analysis = None  # Last approach analysis result
        
        # Debug mode variables
        self.debug_frozen = False
        self.debug_freeze_time = 0
        self.debug_analysis_points = []
        self.debug_reversal_points = []
        self.debug_pause_points = []
        self.debug_x_undershoot_points = []  # X axis undershoots
        self.debug_y_undershoot_points = []  # Y axis undershoots
        self.debug_x_overshoot_pos = None  # Position of max X overshoot
        self.debug_y_overshoot_pos = None  # Position of max Y overshoot
        
        # Last shot analysis for detailed display
        self.last_shot_analysis = None  # Stores the most recent shot's approach data
        self.last_shot_was_hit = False  # Whether last shot was a hit or miss
        
        # Crosshair styles
        self.crosshair_styles = {
            0: {'name': 'None', 'type': 'none', 'outline': False},
            1: {'name': 'Cross', 'type': 'cross', 'outline': False},
            2: {'name': 'Cross+', 'type': 'cross', 'outline': True},
            3: {'name': 'Square', 'type': 'square', 'outline': False},
            4: {'name': 'Square+', 'type': 'square', 'outline': True},
            5: {'name': 'Circle', 'type': 'circle', 'outline': False},
            6: {'name': 'Circle+', 'type': 'circle', 'outline': True}
        }
        self.current_crosshair = 0  # Default to no crosshair
        self.crosshair_color = "#39ff14"  # Neon green
        self.crosshair_outline_color = "#ff0000"  # Red outline
        self.crosshair_size = 7  # Size in pixels (75% of original 10)
        self.crosshair_thickness = 2  # Line thickness
        self.crosshair_outline_thickness = 1  # Outline thickness
        
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
    
    def apply_sensitivity(self, x_fn_sens=None, y_fn_sens=None):
        """Apply sensitivity setting using Fortnite sensitivity percentages"""
        # Get values from entry fields if not provided
        if x_fn_sens is None:
            try:
                x_fn_sens = float(self.x_sens_var.get())
            except (ValueError, AttributeError):
                x_fn_sens = 5.3  # Default
        
        if y_fn_sens is None:
            try:
                y_fn_sens = float(self.y_sens_var.get())
            except (ValueError, AttributeError):
                y_fn_sens = x_fn_sens  # Default to same as X
        
        # Clamp values to reasonable range (1% to 20%)
        x_fn_sens = max(1.0, min(20.0, x_fn_sens))
        y_fn_sens = max(1.0, min(20.0, y_fn_sens))
        
        # Convert Fortnite sens % to cm/360
        # Fortnite_sens% * cm_per_360 ≈ 164.6
        x_cm_per_360 = self.fn_sens_constant / x_fn_sens
        y_cm_per_360 = self.fn_sens_constant / y_fn_sens
        
        # Horizontal sensitivity calculations
        h_inches_per_360 = x_cm_per_360 / 2.54
        h_counts_per_360 = h_inches_per_360 * self.h_dpi
        self.h_counts_per_degree = h_counts_per_360 / 360.0
        
        # Vertical sensitivity calculations
        v_inches_per_360 = y_cm_per_360 / 2.54
        v_counts_per_360 = v_inches_per_360 * self.v_dpi
        self.v_counts_per_degree = v_counts_per_360 / 360.0
        
        # Store current values
        self.current_x_sens = x_fn_sens
        self.current_y_sens = y_fn_sens
    
    def apply_custom_sensitivity(self):
        """Apply sensitivity from the entry fields"""
        try:
            x_val = float(self.x_sens_var.get())
            # Round to 1 decimal place and update display
            x_val = round(x_val, 1)
            self.x_sens_var.set(f"{x_val:.1f}")
        except ValueError:
            x_val = 5.3
            self.x_sens_var.set("5.3")
        
        try:
            y_val = float(self.y_sens_var.get())
            # Round to 1 decimal place and update display
            y_val = round(y_val, 1)
            self.y_sens_var.set(f"{y_val:.1f}")
        except ValueError:
            y_val = x_val
            self.y_sens_var.set(f"{y_val:.1f}")
        
        self.apply_sensitivity(x_val, y_val)
        
        # Clear preset button highlights since we're using custom values
        for btn in self.sens_buttons.values():
            btn.config(bg="#444444")
        for btn in self.y_sens_buttons.values():
            btn.config(bg="#444444")
    
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
            text="RANDOM TARGETS\n\nClick shrinking targets\n3 active at once",
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
        
        # Debug test mode button
        self.debug_mode_btn = tk.Button(
            self.mode_frame,
            text="DEBUG TEST\n\nSingle target, visual path\nTest approach metrics",
            command=lambda: self.select_mode('debug'),
            font=("Arial", 14, "bold"),
            bg="#aa5500",
            fg="white",
            width=25,
            height=5,
            relief=tk.FLAT
        )
        self.debug_mode_btn.pack(side=tk.LEFT, padx=15)
        
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
        
        # Sensitivity controls frame (contains both X and Y)
        self.sens_frame = tk.Frame(self.root, bg="#1a1a1a")
        
        # X Sensitivity row
        self.x_sens_row = tk.Frame(self.sens_frame, bg="#1a1a1a")
        self.x_sens_row.pack(pady=3)
        
        self.sens_label = tk.Label(
            self.x_sens_row,
            text="X Sens:",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.sens_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # X sensitivity numeric entry
        self.x_sens_var = tk.StringVar(value="5.3")
        self.x_sens_entry = tk.Entry(
            self.x_sens_row,
            textvariable=self.x_sens_var,
            font=("Arial", 12, "bold"),
            width=6,
            justify=tk.CENTER,
            bg="#333333",
            fg="#00ff00",
            insertbackground="#00ff00",
            relief=tk.FLAT
        )
        self.x_sens_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.x_sens_entry.bind('<Return>', lambda e: self.apply_custom_sensitivity())
        self.x_sens_entry.bind('<FocusOut>', lambda e: self.apply_custom_sensitivity())
        
        self.x_sens_percent = tk.Label(
            self.x_sens_row,
            text="%",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.x_sens_percent.pack(side=tk.LEFT, padx=(0, 15))
        
        # X sensitivity preset buttons
        self.sens_buttons = {}
        for preset_num, preset_data in self.sensitivity_presets.items():
            btn = tk.Button(
                self.x_sens_row,
                text=f"{preset_data['fn_sens']}",
                command=lambda p=preset_num: self.set_sensitivity_preset(p),
                font=("Arial", 10),
                bg="#444444",
                fg="white",
                width=5,
                height=1,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.sens_buttons[preset_num] = btn
        
        # Y Sensitivity row
        self.y_sens_row = tk.Frame(self.sens_frame, bg="#1a1a1a")
        self.y_sens_row.pack(pady=3)
        
        self.y_sens_label = tk.Label(
            self.y_sens_row,
            text="Y Sens:",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.y_sens_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Y sensitivity numeric entry
        self.y_sens_var = tk.StringVar(value="7.6")
        self.y_sens_entry = tk.Entry(
            self.y_sens_row,
            textvariable=self.y_sens_var,
            font=("Arial", 12, "bold"),
            width=6,
            justify=tk.CENTER,
            bg="#333333",
            fg="#00ff00",
            insertbackground="#00ff00",
            relief=tk.FLAT
        )
        self.y_sens_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.y_sens_entry.bind('<Return>', lambda e: self.apply_custom_sensitivity())
        self.y_sens_entry.bind('<FocusOut>', lambda e: self.apply_custom_sensitivity())
        
        self.y_sens_percent = tk.Label(
            self.y_sens_row,
            text="%",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.y_sens_percent.pack(side=tk.LEFT, padx=(0, 15))
        
        # Y sensitivity quick offset buttons
        self.y_sens_buttons = {}
        for option_num, option_data in self.y_sens_options.items():
            btn = tk.Button(
                self.y_sens_row,
                text=option_data['label'],
                command=lambda o=option_num: self.set_y_sensitivity_offset(o),
                font=("Arial", 10),
                bg="#444444",
                fg="white",
                width=5,
                height=1,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.y_sens_buttons[option_num] = btn
        
        # We no longer need the separate y_sens_frame
        self.y_sens_frame = None
        
        # Crosshair style buttons frame
        self.crosshair_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.crosshair_label = tk.Label(
            self.crosshair_frame,
            text="Crosshair:",
            font=("Arial", 11),
            bg="#1a1a1a",
            fg="#aaaaaa"
        )
        self.crosshair_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create crosshair style buttons
        self.crosshair_buttons = {}
        for style_num, style_data in self.crosshair_styles.items():
            btn = tk.Button(
                self.crosshair_frame,
                text=style_data['name'],
                command=lambda s=style_num: self.set_crosshair_style(s),
                font=("Arial", 11, "bold"),
                bg="#00aa00" if style_num == self.current_crosshair else "#444444",
                fg="white",
                width=7,
                height=1,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.crosshair_buttons[style_num] = btn
        
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
        
        # Apply initial sensitivity from entry field values
        self.apply_custom_sensitivity()
    
    def set_crosshair_style(self, style_num):
        """Set the crosshair style"""
        self.current_crosshair = style_num
        
        # Update button colors
        for num, btn in self.crosshair_buttons.items():
            if num == style_num:
                btn.config(bg="#00aa00")  # Highlight selected
            else:
                btn.config(bg="#444444")  # Default color
    
    def draw_crosshair(self, center_x, center_y):
        """Draw the crosshair at the specified position"""
        style = self.crosshair_styles[self.current_crosshair]
        
        # No crosshair option
        if style['type'] == 'none':
            return
        
        size = self.crosshair_size
        thickness = self.crosshair_thickness
        outline_thickness = self.crosshair_outline_thickness
        color = self.crosshair_color
        outline_color = self.crosshair_outline_color
        has_outline = style['outline']
        
        if style['type'] == 'cross':
            # Draw cross crosshair
            if has_outline:
                # Draw red outline first (slightly larger)
                outline_size = size + outline_thickness
                outline_width = thickness + (outline_thickness * 2)
                # Horizontal outline
                self.canvas.create_line(
                    center_x - outline_size, center_y,
                    center_x + outline_size, center_y,
                    fill=outline_color,
                    width=outline_width,
                    tags="crosshair"
                )
                # Vertical outline
                self.canvas.create_line(
                    center_x, center_y - outline_size,
                    center_x, center_y + outline_size,
                    fill=outline_color,
                    width=outline_width,
                    tags="crosshair"
                )
            
            # Draw green cross
            # Horizontal line
            self.canvas.create_line(
                center_x - size, center_y,
                center_x + size, center_y,
                fill=color,
                width=thickness,
                tags="crosshair"
            )
            # Vertical line
            self.canvas.create_line(
                center_x, center_y - size,
                center_x, center_y + size,
                fill=color,
                width=thickness,
                tags="crosshair"
            )
        
        elif style['type'] == 'square':
            # Draw square crosshair
            half_size = size
            
            if has_outline:
                # Draw red outline first (slightly larger)
                outline_offset = outline_thickness
                self.canvas.create_rectangle(
                    center_x - half_size - outline_offset,
                    center_y - half_size - outline_offset,
                    center_x + half_size + outline_offset,
                    center_y + half_size + outline_offset,
                    outline=outline_color,
                    width=thickness + outline_thickness,
                    tags="crosshair"
                )
            
            # Draw green square
            self.canvas.create_rectangle(
                center_x - half_size,
                center_y - half_size,
                center_x + half_size,
                center_y + half_size,
                outline=color,
                width=thickness,
                tags="crosshair"
            )
        
        elif style['type'] == 'circle':
            # Draw circle crosshair (hollow)
            radius = size
            
            if has_outline:
                # Draw red outline first (slightly larger)
                outline_radius = radius + outline_thickness
                self.canvas.create_oval(
                    center_x - outline_radius,
                    center_y - outline_radius,
                    center_x + outline_radius,
                    center_y + outline_radius,
                    outline=outline_color,
                    width=thickness + outline_thickness,
                    tags="crosshair"
                )
            
            # Draw green circle
            self.canvas.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                outline=color,
                width=thickness,
                tags="crosshair"
            )
    
    def set_sensitivity_preset(self, preset_num):
        """Set the sensitivity to a preset value"""
        self.current_preset = preset_num
        fn_sens = float(self.sensitivity_presets[preset_num]['fn_sens'].replace('%', ''))
        
        # Update entry field
        self.x_sens_var.set(f"{fn_sens:.1f}")
        
        # Highlight selected preset button
        for num, btn in self.sens_buttons.items():
            if num == preset_num:
                btn.config(bg="#00aa00")
            else:
                btn.config(bg="#444444")
        
        # Apply sensitivity
        self.apply_custom_sensitivity()
    
    def set_y_sensitivity_offset(self, option_num):
        """Set the Y sensitivity using offset from current X"""
        try:
            x_val = float(self.x_sens_var.get())
        except ValueError:
            x_val = 5.3
        
        y_option = self.y_sens_options[option_num]
        if y_option['offset'] is None:
            y_val = x_val  # Same as X
        else:
            y_val = x_val + y_option['offset']
        
        # Update Y entry field
        self.y_sens_var.set(f"{y_val:.1f}")
        
        # Highlight selected offset button
        for num, btn in self.y_sens_buttons.items():
            if num == option_num:
                btn.config(bg="#00aa00")
            else:
                btn.config(bg="#444444")
        
        # Apply sensitivity
        self.apply_custom_sensitivity()
        
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
        elif mode == 'debug':
            self.title.config(text="Debug Test Mode", font=("Arial", 20, "bold"))
            self.stats_label.config(text="Single target | Path visualization | SPACE to spawn new target | M for menu")
        
        # Show control buttons
        self.button_frame.pack(pady=10)
        
        # Show sensitivity frame (contains both X and Y)
        self.sens_frame.pack(pady=5)
        
        # Show crosshair frame
        self.crosshair_frame.pack(pady=5)
        
        # Show canvas
        self.canvas.pack(pady=5)
        
    def back_to_mode_select(self):
        """Return to mode selection"""
        if self.is_active:
            self.stop_exercise()
        
        self.game_mode = None
        self.button_frame.pack_forget()
        self.sens_frame.pack_forget()
        self.crosshair_frame.pack_forget()
        self.canvas.pack_forget()
        self.title.config(text="FPS Aim Trainer - Select Your Mode", font=("Arial", 24, "bold"))
        self.stats_label.config(text="Select a mode to begin")
        self.mode_frame.pack(pady=20)
        
    def start_exercise(self):
        """Start the aim exercise"""
        if self.game_mode is None:
            return
        
        # Apply current sensitivity from entry fields before starting
        self.apply_custom_sensitivity()
            
        self.is_active = True
        self.mouse_locked = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Hide UI elements
        self.title.pack_forget()
        self.button_frame.pack_forget()
        self.sens_frame.pack_forget()
        self.crosshair_frame.pack_forget()
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
        self.x_efficiencies = []  # Reset X efficiency tracking
        self.y_efficiencies = []  # Reset Y efficiency tracking
        self.path_points = []
        self.has_last_hit = False
        self.hit_precisions = []  # Reset hit precision tracking
        
        # Reset approach analysis tracking
        self.x_overshoots = []
        self.y_overshoots = []
        self.x_micro_adjustments = []
        self.y_micro_adjustments = []
        self.last_shot_analysis = None
        self.last_shot_was_hit = False
        self.last_shot_type = ""
        
        # Reset debug/analysis markers (used in both debug and random modes)
        self.debug_x_overshoot_pos = None
        self.debug_y_overshoot_pos = None
        self.debug_x_undershoot_points = []
        self.debug_y_undershoot_points = []
        self.debug_pause_points = []
        self.debug_reversal_points = []
        self.debug_analysis_points = []
        
        # Reset session timer
        self.session_timer = 0.0
        self.last_timer_update = time.time()
        
        # Store last mouse position for delta calculation
        pos = self.mouse.position
        self.last_mouse_x = pos[0]
        self.last_mouse_y = pos[1]
        
        # Spawn initial targets based on mode
        if self.game_mode == 'random':
            # Spawn 3 purple targets
            self.targets = []
            for i in range(self.num_targets):
                self.spawn_target_at_random_position()
        elif self.game_mode == 'tracking':
            self.tracking_start_time = time.time()
            self.tracking_time_on_target = 0.0
            self.tracking_total_time = 0.0
            self.tracking_targets = []
            self.spawn_tracking_target()
            self.spawn_tracking_target()  # Start with 2 targets
        elif self.game_mode == 'debug':
            # Debug mode: single target, no expiration
            self.debug_frozen = False  # Whether we're frozen showing results
            self.debug_freeze_time = 0
            self.debug_analysis_points = []  # Points in the analysis window
            self.debug_reversal_points = []  # Where reversals were detected
            self.debug_pause_points = []  # Where pauses were detected
            self.debug_x_undershoot_points = []  # X axis undershoots
            self.debug_y_undershoot_points = []  # Y axis undershoots
            self.spawn_debug_target()
            # Bind space to spawn new target
            self.root.bind("<space>", lambda e: self.spawn_debug_target() if (self.is_active and self.game_mode == 'debug') else None)
        
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
        self.crosshair_frame.pack(pady=5)
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
        self.x_efficiencies = []
        self.y_efficiencies = []
        self.hit_precisions = []
        self.has_last_hit = False
        self.x_overshoots = []
        self.y_overshoots = []
        self.x_micro_adjustments = []
        self.y_micro_adjustments = []
        self.update_stats_display()
        
    def lock_mouse_loop(self):
        """Continuously recenter mouse and update view"""
        if self.is_active:
            current_time = time.time()
            
            # Update session timer only when active and mouse is locked (window focused)
            if self.mouse_locked:
                delta = current_time - self.last_timer_update
                self.session_timer += delta
            self.last_timer_update = current_time
            
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
                
                # Clamp pitch to screen bounds (small range)
                max_pitch = (self.canvas_height / 2) / self.pixels_per_degree * 0.5
                self.pitch = max(-max_pitch, min(max_pitch, self.pitch))

                # Clamp yaw to screen bounds (small range) instead of wrapping 360
                max_yaw = (self.canvas_width / 2) / self.pixels_per_degree * 0.5
                self.yaw = max(-max_yaw, min(max_yaw, self.yaw))
                
                # Add trail point every few milliseconds
                current_time = time.time()
                if current_time - self.last_trail_time > 0.01:  # Every 10ms
                    self.trail_points.append((self.yaw, self.pitch, current_time))
                    self.last_trail_time = current_time
                    
                    # Track path for efficiency calculation (random and debug modes)
                    if (self.game_mode == 'random' or self.game_mode == 'debug') and self.has_last_hit:
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
    
    def calculate_axis_efficiency(self, target_yaw, target_pitch):
        """Calculate X and Y axis efficiency separately"""
        if len(self.path_points) < 2 or not self.has_last_hit:
            return None, None  # Not enough data
        
        # Calculate direct X (yaw) distance from last hit to target
        direct_x = target_yaw - self.last_hit_yaw
        # Handle yaw wraparound
        while direct_x > 180:
            direct_x -= 360
        while direct_x < -180:
            direct_x += 360
        direct_x = abs(direct_x)
        
        # Calculate direct Y (pitch) distance
        direct_y = abs(target_pitch - self.last_hit_pitch)
        
        # Skip if movement was too small on either axis
        min_movement = 0.5  # Minimum degrees to consider
        
        # Calculate actual X and Y distances traveled
        actual_x = 0.0
        actual_y = 0.0
        
        for i in range(1, len(self.path_points)):
            yaw1, pitch1 = self.path_points[i - 1]
            yaw2, pitch2 = self.path_points[i]
            
            # Handle yaw wraparound for X movement
            seg_x = yaw2 - yaw1
            while seg_x > 180:
                seg_x -= 360
            while seg_x < -180:
                seg_x += 360
            actual_x += abs(seg_x)
            
            # Y movement (no wraparound needed)
            actual_y += abs(pitch2 - pitch1)
        
        # Calculate X efficiency
        x_efficiency = None
        if direct_x >= min_movement and actual_x > 0:
            x_efficiency = (direct_x / actual_x) * 100
            x_efficiency = min(x_efficiency, 100.0)  # Cap at 100%
        
        # Calculate Y efficiency
        y_efficiency = None
        if direct_y >= min_movement and actual_y > 0:
            y_efficiency = (direct_y / actual_y) * 100
            y_efficiency = min(y_efficiency, 100.0)  # Cap at 100%
        
        return x_efficiency, y_efficiency
    
    def analyze_final_approach(self, target_yaw, target_pitch, capture_debug=False):
        """
        Analyze the final approach to the target to detect overshoot/undershoot patterns.
        
        Returns dict with:
        - x_reversals: Number of X direction changes near target (overshoot indicator)
        - y_reversals: Number of Y direction changes near target (overshoot indicator)
        - x_micro_adjustments: Number of distinct movement pulses on X (undershoot indicator)
        - y_micro_adjustments: Number of distinct movement pulses on Y (undershoot indicator)
        - x_max_overshoot: Maximum distance past target on X axis
        - y_max_overshoot: Maximum distance past target on Y axis
        
        If capture_debug=True, also populates self.debug_*_points lists for visualization.
        """
        if len(self.path_points) < 5 or not self.has_last_hit:
            return None
        
        # Analyze the final portion of the path (last 30%) for reversals/pulses
        analysis_start = int(len(self.path_points) * (1 - self.approach_analysis_window))
        final_path = self.path_points[analysis_start:]
        
        if len(final_path) < 3:
            return None
        
        # Clear and capture debug points if requested
        if capture_debug:
            self.debug_analysis_points = final_path.copy()
            self.debug_reversal_points = []
            self.debug_pause_points = []
            self.debug_x_undershoot_points = []
            self.debug_y_undershoot_points = []
            self.debug_x_overshoot_pos = None
            self.debug_y_overshoot_pos = None
        
        # Initialize counters
        x_reversals = 0
        y_reversals = 0
        x_max_overshoot = 0.0
        y_max_overshoot = 0.0
        x_max_overshoot_pos = None
        y_max_overshoot_pos = None
        
        # Movement pulse detection
        # A "pulse" is a period of movement after a pause
        # More pulses = more stop-and-go = undershooting
        pause_threshold = 0.01  # Degrees - below this is considered "stopped"
        move_threshold = 0.02   # Degrees - above this is considered "moving"
        
        x_is_moving = False
        y_is_moving = False
        x_pulses = 0
        y_pulses = 0
        x_was_paused = False  # Track if we've seen a pause
        y_was_paused = False
        
        last_x_dir = 0
        last_y_dir = 0
        
        # Calculate target direction from START of entire path (not analysis window)
        # This is critical for overshoot detection
        path_start_yaw, path_start_pitch = self.path_points[0]
        
        # Handle yaw wraparound for target direction
        target_x_diff = target_yaw - path_start_yaw
        while target_x_diff > 180:
            target_x_diff -= 360
        while target_x_diff < -180:
            target_x_diff += 360
        target_x_dir = 1 if target_x_diff > 0 else -1
        
        target_y_diff = target_pitch - path_start_pitch
        target_y_dir = 1 if target_y_diff > 0 else -1
        
        # Calculate target angular radius (half-size in degrees)
        # Use current size based on age for more accurate hit detection
        target_angular_radius = self.target_size / self.pixels_per_degree
        
        # Calculate target edges based on approach direction
        # If approaching from left (target_x_dir > 0), the far edge is target_yaw + radius
        # If approaching from right (target_x_dir < 0), the far edge is target_yaw - radius
        target_x_far_edge = target_yaw + (target_x_dir * target_angular_radius)
        target_y_far_edge = target_pitch + (target_y_dir * target_angular_radius)
        
        # First pass: scan ENTIRE path for max overshoot past target EDGE (track X and Y separately)
        for i in range(1, len(self.path_points)):
            curr_yaw, curr_pitch = self.path_points[i]
            
            # Check for X overshoot (crossed past target's far horizontal edge)
            curr_x_diff = target_x_far_edge - curr_yaw
            while curr_x_diff > 180:
                curr_x_diff -= 360
            while curr_x_diff < -180:
                curr_x_diff += 360
            
            # Overshoot if we're on the opposite side of the FAR EDGE from where we started
            curr_x_side = 1 if curr_x_diff > 0 else -1
            if curr_x_side != target_x_dir:
                # We crossed past the far edge - this is overshoot
                overshoot_dist = abs(curr_x_diff)
                if overshoot_dist > x_max_overshoot:
                    x_max_overshoot = overshoot_dist
                    x_max_overshoot_pos = (curr_yaw, curr_pitch)
            
            # Check for Y overshoot (crossed past target's far vertical edge)
            curr_y_diff = target_y_far_edge - curr_pitch
            curr_y_side = 1 if curr_y_diff > 0 else -1
            if curr_y_side != target_y_dir:
                # We crossed past the far edge - this is overshoot
                overshoot_dist = abs(curr_y_diff)
                if overshoot_dist > y_max_overshoot:
                    y_max_overshoot = overshoot_dist
                    y_max_overshoot_pos = (curr_yaw, curr_pitch)
        
        # Use start of analysis window for reversal/pulse direction
        start_yaw, start_pitch = final_path[0]
        
        # Analyze the final portion of the path for both reversals and undershoots
        for i in range(1, len(final_path)):
            prev_yaw, prev_pitch = final_path[i - 1]
            curr_yaw, curr_pitch = final_path[i]
            
            # Calculate movement deltas
            dx = curr_yaw - prev_yaw
            while dx > 180:
                dx -= 360
            while dx < -180:
                dx += 360
            dy = curr_pitch - prev_pitch
            
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            
            # Check if cursor has reached the target's NEAR edge yet
            curr_x_diff_to_near = (target_yaw - target_x_dir * target_angular_radius) - curr_yaw
            while curr_x_diff_to_near > 180:
                curr_x_diff_to_near -= 360
            while curr_x_diff_to_near < -180:
                curr_x_diff_to_near += 360
            curr_x_side_of_near = 1 if curr_x_diff_to_near > 0 else -1
            x_reached_target = (curr_x_side_of_near != target_x_dir)
            
            curr_y_diff_to_near = (target_pitch - target_y_dir * target_angular_radius) - curr_pitch
            curr_y_side_of_near = 1 if curr_y_diff_to_near > 0 else -1
            y_reached_target = (curr_y_side_of_near != target_y_dir)
            
            # Determine movement direction
            curr_x_dir = 1 if dx > 0.01 else (-1 if dx < -0.01 else 0)
            curr_y_dir = 1 if dy > 0.01 else (-1 if dy < -0.01 else 0)
            
            # Detect X reversals (direction change)
            if curr_x_dir != 0 and last_x_dir != 0 and curr_x_dir != last_x_dir:
                x_reversals += 1
                if capture_debug:
                    self.debug_reversal_points.append((prev_yaw, prev_pitch))
            
            # Detect Y reversals
            if curr_y_dir != 0 and last_y_dir != 0 and curr_y_dir != last_y_dir:
                y_reversals += 1
                if capture_debug:
                    self.debug_reversal_points.append((prev_yaw, prev_pitch))
            
            # Detect X movement pulses (stop-and-go pattern) - ONLY before reaching target
            if abs_dx < pause_threshold:
                # We've stopped on X axis
                if x_is_moving and capture_debug and not x_reached_target:
                    self.debug_pause_points.append((curr_yaw, curr_pitch))
                x_is_moving = False
                if not x_reached_target:
                    x_was_paused = True
            elif abs_dx > move_threshold:
                # We're moving on X axis
                if not x_is_moving:
                    # Just started a new movement pulse - only count if before reaching target
                    if not x_reached_target:
                        x_pulses += 1
                        if capture_debug and x_was_paused:
                            self.debug_x_undershoot_points.append((curr_yaw, curr_pitch))
                x_is_moving = True
            
            # Detect Y movement pulses - ONLY before reaching target
            if abs_dy < pause_threshold:
                if y_is_moving and capture_debug and not y_reached_target:
                    self.debug_pause_points.append((curr_yaw, curr_pitch))
                y_is_moving = False
                if not y_reached_target:
                    y_was_paused = True
            elif abs_dy > move_threshold:
                if not y_is_moving:
                    if not y_reached_target:
                        y_pulses += 1
                        if capture_debug and y_was_paused:
                            self.debug_y_undershoot_points.append((curr_yaw, curr_pitch))
                y_is_moving = True
            
            # Update last direction
            if curr_x_dir != 0:
                last_x_dir = curr_x_dir
            if curr_y_dir != 0:
                last_y_dir = curr_y_dir
        
        # Subtract 1 from pulses (the initial movement toward target is expected)
        # More than 1 pulse = had to restart movement = undershooting
        x_micro_adjustments = max(0, x_pulses - 1)
        y_micro_adjustments = max(0, y_pulses - 1)
        
        # Capture max overshoot positions for debug visualization (store separately)
        if capture_debug:
            self.debug_x_overshoot_pos = x_max_overshoot_pos
            self.debug_y_overshoot_pos = y_max_overshoot_pos
        
        return {
            'x_reversals': x_reversals,
            'y_reversals': y_reversals,
            'x_micro_adjustments': x_micro_adjustments,
            'y_micro_adjustments': y_micro_adjustments,
            'x_max_overshoot': x_max_overshoot,
            'y_max_overshoot': y_max_overshoot
        }
    
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
    
    def get_average_x_efficiency(self):
        """Get average X-axis efficiency"""
        if not self.x_efficiencies:
            return 0.0
        return sum(self.x_efficiencies) / len(self.x_efficiencies)
    
    def get_average_y_efficiency(self):
        """Get average Y-axis efficiency"""
        if not self.y_efficiencies:
            return 0.0
        return sum(self.y_efficiencies) / len(self.y_efficiencies)
    
    def get_average_hit_precision(self):
        """Get average hit precision (100% = center of target)"""
        if not self.hit_precisions:
            return 0.0
        return sum(self.hit_precisions) / len(self.hit_precisions)
    
    def get_average_overshoots(self):
        """Get average overshoot counts for X and Y"""
        x_avg = sum(self.x_overshoots) / len(self.x_overshoots) if self.x_overshoots else 0.0
        y_avg = sum(self.y_overshoots) / len(self.y_overshoots) if self.y_overshoots else 0.0
        return x_avg, y_avg
    
    def get_average_micro_adjustments(self):
        """Get average micro-adjustment counts for X and Y"""
        x_avg = sum(self.x_micro_adjustments) / len(self.x_micro_adjustments) if self.x_micro_adjustments else 0.0
        y_avg = sum(self.y_micro_adjustments) / len(self.y_micro_adjustments) if self.y_micro_adjustments else 0.0
        return x_avg, y_avg
    
    def get_sensitivity_diagnosis(self):
        """
        Analyze overshoot/nudge patterns to suggest sensitivity adjustments.
        Returns a diagnosis string for display.
        """
        x_over, y_over = self.get_average_overshoots()
        x_nudges, y_nudges = self.get_average_micro_adjustments()
        
        diagnoses = []
        
        # Thresholds for diagnosis
        # Reversals: direction changes near target (overshoot indicator)
        overshoot_threshold = 0.5  # 0.5+ reversals per target = overshooting
        
        # Nudges: extra movement pulses (undershoot indicator)
        # 0 = one smooth motion (ideal)
        # 1+ = had to restart movement (undershooting)
        nudge_threshold = 0.8  # 0.8+ extra pulses per target = undershooting
        
        # X-axis diagnosis
        if x_over > overshoot_threshold and x_nudges <= nudge_threshold:
            diagnoses.append("X: overshoot (↓ sens)")
        elif x_nudges > nudge_threshold and x_over <= overshoot_threshold:
            diagnoses.append("X: undershoot (↑ sens)")
        elif x_over > overshoot_threshold and x_nudges > nudge_threshold:
            diagnoses.append("X: inconsistent")
        
        # Y-axis diagnosis
        if y_over > overshoot_threshold and y_nudges <= nudge_threshold:
            diagnoses.append("Y: overshoot (↓ sens)")
        elif y_nudges > nudge_threshold and y_over <= overshoot_threshold:
            diagnoses.append("Y: undershoot (↑ sens)")
        elif y_over > overshoot_threshold and y_nudges > nudge_threshold:
            diagnoses.append("Y: inconsistent")
        
        return " | ".join(diagnoses) if diagnoses else ""
    
    def classify_shot(self, approach_data):
        """
        Classify a single shot as overshoot/undershoot/good based on approach data.
        Returns a dict with X and Y classifications.
        """
        if not approach_data:
            return {'x': 'none', 'y': 'none'}
        
        # Thresholds (same as diagnosis)
        overshoot_threshold = 0.5
        nudge_threshold = 0.8
        
        result = {'x': 'good', 'y': 'good'}
        
        # X-axis
        x_rev = approach_data['x_reversals']
        x_nudge = approach_data['x_micro_adjustments']
        if x_rev > overshoot_threshold and x_nudge <= nudge_threshold:
            result['x'] = 'OVER'
        elif x_nudge > nudge_threshold and x_rev <= overshoot_threshold:
            result['x'] = 'UNDER'
        elif x_rev > overshoot_threshold and x_nudge > nudge_threshold:
            result['x'] = 'BOTH'
        
        # Y-axis
        y_rev = approach_data['y_reversals']
        y_nudge = approach_data['y_micro_adjustments']
        if y_rev > overshoot_threshold and y_nudge <= nudge_threshold:
            result['y'] = 'OVER'
        elif y_nudge > nudge_threshold and y_rev <= overshoot_threshold:
            result['y'] = 'UNDER'
        elif y_rev > overshoot_threshold and y_nudge > nudge_threshold:
            result['y'] = 'BOTH'
        
        return result
    
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
            
    def spawn_target_at_random_position(self):
        """Spawn a new purple target at random position within world bounds"""
        if not self.is_active:
            return
        
        # Calculate world bounds (same as camera clamp)
        max_pitch = (self.canvas_height / 2) / self.pixels_per_degree * 0.5
        max_yaw = (self.canvas_width / 2) / self.pixels_per_degree * 0.5
        
        # Spawn within the bounded world space (with margin from edges)
        margin = 0.85  # Stay within 85% of bounds so targets aren't at very edge
        target_yaw = random.uniform(-max_yaw * margin, max_yaw * margin)
        target_pitch = random.uniform(-max_pitch * margin, max_pitch * margin)
        
        self.targets.append({
            'yaw': target_yaw,
            'pitch': target_pitch,
            'spawn_time': time.time()
        })
    
    def find_closest_target(self):
        """Find the target closest to the current crosshair position"""
        if not self.targets:
            return None, None, float('inf')
        
        closest_target = None
        closest_index = None
        closest_distance = float('inf')
        
        for i, target in enumerate(self.targets):
            target_yaw = target['yaw']
            target_pitch = target['pitch']
            
            # Calculate angular distance to crosshair
            yaw_diff = target_yaw - self.yaw
            while yaw_diff > 180:
                yaw_diff -= 360
            while yaw_diff < -180:
                yaw_diff += 360
            
            pitch_diff = target_pitch - self.pitch
            
            distance = math.sqrt(yaw_diff**2 + pitch_diff**2)
            
            if distance < closest_distance:
                closest_distance = distance
                closest_target = target
                closest_index = i
        
        return closest_target, closest_index, closest_distance
    
    def get_target_current_size(self, target):
        """Get the current size of a target based on its age (shrinks over lifetime)"""
        current_time = time.time()
        target_age = current_time - target['spawn_time']
        
        # Linear shrink from target_size to target_min_size over lifetime
        age_ratio = min(target_age / self.target_lifetime, 1.0)
        current_size = self.target_size - (self.target_size - self.target_min_size) * age_ratio
        
        return max(current_size, self.target_min_size)
    
    def spawn_debug_target(self):
        """Spawn a single target for debug mode - doesn't expire"""
        if not self.is_active or self.game_mode != 'debug':
            return
        
        self.targets = []
        
        # Reset debug visualization
        self.debug_frozen = False
        self.debug_analysis_points = []
        self.debug_reversal_points = []
        self.debug_pause_points = []
        self.debug_x_undershoot_points = []
        self.debug_y_undershoot_points = []
        self.debug_x_overshoot_pos = None
        self.debug_y_overshoot_pos = None
        
        # Reset path tracking
        self.path_points = [(self.yaw, self.pitch)]
        self.has_last_hit = True
        self.last_hit_yaw = self.yaw
        self.last_hit_pitch = self.pitch
        
        # Calculate world bounds (same as camera clamp)
        max_pitch = (self.canvas_height / 2) / self.pixels_per_degree * 0.5
        max_yaw = (self.canvas_width / 2) / self.pixels_per_degree * 0.5
        
        # Spawn within bounded world space
        margin = 0.85
        target_yaw = random.uniform(-max_yaw * margin, max_yaw * margin)
        target_pitch = random.uniform(-max_pitch * margin, max_pitch * margin)
        
        self.targets.append((target_yaw, target_pitch, time.time()))
        
        self.trail_points = []
        
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
            
            # Draw timer in top right corner
            timer_minutes = int(self.session_timer // 60)
            timer_seconds = int(self.session_timer % 60)
            timer_text = f"{timer_minutes:02d}:{timer_seconds:02d}"
            self.canvas.create_text(
                self.canvas_width - 60,
                30,
                text=timer_text,
                font=("Arial", 20, "bold"),
                fill="#ffffff",
                tags="timer"
            )
            
            if self.game_mode == 'random':
                # First line: basic stats
                stats_text = f"Hits: {self.stats.hits} | Misses: {self.stats.misses} | Accuracy: {accuracy:.1f}%"
                if avg_time > 0:
                    stats_text += f" | Avg Time: {avg_time:.3f}s"
                avg_precision = self.get_average_hit_precision()
                if avg_precision > 0:
                    stats_text += f" | Precision: {avg_precision:.1f}%"
                
                # Second line: path efficiency breakdown
                avg_efficiency = self.get_average_path_efficiency()
                avg_x_eff = self.get_average_x_efficiency()
                avg_y_eff = self.get_average_y_efficiency()
                
                efficiency_text = ""
                if avg_efficiency > 0:
                    efficiency_text = f"Path: {avg_efficiency:.1f}%"
                if avg_x_eff > 0:
                    efficiency_text += f" | X: {avg_x_eff:.1f}%"
                if avg_y_eff > 0:
                    efficiency_text += f" | Y: {avg_y_eff:.1f}%"
                
                # Third line: approach analysis (overshoot/undershoot from last shot)
                approach_text = ""
                if self.last_shot_analysis:
                    data = self.last_shot_analysis
                    approach_text = f"LAST: {self.last_shot_type}"
                    # Show overshoot distances in degrees
                    if data['x_max_overshoot'] > 0 or data['y_max_overshoot'] > 0:
                        approach_text += f" | OVER: X={data['x_max_overshoot']:.2f}° Y={data['y_max_overshoot']:.2f}°"
                    # Show undershoot (micro-adjustment) counts
                    if data['x_micro_adjustments'] > 0 or data['y_micro_adjustments'] > 0:
                        approach_text += f" | UNDER: X={data['x_micro_adjustments']:.0f} Y={data['y_micro_adjustments']:.0f}"
                
                # Fourth line: totals and sensitivity diagnosis
                last_shot_text = ""
                total_samples = len(self.x_overshoots)
                if total_samples > 0:
                    total_x_over = sum(1 for x in self.x_overshoots if x > 0.5)
                    total_y_over = sum(1 for y in self.y_overshoots if y > 0.5)
                    total_x_under = sum(1 for x in self.x_micro_adjustments if x > 0.8)
                    total_y_under = sum(1 for y in self.y_micro_adjustments if y > 0.8)
                    
                    last_shot_text = f"TOTALS ({total_samples}): X-over={total_x_over} X-under={total_x_under} Y-over={total_y_over} Y-under={total_y_under}"
                    
                    # Add sensitivity diagnosis
                    diagnosis = self.get_sensitivity_diagnosis()
                    if diagnosis:
                        last_shot_text += f" | {diagnosis}"
                
            elif self.game_mode == 'tracking':
                elapsed = time.time() - self.tracking_start_time
                remaining = max(0, self.tracking_duration - elapsed)
                tracking_accuracy = 0
                if self.tracking_total_time > 0:
                    tracking_accuracy = (self.tracking_time_on_target / self.tracking_total_time) * 100
                stats_text = f"Time: {remaining:.1f}s | Tracking Accuracy: {tracking_accuracy:.1f}% | On Target: {self.tracking_time_on_target:.1f}s"
                efficiency_text = ""
                approach_text = ""
                last_shot_text = ""
            
            elif self.game_mode == 'debug':
                # Debug mode display
                stats_text = f"DEBUG MODE | Hits: {self.stats.hits} | Misses: {self.stats.misses} | SPACE = new target"
                efficiency_text = f"Path points: {len(self.path_points)} | Analysis window: last {int(self.approach_analysis_window * 100)}%"
                
                # Detailed approach info - show both over and under
                approach_text = ""
                if self.last_shot_analysis:
                    data = self.last_shot_analysis
                    approach_text = f"LAST: {self.last_shot_type}"
                    # Show overshoot distances in degrees
                    if data['x_max_overshoot'] > 0 or data['y_max_overshoot'] > 0:
                        approach_text += f" | OVER: X={data['x_max_overshoot']:.2f}° Y={data['y_max_overshoot']:.2f}°"
                    # Show undershoot (micro-adjustment) counts
                    if data['x_micro_adjustments'] > 0 or data['y_micro_adjustments'] > 0:
                        approach_text += f" | UNDER: X={data['x_micro_adjustments']:.0f} Y={data['y_micro_adjustments']:.0f}"
                
                # Debug markers info
                last_shot_text = ""
                overshoot_count = (1 if self.debug_x_overshoot_pos else 0) + (1 if self.debug_y_overshoot_pos else 0)
                x_undershoot_count = len(self.debug_x_undershoot_points)
                y_undershoot_count = len(self.debug_y_undershoot_points)
                parts = []
                if overshoot_count > 0:
                    parts.append(f"{overshoot_count} OVER (X=yellow, Y=orange, XY=red)")
                if x_undershoot_count > 0 or y_undershoot_count > 0:
                    parts.append(f"UNDER X={x_undershoot_count} Y={y_undershoot_count} (cyan/magenta)")
                if parts:
                    last_shot_text = "Markers: " + " | ".join(parts)
            
            # Show current sensitivity (X and Y)
            stats_text += f" | X: {self.current_x_sens:.1f}% Y: {self.current_y_sens:.1f}%"
            
            # Add message if mouse is unlocked
            if not self.mouse_locked and self.mouse_was_locked:
                stats_text += " | CLICK TO REACTIVATE MOUSE LOCK"
            
            # Draw first line of stats
            self.canvas.create_text(
                center_x,
                30,
                text=stats_text,
                font=("Arial", 16, "bold"),
                fill="#00ff00",
                tags="stats"
            )
            
            # Draw second line (efficiency breakdown) if we have data
            if (self.game_mode == 'random' or self.game_mode == 'debug') and efficiency_text:
                self.canvas.create_text(
                    center_x,
                    55,
                    text=efficiency_text,
                    font=("Arial", 14),
                    fill="#ffaa00",  # Orange for efficiency stats
                    tags="stats"
                )
            
            # Draw third line (approach analysis) if we have data
            if (self.game_mode == 'random' or self.game_mode == 'debug') and approach_text:
                self.canvas.create_text(
                    center_x,
                    80,
                    text=approach_text,
                    font=("Arial", 13),
                    fill="#ff6666",  # Light red for approach analysis
                    tags="stats"
                )
            
            # Draw fourth line (last shot details) if we have data
            if (self.game_mode == 'random' or self.game_mode == 'debug') and last_shot_text:
                self.canvas.create_text(
                    center_x,
                    105,
                    text=last_shot_text,
                    font=("Arial", 12),
                    fill="#66ffff",  # Cyan for debug info
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
                
                # Normal cyan/blue trail (no flash effect)
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
        
        # Debug mode: Draw full path visualization
        if self.game_mode == 'debug' and len(self.path_points) > 1:
            # Calculate analysis window start index
            analysis_start = int(len(self.path_points) * (1 - self.approach_analysis_window))
            
            # Draw path points
            for i in range(1, len(self.path_points)):
                prev_yaw, prev_pitch = self.path_points[i - 1]
                curr_yaw, curr_pitch = self.path_points[i]
                
                # Convert to screen coordinates
                prev_yaw_diff = prev_yaw - self.yaw
                while prev_yaw_diff > 180:
                    prev_yaw_diff -= 360
                while prev_yaw_diff < -180:
                    prev_yaw_diff += 360
                prev_x = center_x + (prev_yaw_diff * self.pixels_per_degree)
                prev_y = center_y - ((prev_pitch - self.pitch) * self.pixels_per_degree)
                
                curr_yaw_diff = curr_yaw - self.yaw
                while curr_yaw_diff > 180:
                    curr_yaw_diff -= 360
                while curr_yaw_diff < -180:
                    curr_yaw_diff += 360
                curr_x = center_x + (curr_yaw_diff * self.pixels_per_degree)
                curr_y = center_y - ((curr_pitch - self.pitch) * self.pixels_per_degree)
                
                # Color: gray for early path, green for analysis window
                if i >= analysis_start:
                    path_color = "#00ff00"  # Green for analysis window
                    path_width = 3
                else:
                    path_color = "#666666"  # Gray for early path
                    path_width = 2
                
                # Draw path segment
                if (0 <= prev_x <= self.canvas_width and 0 <= prev_y <= self.canvas_height and
                    0 <= curr_x <= self.canvas_width and 0 <= curr_y <= self.canvas_height):
                    self.canvas.create_line(
                        prev_x, prev_y, curr_x, curr_y,
                        fill=path_color,
                        width=path_width,
                        tags="debug_path"
                    )
            
            # Draw green square at path start
            start_yaw, start_pitch = self.path_points[0]
            start_yaw_diff = start_yaw - self.yaw
            while start_yaw_diff > 180:
                start_yaw_diff -= 360
            while start_yaw_diff < -180:
                start_yaw_diff += 360
            start_x = center_x + (start_yaw_diff * self.pixels_per_degree)
            start_y = center_y - ((start_pitch - self.pitch) * self.pixels_per_degree)
            
            if 0 <= start_x <= self.canvas_width and 0 <= start_y <= self.canvas_height:
                size = 6
                self.canvas.create_rectangle(
                    start_x - size, start_y - size,
                    start_x + size, start_y + size,
                    fill="#00ff00",  # Green for start
                    outline="#ffffff",
                    width=2,
                    tags="debug_marker"
                )
                self.canvas.create_text(
                    start_x, start_y - 15,
                    text="START",
                    fill="#00ff00",
                    font=("Arial", 8, "bold"),
                    tags="debug_marker"
                )
        
        # Draw all targets
        # Handle expiration and drawing for random mode
        if self.game_mode == 'random':
            targets_to_remove = []
            
            # Check for expired targets and draw all targets
            for target in self.targets:
                target_yaw = target['yaw']
                target_pitch = target['pitch']
                target_age = current_time - target['spawn_time']
                
                # Check if target expired
                if target_age >= self.target_lifetime:
                    targets_to_remove.append(target)
                    self.stats.record_miss()
                    self.play_sound('miss')
                    continue
                
                # Calculate current size (shrinks over time)
                current_target_size = self.get_target_current_size(target)
                
                yaw_diff = target_yaw - self.yaw
                pitch_diff = target_pitch - self.pitch
                
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                
                target_screen_x = center_x + (yaw_diff * self.pixels_per_degree)
                target_screen_y = center_y - (pitch_diff * self.pixels_per_degree)
                
                # Only DRAW if on screen (but target stays in list regardless)
                margin = current_target_size + 10
                if (-margin <= target_screen_x <= self.canvas_width + margin and 
                    -margin <= target_screen_y <= self.canvas_height + margin):
                    
                    # Purple color for all targets
                    fill_color = "#9933ff"
                    outline_color = "#ffffff"
                    outline_width = 3
                    
                    # Draw SQUARE target
                    self.canvas.create_rectangle(
                        target_screen_x - current_target_size,
                        target_screen_y - current_target_size,
                        target_screen_x + current_target_size,
                        target_screen_y + current_target_size,
                        fill=fill_color,
                        outline=outline_color,
                        width=outline_width,
                        tags="target"
                    )
                    
                    # Draw target center dot
                    self.canvas.create_oval(
                        target_screen_x - 3,
                        target_screen_y - 3,
                        target_screen_x + 3,
                        target_screen_y + 3,
                        fill="#ffffff",
                        tags="target"
                    )
            
            # Remove expired targets and spawn replacements
            for target in targets_to_remove:
                self.targets.remove(target)
                self.spawn_target_at_random_position()
                self.path_points = [(self.yaw, self.pitch)]
            
            # Ensure we always have enough targets
            while len(self.targets) < self.num_targets:
                self.spawn_target_at_random_position()
        
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
        
        # Debug and Random mode: Draw OVER/UNDER markers on top of targets
        if self.game_mode in ('debug', 'random'):
            # Draw overshoot markers - combine into "XY" if positions are close
            x_pos = None
            y_pos = None
            
            if self.debug_x_overshoot_pos is not None:
                yaw, pitch = self.debug_x_overshoot_pos
                yaw_diff = yaw - self.yaw
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                x_pos = (center_x + (yaw_diff * self.pixels_per_degree),
                         center_y - ((pitch - self.pitch) * self.pixels_per_degree))
            
            if self.debug_y_overshoot_pos is not None:
                yaw, pitch = self.debug_y_overshoot_pos
                yaw_diff = yaw - self.yaw
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                y_pos = (center_x + (yaw_diff * self.pixels_per_degree),
                         center_y - ((pitch - self.pitch) * self.pixels_per_degree))
            
            # Check if markers are close enough to combine (within 25 pixels)
            combine_threshold = 25
            should_combine = False
            if x_pos and y_pos:
                dist = math.sqrt((x_pos[0] - y_pos[0])**2 + (x_pos[1] - y_pos[1])**2)
                should_combine = dist < combine_threshold
            
            if should_combine:
                # Draw combined XY marker (use X position, green color)
                x, y = x_pos
                if 0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height:
                    self.canvas.create_oval(
                        x - 12, y - 12, x + 12, y + 12,
                        fill="#ff0000",  # Red for combined XY
                        outline="#000000",
                        width=2,
                        tags="debug_marker"
                    )
                    self.canvas.create_text(
                        x, y,
                        text="XY",
                        fill="#000000",
                        font=("Arial", 10, "bold"),
                        tags="debug_marker"
                    )
            else:
                # Draw X marker separately
                if x_pos:
                    x, y = x_pos
                    if 0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height:
                        self.canvas.create_oval(
                            x - 10, y - 10, x + 10, y + 10,
                            fill="#ffff00",  # Yellow for X overshoot
                            outline="#000000",
                            width=2,
                            tags="debug_marker"
                        )
                        self.canvas.create_text(
                            x, y,
                            text="X",
                            fill="#000000",
                            font=("Arial", 11, "bold"),
                            tags="debug_marker"
                        )
                
                # Draw Y marker separately
                if y_pos:
                    x, y = y_pos
                    if 0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height:
                        self.canvas.create_oval(
                            x - 10, y - 10, x + 10, y + 10,
                            fill="#ff8800",  # Orange for Y overshoot
                            outline="#000000",
                            width=2,
                            tags="debug_marker"
                        )
                        self.canvas.create_text(
                            x, y,
                            text="Y",
                            fill="#000000",
                            font=("Arial", 11, "bold"),
                            tags="debug_marker"
                        )
            
            # Draw UNDER markers - X undershoots (cyan with "X") and Y undershoots (magenta with "Y")
            # First, collect all undershoot positions
            x_under_positions = []
            for yaw, pitch in self.debug_x_undershoot_points:
                yaw_diff = yaw - self.yaw
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                x_under_positions.append((
                    center_x + (yaw_diff * self.pixels_per_degree),
                    center_y - ((pitch - self.pitch) * self.pixels_per_degree),
                    'X'
                ))
            
            y_under_positions = []
            for yaw, pitch in self.debug_y_undershoot_points:
                yaw_diff = yaw - self.yaw
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                y_under_positions.append((
                    center_x + (yaw_diff * self.pixels_per_degree),
                    center_y - ((pitch - self.pitch) * self.pixels_per_degree),
                    'Y'
                ))
            
            # Check for overlapping X and Y undershoots and combine them
            combine_threshold = 25
            used_y_indices = set()
            
            for x_pos in x_under_positions:
                x, y, _ = x_pos
                if not (0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height):
                    continue
                
                # Check if there's a nearby Y undershoot to combine with
                combined = False
                for i, y_pos in enumerate(y_under_positions):
                    if i in used_y_indices:
                        continue
                    yx, yy, _ = y_pos
                    dist = math.sqrt((x - yx)**2 + (y - yy)**2)
                    if dist < combine_threshold:
                        # Draw combined XY undershoot (purple)
                        self.canvas.create_oval(
                            x - 10, y - 10, x + 10, y + 10,
                            fill="#ff00ff",  # Purple for combined XY undershoot
                            outline="#000000",
                            width=2,
                            tags="debug_marker"
                        )
                        self.canvas.create_text(
                            x, y,
                            text="XY",
                            fill="#000000",
                            font=("Arial", 9, "bold"),
                            tags="debug_marker"
                        )
                        used_y_indices.add(i)
                        combined = True
                        break
                
                if not combined:
                    # Draw X undershoot alone (cyan)
                    self.canvas.create_oval(
                        x - 8, y - 8, x + 8, y + 8,
                        fill="#00ffff",  # Cyan for X undershoot
                        outline="#000000",
                        width=2,
                        tags="debug_marker"
                    )
                    self.canvas.create_text(
                        x, y,
                        text="X",
                        fill="#000000",
                        font=("Arial", 10, "bold"),
                        tags="debug_marker"
                    )
            
            # Draw remaining Y undershoots that weren't combined
            for i, y_pos in enumerate(y_under_positions):
                if i in used_y_indices:
                    continue
                x, y, _ = y_pos
                if not (0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height):
                    continue
                
                # Draw Y undershoot alone (magenta/pink)
                self.canvas.create_oval(
                    x - 8, y - 8, x + 8, y + 8,
                    fill="#ff66ff",  # Magenta/pink for Y undershoot
                    outline="#000000",
                    width=2,
                    tags="debug_marker"
                )
                self.canvas.create_text(
                    x, y,
                    text="Y",
                    fill="#000000",
                    font=("Arial", 10, "bold"),
                    tags="debug_marker"
                )
            
            # Draw pause points (small red dots - where movement stopped)
            for yaw, pitch in self.debug_pause_points:
                yaw_diff = yaw - self.yaw
                while yaw_diff > 180:
                    yaw_diff -= 360
                while yaw_diff < -180:
                    yaw_diff += 360
                x = center_x + (yaw_diff * self.pixels_per_degree)
                y = center_y - ((pitch - self.pitch) * self.pixels_per_degree)
                
                if 0 <= x <= self.canvas_width and 0 <= y <= self.canvas_height:
                    self.canvas.create_oval(
                        x - 4, y - 4, x + 4, y + 4,
                        fill="#ff0000",  # Red for pauses
                        outline="#ffffff",
                        width=1,
                        tags="debug_marker"
                    )
        
        # Draw crosshair last (on top of everything)
        self.draw_crosshair(center_x, center_y)
            
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
        elif self.game_mode == 'debug':
            self.handle_debug_mode_shot()
    
    def handle_random_mode_shot(self):
        """Handle shooting in random targets mode - find closest target to crosshair"""
        # Find the closest target to crosshair position
        closest_target, closest_index, closest_distance = self.find_closest_target()
        
        if not closest_target:
            return
        
        target_yaw = closest_target['yaw']
        target_pitch = closest_target['pitch']
        spawn_time = closest_target['spawn_time']
        
        # Get current target size (shrinks over time)
        current_target_size = self.get_target_current_size(closest_target)
        
        # Check if we hit the closest target (SQUARE hitbox)
        yaw_diff = target_yaw - self.yaw
        pitch_diff = target_pitch - self.pitch
        
        while yaw_diff > 180:
            yaw_diff -= 360
        while yaw_diff < -180:
            yaw_diff += 360
        
        target_angular_size = current_target_size / self.pixels_per_degree
        
        # Square hitbox: hit if BOTH X and Y are within target bounds
        hit = (abs(yaw_diff) <= target_angular_size and abs(pitch_diff) <= target_angular_size)
        
        # Always analyze approach to the closest target (regardless of hit/miss)
        if self.has_last_hit:
            efficiency = self.calculate_path_efficiency(target_yaw, target_pitch)
            if efficiency is not None:
                self.path_efficiencies.append(efficiency)
            
            # Calculate axis-specific efficiency
            x_eff, y_eff = self.calculate_axis_efficiency(target_yaw, target_pitch)
            if x_eff is not None:
                self.x_efficiencies.append(x_eff)
            if y_eff is not None:
                self.y_efficiencies.append(y_eff)
            
            # Analyze final approach for overshoot/undershoot patterns
            approach_data = self.analyze_final_approach(target_yaw, target_pitch, capture_debug=True)
            if approach_data:
                self.x_overshoots.append(approach_data['x_reversals'])
                self.y_overshoots.append(approach_data['y_reversals'])
                self.x_micro_adjustments.append(approach_data['x_micro_adjustments'])
                self.y_micro_adjustments.append(approach_data['y_micro_adjustments'])
                # Store for detailed display
                self.last_shot_analysis = approach_data
                self.last_shot_was_hit = hit
                self.last_shot_type = "HIT" if hit else "MISS"
        
        if hit:
            # HIT the target
            reaction_time = time.time() - spawn_time
            self.stats.record_hit(reaction_time)
            
            # Calculate hit precision (100% = center, 0% = edge)
            # For square, use max of X and Y distance ratio
            x_ratio = abs(yaw_diff) / target_angular_size if target_angular_size > 0 else 0
            y_ratio = abs(pitch_diff) / target_angular_size if target_angular_size > 0 else 0
            max_ratio = max(x_ratio, y_ratio)
            precision = (1 - max_ratio) * 100
            self.hit_precisions.append(precision)
            
            # Play hit sound
            self.play_sound('hit')
            
            # Record this hit position for next path measurement
            self.record_hit_position()
            
            # Remove hit target and spawn a new one
            self.targets.remove(closest_target)
            self.spawn_target_at_random_position()
        else:
            # MISS - clicked but didn't hit the closest target
            self.stats.record_miss()
            
            # Reset path for next attempt (don't update last_hit position since we missed)
            self.path_points = [(self.yaw, self.pitch)]
        
        self.update_stats_display()
    
    def handle_debug_mode_shot(self):
        """Handle shooting in debug test mode"""
        if not self.targets:
            return
        
        # Get the single target
        target_yaw, target_pitch, spawn_time = self.targets[0]
        
        # Check if we hit (SQUARE hitbox for debug mode)
        yaw_diff = target_yaw - self.yaw
        pitch_diff = target_pitch - self.pitch
        
        while yaw_diff > 180:
            yaw_diff -= 360
        while yaw_diff < -180:
            yaw_diff += 360
        
        target_angular_size = self.target_size / self.pixels_per_degree
        
        # Square hitbox: hit if BOTH X and Y are within target bounds
        hit = (abs(yaw_diff) <= target_angular_size and abs(pitch_diff) <= target_angular_size)
        
        # Record stats first
        if hit:
            self.stats.record_hit(time.time() - spawn_time)
            self.play_sound('hit')
            self.last_shot_type = "HIT"
        else:
            self.stats.record_miss()
            self.last_shot_type = "MISS"
        
        self.last_shot_was_hit = hit
        
        # Analyze approach with debug capture (may return None if not enough points)
        approach_data = self.analyze_final_approach(target_yaw, target_pitch, capture_debug=True)
        
        if approach_data:
            self.last_shot_analysis = approach_data
        else:
            # Not enough path data - clear previous analysis
            self.last_shot_analysis = None
            self.debug_reversal_points = []
            self.debug_pause_points = []
            self.debug_x_undershoot_points = []
            self.debug_y_undershoot_points = []
            self.debug_x_overshoot_pos = None
            self.debug_y_overshoot_pos = None
        
        # Don't auto-spawn new target in debug mode - user presses SPACE
        # Keep the visualization on screen
    
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
        
        # Add efficiency breakdown
        avg_efficiency = self.get_average_path_efficiency()
        avg_x_eff = self.get_average_x_efficiency()
        avg_y_eff = self.get_average_y_efficiency()
        
        if avg_efficiency > 0:
            stats_text += f" | Path: {avg_efficiency:.1f}%"
        if avg_x_eff > 0:
            stats_text += f" | X: {avg_x_eff:.1f}%"
        if avg_y_eff > 0:
            stats_text += f" | Y: {avg_y_eff:.1f}%"
        
        # Only update label when not in active gameplay (stats drawn in draw_scene when active)
        if not self.is_active:
            self.stats_label.config(text=stats_text)
        
    def cleanup(self):
        """Cleanup resources"""
        self.mouse_locked = False
        self.is_active = False
