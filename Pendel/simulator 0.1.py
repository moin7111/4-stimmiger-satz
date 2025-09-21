# Pendel-Simulator v2.0
# Verbesserte und übersichtlichere Version mit optimiertem Layout

import ui
import math
import time
import threading


# ===================== Physik-Engine =====================

class PendulumPhysics:
    """Physik-Engine für Einzel- und Doppelpendel-Simulation"""
    
    @staticmethod
    def single_pendulum_derivatives(state, params):
        """Berechnet Ableitungen für Einzelpendel"""
        theta, omega = state
        g = params['g']
        l = params['l1']
        damping = params.get('damping', 0.0)
        
        dtheta = omega
        domega = -(g / l) * math.sin(theta) - damping * omega
        
        return [dtheta, domega]
    
    @staticmethod
    def double_pendulum_derivatives(state, params):
        """Berechnet Ableitungen für Doppelpendel"""
        th1, w1, th2, w2 = state
        m1, m2 = params['m1'], params['m2']
        l1, l2 = params['l1'], params['l2']
        g = params['g']
        damping = params.get('damping', 0.0)
        
        delta = th2 - th1
        denom = (2 * m1 + m2 - m2 * math.cos(2 * delta))
        
        if abs(denom) < 1e-9:
            denom = 1e-9
        
        # Erste Masse
        num1 = -g * (2 * m1 + m2) * math.sin(th1)
        num1 -= m2 * g * math.sin(th1 - 2 * th2)
        num1 -= 2 * math.sin(delta) * m2 * (w2**2 * l2 + w1**2 * l1 * math.cos(delta))
        domega1 = num1 / (l1 * denom) - damping * w1
        
        # Zweite Masse
        num2 = 2 * math.sin(delta) * (w1**2 * l1 * (m1 + m2) + 
                                      g * (m1 + m2) * math.cos(th1) + 
                                      w2**2 * l2 * m2 * math.cos(delta))
        domega2 = num2 / (l2 * denom) - damping * w2
        
        return [w1, domega1, w2, domega2]
    
    @staticmethod
    def rk4_step(state, dt, params, deriv_func):
        """Runge-Kutta 4. Ordnung Integration"""
        k1 = deriv_func(state, params)
        
        s2 = [state[i] + 0.5 * dt * k1[i] for i in range(len(state))]
        k2 = deriv_func(s2, params)
        
        s3 = [state[i] + 0.5 * dt * k2[i] for i in range(len(state))]
        k3 = deriv_func(s3, params)
        
        s4 = [state[i] + dt * k3[i] for i in range(len(state))]
        k4 = deriv_func(s4, params)
        
        return [state[i] + dt * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i]) / 6.0 
                for i in range(len(state))]


# ===================== Visualisierung =====================

class PendulumCanvas(ui.View):
    """Zeichenfläche für die Pendel-Simulation"""
    
    def __init__(self):
        super().__init__()
        self.background_color = '#F8F9FA'
        self.mode = 'double'
        self.state = [math.radians(45), 0, math.radians(-30), 0]
        self.params = {
            'm1': 1.0, 'm2': 1.0,
            'l1': 1.0, 'l2': 1.0,
            'g': 9.81, 'damping': 0.0
        }
        self.trail = []
        self.trail_enabled = True
        self.max_trail_points = 200
        self.scale = 150  # Pixel pro Meter
        self.time = 0.0
        self.marks = []
        
    def draw(self):
        """Zeichnet die Pendel-Visualisierung"""
        width = self.width
        height = self.height
        
        # Hintergrund
        ui.set_color('#FFFFFF')
        ui.Path.rect(0, 0, width, height).fill()
        
        # Gitter
        ui.set_color('#E5E7EB')
        grid_size = 50
        for x in range(0, int(width), grid_size):
            path = ui.Path()
            path.line_width = 0.5
            path.move_to(x, 0)
            path.line_to(x, height)
            path.stroke()
        for y in range(0, int(height), grid_size):
            path = ui.Path()
            path.line_width = 0.5
            path.move_to(0, y)
            path.line_to(width, y)
            path.stroke()
        
        # Ursprung
        origin_x = width / 2
        origin_y = height * 0.2
        
        # Pendel-Positionen berechnen
        l1 = self.params['l1'] * self.scale
        l2 = self.params['l2'] * self.scale
        
        if self.mode == 'double':
            th1, _, th2, _ = self.state
            x1 = origin_x + l1 * math.sin(th1)
            y1 = origin_y + l1 * math.cos(th1)
            x2 = x1 + l2 * math.sin(th2)
            y2 = y1 + l2 * math.cos(th2)
        else:
            th1, _ = self.state
            x1 = origin_x + l1 * math.sin(th1)
            y1 = origin_y + l1 * math.cos(th1)
            x2, y2 = x1, y1
        
        # Spur zeichnen
        if self.trail_enabled and len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = 0.3 + 0.7 * (i / len(self.trail))
                ui.set_color((0.2, 0.4, 0.8, alpha))
                path = ui.Path()
                path.line_width = 2
                path.move_to(self.trail[i-1][0], self.trail[i-1][1])
                path.line_to(self.trail[i][0], self.trail[i][1])
                path.stroke()
        
        # Pendelstangen
        ui.set_color('#374151')
        path = ui.Path()
        path.line_width = 3
        path.move_to(origin_x, origin_y)
        path.line_to(x1, y1)
        path.stroke()
        
        if self.mode == 'double':
            path = ui.Path()
            path.line_width = 3
            path.move_to(x1, y1)
            path.line_to(x2, y2)
            path.stroke()
        
        # Massen
        ui.set_color('#2563EB')
        ui.Path.oval(x1 - 10, y1 - 10, 20, 20).fill()
        
        if self.mode == 'double':
            ui.set_color('#DC2626')
            ui.Path.oval(x2 - 8, y2 - 8, 16, 16).fill()
        
        # Aufhängepunkt
        ui.set_color('#1F2937')
        ui.Path.oval(origin_x - 5, origin_y - 5, 10, 10).fill()
        
        # Markierungen
        ui.set_color('#10B981')
        for mark in self.marks:
            ui.Path.oval(mark[0] - 3, mark[1] - 3, 6, 6).fill()
        
        # Zeit-Anzeige
        ui.set_color('#374151')
        time_text = f'Zeit: {self.time:.2f} s'
        ui.draw_string(time_text, (10, height - 30, 150, 20), 
                      font=('Helvetica', 14))
    
    def add_trail_point(self, x, y):
        """Fügt einen Punkt zur Spur hinzu"""
        self.trail.append((x, y))
        if len(self.trail) > self.max_trail_points:
            self.trail.pop(0)
    
    def clear_trail(self):
        """Löscht die Spur"""
        self.trail = []
        self.set_needs_display()
    
    def add_mark(self, x, y):
        """Fügt eine Markierung hinzu"""
        self.marks.append((x, y))
        self.set_needs_display()
    
    def clear_marks(self):
        """Löscht alle Markierungen"""
        self.marks = []
        self.set_needs_display()


# ===================== Hauptanwendung =====================

class PendulumSimulator:
    """Hauptklasse für den Pendel-Simulator"""
    
    def __init__(self):
        self.physics = PendulumPhysics()
        self.running = False
        self.time_scale = 1.0
        self.thread = None
        self.stop_flag = False
        
        # UI erstellen
        self.create_ui()
        
    def create_ui(self):
        """Erstellt die Benutzeroberfläche"""
        # Hauptfenster
        self.view = ui.View()
        self.view.name = 'Pendel Simulator v2.0'
        self.view.background_color = '#F3F4F6'
        
        # Canvas
        self.canvas = PendulumCanvas()
        self.canvas.flex = 'WH'
        
        # Control Panel
        self.create_control_panel()
        
        # Layout
        self.view.add_subview(self.canvas)
        self.view.add_subview(self.control_panel)
        
    def create_control_panel(self):
        """Erstellt das Kontrollpanel"""
        panel = ui.View()
        panel.background_color = '#FFFFFF'
        panel.border_width = 1
        panel.border_color = '#E5E7EB'
        panel.corner_radius = 8
        
        y_pos = 10
        
        # Titel
        title = ui.Label()
        title.text = 'Steuerung'
        title.font = ('Helvetica-Bold', 16)
        title.alignment = ui.ALIGN_CENTER
        title.frame = (10, y_pos, 280, 30)
        panel.add_subview(title)
        y_pos += 40
        
        # Start/Stop Button
        self.start_btn = ui.Button()
        self.start_btn.title = 'Start'
        self.start_btn.background_color = '#10B981'
        self.start_btn.tint_color = 'white'
        self.start_btn.corner_radius = 6
        self.start_btn.frame = (10, y_pos, 135, 40)
        self.start_btn.action = self.toggle_simulation
        panel.add_subview(self.start_btn)
        
        # Reset Button
        reset_btn = ui.Button()
        reset_btn.title = 'Reset'
        reset_btn.background_color = '#6B7280'
        reset_btn.tint_color = 'white'
        reset_btn.corner_radius = 6
        reset_btn.frame = (155, y_pos, 135, 40)
        reset_btn.action = self.reset_simulation
        panel.add_subview(reset_btn)
        y_pos += 50
        
        # Separator
        self.add_separator(panel, y_pos)
        y_pos += 10
        
        # Modus-Auswahl
        mode_label = ui.Label()
        mode_label.text = 'Modus:'
        mode_label.frame = (10, y_pos, 60, 30)
        panel.add_subview(mode_label)
        
        self.mode_control = ui.SegmentedControl()
        self.mode_control.segments = ['Doppelpendel', 'Einzelpendel']
        self.mode_control.selected_index = 0
        self.mode_control.frame = (80, y_pos, 210, 30)
        self.mode_control.action = self.change_mode
        panel.add_subview(self.mode_control)
        y_pos += 40
        
        # Parameter-Sektion
        self.add_separator(panel, y_pos)
        y_pos += 10
        
        # Längen
        y_pos = self.add_parameter_field(panel, 'Länge 1 (m):', 'l1_field', 
                                         '1.0', y_pos)
        y_pos = self.add_parameter_field(panel, 'Länge 2 (m):', 'l2_field', 
                                         '1.0', y_pos)
        
        # Massen
        y_pos = self.add_parameter_field(panel, 'Masse 1 (kg):', 'm1_field', 
                                         '1.0', y_pos)
        y_pos = self.add_parameter_field(panel, 'Masse 2 (kg):', 'm2_field', 
                                         '1.0', y_pos)
        
        # Gravitation
        self.add_separator(panel, y_pos)
        y_pos += 10
        
        g_label = ui.Label()
        g_label.text = 'Gravitation (m/s²):'
        g_label.frame = (10, y_pos, 130, 25)
        panel.add_subview(g_label)
        
        self.g_slider = ui.Slider()
        self.g_slider.value = 9.81
        self.g_slider.minimum_value = 0
        self.g_slider.maximum_value = 20
        self.g_slider.frame = (10, y_pos + 25, 230, 30)
        self.g_slider.action = self.update_gravity
        panel.add_subview(self.g_slider)
        
        self.g_value = ui.Label()
        self.g_value.text = '9.81'
        self.g_value.alignment = ui.ALIGN_RIGHT
        self.g_value.frame = (245, y_pos + 25, 45, 30)
        panel.add_subview(self.g_value)
        y_pos += 60
        
        # Dämpfung
        damp_label = ui.Label()
        damp_label.text = 'Dämpfung:'
        damp_label.frame = (10, y_pos, 130, 25)
        panel.add_subview(damp_label)
        
        self.damping_slider = ui.Slider()
        self.damping_slider.value = 0
        self.damping_slider.minimum_value = 0
        self.damping_slider.maximum_value = 0.5
        self.damping_slider.frame = (10, y_pos + 25, 230, 30)
        self.damping_slider.action = self.update_damping
        panel.add_subview(self.damping_slider)
        
        self.damping_value = ui.Label()
        self.damping_value.text = '0.00'
        self.damping_value.alignment = ui.ALIGN_RIGHT
        self.damping_value.frame = (245, y_pos + 25, 45, 30)
        panel.add_subview(self.damping_value)
        y_pos += 60
        
        # Geschwindigkeit
        self.add_separator(panel, y_pos)
        y_pos += 10
        
        speed_label = ui.Label()
        speed_label.text = 'Geschwindigkeit:'
        speed_label.frame = (10, y_pos, 130, 25)
        panel.add_subview(speed_label)
        
        self.speed_slider = ui.Slider()
        self.speed_slider.value = 1.0
        self.speed_slider.minimum_value = 0.1
        self.speed_slider.maximum_value = 3.0
        self.speed_slider.frame = (10, y_pos + 25, 230, 30)
        self.speed_slider.action = self.update_speed
        panel.add_subview(self.speed_slider)
        
        self.speed_value = ui.Label()
        self.speed_value.text = '1.0x'
        self.speed_value.alignment = ui.ALIGN_RIGHT
        self.speed_value.frame = (245, y_pos + 25, 45, 30)
        panel.add_subview(self.speed_value)
        y_pos += 60
        
        # Spur-Kontrollen
        self.add_separator(panel, y_pos)
        y_pos += 10
        
        trail_label = ui.Label()
        trail_label.text = 'Spur anzeigen:'
        trail_label.frame = (10, y_pos, 120, 30)
        panel.add_subview(trail_label)
        
        self.trail_switch = ui.Switch()
        self.trail_switch.value = True
        self.trail_switch.frame = (140, y_pos, 60, 30)
        self.trail_switch.action = self.toggle_trail
        panel.add_subview(self.trail_switch)
        
        clear_trail_btn = ui.Button()
        clear_trail_btn.title = 'Löschen'
        clear_trail_btn.background_color = '#EF4444'
        clear_trail_btn.tint_color = 'white'
        clear_trail_btn.corner_radius = 4
        clear_trail_btn.frame = (210, y_pos, 80, 30)
        clear_trail_btn.action = lambda s: self.canvas.clear_trail()
        panel.add_subview(clear_trail_btn)
        
        panel.frame = (0, 0, 300, y_pos + 40)
        self.control_panel = panel
        
        # Parameter-Felder speichern
        self.parameter_fields = {
            'l1': self.l1_field,
            'l2': self.l2_field,
            'm1': self.m1_field,
            'm2': self.m2_field
        }
    
    def add_parameter_field(self, panel, label_text, field_name, default, y_pos):
        """Fügt ein Parameter-Eingabefeld hinzu"""
        label = ui.Label()
        label.text = label_text
        label.frame = (10, y_pos, 120, 25)
        panel.add_subview(label)
        
        field = ui.TextField()
        field.text = default
        field.alignment = ui.ALIGN_RIGHT
        field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        field.border_width = 1
        field.border_color = '#E5E7EB'
        field.corner_radius = 4
        field.frame = (200, y_pos, 90, 25)
        panel.add_subview(field)
        
        setattr(self, field_name, field)
        return y_pos + 30
    
    def add_separator(self, panel, y_pos):
        """Fügt eine Trennlinie hinzu"""
        sep = ui.View()
        sep.background_color = '#E5E7EB'
        sep.frame = (10, y_pos, 280, 1)
        panel.add_subview(sep)
    
    def toggle_simulation(self, sender):
        """Startet/Stoppt die Simulation"""
        if self.running:
            self.stop_simulation()
        else:
            self.start_simulation()
    
    def start_simulation(self):
        """Startet die Simulation"""
        if self.running:
            return
        
        self.running = True
        self.stop_flag = False
        self.start_btn.title = 'Stop'
        self.start_btn.background_color = '#EF4444'
        
        # Parameter aktualisieren
        self.update_parameters()
        
        # Simulationsthread starten
        self.thread = threading.Thread(target=self.simulation_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_simulation(self):
        """Stoppt die Simulation"""
        self.running = False
        self.stop_flag = True
        self.start_btn.title = 'Start'
        self.start_btn.background_color = '#10B981'
    
    def reset_simulation(self, sender=None):
        """Setzt die Simulation zurück"""
        self.stop_simulation()
        
        # Zustand zurücksetzen
        if self.canvas.mode == 'double':
            self.canvas.state = [math.radians(45), 0, math.radians(-30), 0]
        else:
            self.canvas.state = [math.radians(45), 0]
        
        self.canvas.time = 0.0
        self.canvas.clear_trail()
        self.canvas.clear_marks()
    
    def simulation_loop(self):
        """Hauptschleife der Simulation"""
        dt = 0.01
        last_time = time.time()
        
        while self.running and not self.stop_flag:
            current_time = time.time()
            elapsed = current_time - last_time
            last_time = current_time
            
            # Zeitschritt anpassen
            sim_dt = dt * self.time_scale
            
            # Parameter aktualisieren
            self.update_parameters()
            
            # Physik-Update
            if self.canvas.mode == 'double':
                deriv_func = self.physics.double_pendulum_derivatives
            else:
                deriv_func = self.physics.single_pendulum_derivatives
            
            self.canvas.state = self.physics.rk4_step(
                self.canvas.state, sim_dt, self.canvas.params, deriv_func
            )
            
            self.canvas.time += sim_dt
            
            # Trail-Update
            if self.canvas.trail_enabled:
                l1 = self.canvas.params['l1'] * self.canvas.scale
                l2 = self.canvas.params['l2'] * self.canvas.scale
                origin_x = self.canvas.width / 2
                origin_y = self.canvas.height * 0.2
                
                if self.canvas.mode == 'double':
                    th1, _, th2, _ = self.canvas.state
                    x1 = origin_x + l1 * math.sin(th1)
                    y1 = origin_y + l1 * math.cos(th1)
                    x2 = x1 + l2 * math.sin(th2)
                    y2 = y1 + l2 * math.cos(th2)
                    self.canvas.add_trail_point(x2, y2)
                else:
                    th1, _ = self.canvas.state
                    x1 = origin_x + l1 * math.sin(th1)
                    y1 = origin_y + l1 * math.cos(th1)
                    self.canvas.add_trail_point(x1, y1)
            
            # UI Update
            ui.delay(self.canvas.set_needs_display, 0)
            
            # Frame-Rate begrenzen
            time.sleep(0.016)
    
    def update_parameters(self):
        """Aktualisiert die Simulationsparameter"""
        try:
            self.canvas.params['l1'] = float(self.l1_field.text or 1.0)
            self.canvas.params['l2'] = float(self.l2_field.text or 1.0)
            self.canvas.params['m1'] = float(self.m1_field.text or 1.0)
            self.canvas.params['m2'] = float(self.m2_field.text or 1.0)
        except ValueError:
            pass
    
    def change_mode(self, sender):
        """Ändert den Simulationsmodus"""
        if sender.selected_index == 0:
            self.canvas.mode = 'double'
            if len(self.canvas.state) == 2:
                self.canvas.state = [self.canvas.state[0], self.canvas.state[1], 
                                    math.radians(-30), 0]
            self.l2_field.enabled = True
            self.m2_field.enabled = True
        else:
            self.canvas.mode = 'single'
            self.canvas.state = self.canvas.state[:2]
            self.l2_field.enabled = False
            self.m2_field.enabled = False
        
        self.canvas.clear_trail()
        self.canvas.set_needs_display()
    
    def update_gravity(self, sender):
        """Aktualisiert die Gravitation"""
        self.canvas.params['g'] = sender.value
        self.g_value.text = f'{sender.value:.2f}'
    
    def update_damping(self, sender):
        """Aktualisiert die Dämpfung"""
        self.canvas.params['damping'] = sender.value
        self.damping_value.text = f'{sender.value:.2f}'
    
    def update_speed(self, sender):
        """Aktualisiert die Simulationsgeschwindigkeit"""
        self.time_scale = sender.value
        self.speed_value.text = f'{sender.value:.1f}x'
    
    def toggle_trail(self, sender):
        """Schaltet die Spur an/aus"""
        self.canvas.trail_enabled = sender.value
        if not sender.value:
            self.canvas.clear_trail()
    
    def layout(self):
        """Layout-Funktion für responsive Anpassung"""
        width = self.view.width
        height = self.view.height
        
        if width > 700:
            # Side-by-side Layout
            self.control_panel.frame = (width - 320, 10, 300, height - 20)
            self.canvas.frame = (10, 10, width - 340, height - 20)
        else:
            # Stacked Layout
            control_height = min(400, height * 0.4)
            self.control_panel.frame = (10, height - control_height - 10, 
                                       width - 20, control_height)
            self.canvas.frame = (10, 10, width - 20, 
                               height - control_height - 30)
    
    def present(self):
        """Zeigt den Simulator an"""
        self.view.present('fullscreen', hide_title_bar=False)
        self.view.layout = lambda: self.layout()
        self.layout()


# ===================== Hauptprogramm =====================

if __name__ == '__main__':
    simulator = PendulumSimulator()
    simulator.present()