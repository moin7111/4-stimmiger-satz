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

        # Trigonometrie-Lookups lokal binden und cachen
        sin = math.sin
        cos = math.cos

        delta = th1 - th2
        sin_th1 = sin(th1)
        cos_th1 = cos(th1)
        sin_th2 = sin(th2)
        cos_th2 = cos(th2)
        sin_delta = sin(delta)
        cos_delta = cos(delta)
        cos_2delta = cos(2.0 * delta)
        sin_th1_minus_2th2 = sin(th1 - 2.0 * th2)

        denom = (2.0 * m1 + m2 - m2 * cos_2delta)
        if abs(denom) < 1e-9:
            denom = 1e-9

        # Erste Masse
        num1 = -g * (2.0 * m1 + m2) * sin_th1
        num1 -= m2 * g * sin_th1_minus_2th2
        num1 -= 2.0 * sin_delta * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * cos_delta)
        domega1 = num1 / (l1 * denom) - damping * w1

        # Zweite Masse
        num2 = 2.0 * sin_delta * (
            w1 * w1 * l1 * (m1 + m2) +
            g * (m1 + m2) * cos_th1 +
            w2 * w2 * l2 * m2 * cos_delta
        )
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

    @staticmethod
    def symplectic_euler_step(state, dt, params, deriv_func):
        """Symplektischer Euler-Schritt (semi-implizit)."""
        n = len(state)
        if n == 4:
            th1, w1, th2, w2 = state
            d = deriv_func([th1, w1, th2, w2], params)
            a1 = d[1]
            a2 = d[3]
            w1 = w1 + dt * a1
            w2 = w2 + dt * a2
            th1 = th1 + dt * w1
            th2 = th2 + dt * w2
            return [th1, w1, th2, w2]
        elif n == 2:
            th, w = state
            d = deriv_func([th, w], params)
            a = d[1]
            w = w + dt * a
            th = th + dt * w
            return [th, w]
        else:
            d = deriv_func(state, params)
            return [state[i] + dt * d[i] for i in range(n)]

    @staticmethod
    def rk4_integrate_substeps(state, dt_total, dt_max, params, deriv_func):
        """Integriert dt_total via RK4 in Teil-Schritten, jeder <= dt_max."""
        steps = max(1, int(math.ceil(abs(dt_total) / max(1e-9, dt_max))))
        dt = float(dt_total) / steps
        s = list(state)
        for _ in range(steps):
            s = PendulumPhysics.rk4_step(s, dt, params, deriv_func)
        return s

    @staticmethod
    def choose_dt_max(state, base_dt=0.005, max_dt=0.02):
        """Heuristische Wahl von dt_max basierend auf max. Winkelgeschwindigkeit."""
        if len(state) == 4:
            w_max = max(abs(state[1]), abs(state[3]))
        else:
            w_max = abs(state[1]) if len(state) > 1 else 0.0
        if w_max <= 0.1:
            return max_dt
        dt = min(max_dt, base_dt / (1.0 + w_max))
        return max(1e-4, dt)

    @staticmethod
    def total_energy(state, params, mode='double'):
        """Gesamtenergie (kinetisch + potenziell). Referenz y=0 am Aufhängepunkt."""
        g = float(params['g'])
        cos = math.cos
        sin = math.sin
        if mode == 'double' and len(state) == 4:
            th1, w1, th2, w2 = state
            m1 = float(params['m1']); m2 = float(params['m2'])
            l1 = float(params['l1']); l2 = float(params['l2'])
            cos_th1 = cos(th1); sin_th1 = sin(th1)
            cos_th2 = cos(th2); sin_th2 = sin(th2)
            x1dot = l1 * w1 * cos_th1
            y1dot = -l1 * w1 * sin_th1
            x2dot = x1dot + l2 * w2 * cos_th2
            y2dot = y1dot - l2 * w2 * sin_th2
            KE = 0.5 * m1 * (x1dot*x1dot + y1dot*y1dot) + 0.5 * m2 * (x2dot*x2dot + y2dot*y2dot)
            y1 = -l1 * cos_th1
            y2 = y1 - l2 * cos_th2
            PE = m1 * g * y1 + m2 * g * y2
            return KE + PE
        else:
            th, w = state[:2]
            m = float(params['m1'])
            l = float(params['l1'])
            cos_th = cos(th); sin_th = sin(th)
            xdot = l * w * cos_th
            ydot = -l * w * sin_th
            KE = 0.5 * m * (xdot*xdot + ydot*ydot)
            y = -l * cos_th
            PE = m * g * y
            return KE + PE

    @staticmethod
    def normalize_angles(state):
        """Normalisiert Winkel auf den Bereich [-pi, pi] ohne die Winkelgeschwindigkeiten zu ändern."""
        def wrap(angle):
            # Robust modulo für Python: Ergebnis in (-pi, pi]
            two_pi = 2.0 * math.pi
            a = (angle + math.pi) % two_pi
            if a < 0:
                a += two_pi
            return a - math.pi
        s = list(state)
        if len(s) >= 2:
            s[0] = wrap(s[0])
        if len(s) >= 4:
            s[2] = wrap(s[2])
        return s


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
        self.dragging = None  # 'bob1' | 'bob2' | None
        self.controller = None  # wird vom Simulator gesetzt
        
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

    # --- Interaktion: Startpunkt durch Ziehen setzen ---
    def _origin_xy(self):
        return (self.width / 2.0, self.height * 0.2)

    def _polar_to_xy(self, origin, angle, length):
        ox, oy = origin
        return (ox + length * math.sin(angle), oy + length * math.cos(angle))

    def _xy_to_angle(self, origin, pt):
        dx = pt[0] - origin[0]
        dy = pt[1] - origin[1]
        # Winkel von der Vertikalen (nach unten) gemessen
        return math.atan2(dx, dy)

    def touch_began(self, touch):
        try:
            tx, ty = touch.location
        except Exception:
            return
        origin = self._origin_xy()
        l1 = self.params['l1'] * self.scale
        l2 = self.params['l2'] * self.scale
        if self.mode == 'double':
            th1, _, th2, _ = self.state
            x1, y1 = self._polar_to_xy(origin, th1, l1)
            x2, y2 = self._polar_to_xy((x1, y1), th2, l2)
        else:
            th1, _ = self.state
            x1, y1 = self._polar_to_xy(origin, th1, l1)
            x2, y2 = x1, y1
        # Auswahl testen (Radius ~ 20 px)
        if self.mode == 'double' and (tx - x2) ** 2 + (ty - y2) ** 2 < 20 * 20:
            self.dragging = 'bob2'
        elif (tx - x1) ** 2 + (ty - y1) ** 2 < 20 * 20:
            self.dragging = 'bob1'
        else:
            self.dragging = None
        # Beim Start des Draggens ggf. Simulation pausieren
        if self.dragging and getattr(self, 'controller', None) is not None:
            try:
                if self.controller.running:
                    self.controller.stop_simulation()
            except Exception:
                pass

    def touch_moved(self, touch):
        if not self.dragging:
            return
        try:
            tx, ty = touch.location
        except Exception:
            return
        origin = self._origin_xy()
        l1 = self.params['l1'] * self.scale
        # bob1: Winkel relativ zum Aufhängepunkt
        if self.dragging == 'bob1':
            th1 = self._xy_to_angle(origin, (tx, ty))
            if self.mode == 'double' and len(self.state) == 4:
                self.state[0] = th1
                self.state[1] = 0.0
            else:
                self.state[0] = th1
                self.state[1] = 0.0
        # bob2: Winkel relativ zur ersten Masse
        elif self.dragging == 'bob2' and self.mode == 'double' and len(self.state) == 4:
            th1 = self.state[0]
            x1, y1 = self._polar_to_xy(origin, th1, l1)
            th2 = self._xy_to_angle((x1, y1), (tx, ty))
            self.state[2] = th2
            self.state[3] = 0.0
        # Winkel normalisieren und Anzeigen aktualisieren
        self.state = PendulumPhysics.normalize_angles(self.state)
        self.set_needs_display()
        # Gewählten Startzustand merken (für Reset)
        if getattr(self, 'controller', None) is not None:
            try:
                if self.mode == 'double':
                    self.controller.start_state = list(self.state)
                else:
                    self.controller.start_state = list(self.state[:2])
            except Exception:
                pass

    def touch_ended(self, touch):
        self.dragging = None
    
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
        # Integrator/Physik-Parameter
        self.integrator = 'rk4'  # 'rk4' | 'symplectic'
        self.base_dt = 0.004
        self.dt_max = 0.015
        self.energy_ref = None
        self.energy_err = 0.0
        self.energy_check_interval = 0.5
        self._energy_accum = 0.0
        self.autoswitch = True
        self.energy_threshold = 0.1
        self.normalize_every_n = 20
        self._norm_counter = 0
        
        # UI erstellen
        self.create_ui()
        # Startzustand merken (für Reset)
        self.start_state = list(self.canvas.state) if self.canvas.mode == 'double' else list(self.canvas.state[:2])
        
    def create_ui(self):
        """Erstellt die Benutzeroberfläche"""
        # Hauptfenster
        self.view = ui.View()
        self.view.name = 'Pendel Simulator v2.0'
        self.view.background_color = '#F3F4F6'
        
        # Canvas
        self.canvas = PendulumCanvas()
        self.canvas.flex = 'WH'
        self.canvas.controller = self
        
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
        g_label.text = 'Gravitation (m/s2):'
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

        # Integrator-Auswahl
        self.add_separator(panel, y_pos)
        y_pos += 10

        int_label = ui.Label()
        int_label.text = 'Integrator:'
        int_label.frame = (10, y_pos, 100, 30)
        panel.add_subview(int_label)

        self.integrator_control = ui.SegmentedControl()
        self.integrator_control.segments = ['Accurate (RK4)', 'Fast (Symplectic)']
        self.integrator_control.selected_index = 0
        self.integrator_control.frame = (110, y_pos, 180, 30)
        self.integrator_control.action = self.change_integrator
        panel.add_subview(self.integrator_control)
        y_pos += 40

        # AutoSwitch-Einstellung
        autosw_label = ui.Label()
        autosw_label.text = 'AutoSwitch:'
        autosw_label.frame = (10, y_pos, 100, 30)
        panel.add_subview(autosw_label)

        self.autoswitch_switch = ui.Switch()
        self.autoswitch_switch.value = True
        self.autoswitch_switch.frame = (110, y_pos, 60, 30)
        self.autoswitch_switch.action = self.toggle_autoswitch
        panel.add_subview(self.autoswitch_switch)
        y_pos += 40

        # Energie-Drift Anzeige
        self.energy_label = ui.Label()
        self.energy_label.text = 'ΔE/E: —'
        self.energy_label.frame = (10, y_pos, 280, 25)
        panel.add_subview(self.energy_label)
        y_pos += 30

        # Integrator-Parameter (dt_max & base_dt)
        self.add_separator(panel, y_pos)
        y_pos += 10

        dtmax_label = ui.Label()
        dtmax_label.text = 'dt_max (s):'
        dtmax_label.frame = (10, y_pos, 100, 25)
        panel.add_subview(dtmax_label)

        self.dtmax_slider = ui.Slider()
        self.dtmax_slider.minimum_value = 0.005
        self.dtmax_slider.maximum_value = 0.05
        self.dtmax_slider.value = self.dt_max
        self.dtmax_slider.frame = (10, y_pos + 25, 230, 30)
        self.dtmax_slider.action = self.update_dt_max
        panel.add_subview(self.dtmax_slider)

        self.dtmax_value = ui.Label()
        self.dtmax_value.text = f'{self.dt_max:.3f}'
        self.dtmax_value.alignment = ui.ALIGN_RIGHT
        self.dtmax_value.frame = (245, y_pos + 25, 45, 30)
        panel.add_subview(self.dtmax_value)
        y_pos += 60

        basedt_label = ui.Label()
        basedt_label.text = 'base_dt (s):'
        basedt_label.frame = (10, y_pos, 100, 25)
        panel.add_subview(basedt_label)

        self.basedt_slider = ui.Slider()
        self.basedt_slider.minimum_value = 0.001
        self.basedt_slider.maximum_value = 0.02
        self.basedt_slider.value = self.base_dt
        self.basedt_slider.frame = (10, y_pos + 25, 230, 30)
        self.basedt_slider.action = self.update_base_dt
        panel.add_subview(self.basedt_slider)

        self.basedt_value = ui.Label()
        self.basedt_value.text = f'{self.base_dt:.3f}'
        self.basedt_value.alignment = ui.ALIGN_RIGHT
        self.basedt_value.frame = (245, y_pos + 25, 45, 30)
        panel.add_subview(self.basedt_value)
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

        # Energie-Referenz initialisieren (ohne Dämpfung)
        try:
            damping = float(self.canvas.params.get('damping', 0.0))
        except Exception:
            damping = 0.0
        if damping == 0.0:
            mode = 'double' if self.canvas.mode == 'double' else 'single'
            try:
                self.energy_ref = self.physics.total_energy(self.canvas.state, self.canvas.params, mode=mode)
            except Exception:
                self.energy_ref = 0.0
        else:
            self.energy_ref = None
        self.energy_err = 0.0
        self._energy_accum = 0.0
        if hasattr(self, 'energy_label'):
            try:
                ui.delay(lambda: setattr(self.energy_label, 'text', 'ΔE/E: 0.000%'), 0)
            except Exception:
                pass
        
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
        try:
            if self.canvas.mode == 'double':
                if hasattr(self, 'start_state') and len(self.start_state) == 4:
                    self.canvas.state = list(self.start_state)
                else:
                    self.canvas.state = [math.radians(45), 0, math.radians(-30), 0]
            else:
                if hasattr(self, 'start_state') and len(self.start_state) >= 2:
                    self.canvas.state = list(self.start_state[:2])
                else:
                    self.canvas.state = [math.radians(45), 0]
        except Exception:
            self.canvas.state = [math.radians(45), 0, math.radians(-30), 0] if self.canvas.mode == 'double' else [math.radians(45), 0]
        # Winkel normalisieren
        self.canvas.state = self.physics.normalize_angles(self.canvas.state)
        
        self.canvas.time = 0.0
        self.canvas.clear_trail()
        self.canvas.clear_marks()
        # Energie-/Integrator-Refs zurücksetzen
        self.energy_ref = None
        self.energy_err = 0.0
        self._energy_accum = 0.0
    
    def simulation_loop(self):
        """Hauptschleife der Simulation"""
        last_time = time.time()
        
        while self.running and not self.stop_flag:
            current_time = time.time()
            elapsed = current_time - last_time
            last_time = current_time
            
            # Zeitschritt anpassen (reale Zeit * Skalierung)
            sim_dt = max(0.0, elapsed * self.time_scale)
            
            # Parameter aktualisieren
            self.update_parameters()
            
            # Physik-Update
            if self.canvas.mode == 'double':
                deriv_func = self.physics.double_pendulum_derivatives
            else:
                deriv_func = self.physics.single_pendulum_derivatives
            
            # Integration mit wählbarem Integrator + Substepping
            if self.integrator == 'rk4':
                dtmx = min(self.dt_max, self.physics.choose_dt_max(self.canvas.state, base_dt=self.base_dt, max_dt=self.dt_max))
                self.canvas.state = self.physics.rk4_integrate_substeps(
                    self.canvas.state, sim_dt, dtmx, self.canvas.params, deriv_func
                )
            else:
                # Symplektischer Euler mit adaptivem dt_max
                dtmx = min(self.dt_max, self.physics.choose_dt_max(self.canvas.state, base_dt=max(0.008, self.base_dt * 2.0), max_dt=self.dt_max))
                steps = max(1, int(math.ceil(abs(sim_dt) / max(1e-9, dtmx))))
                small = float(sim_dt) / steps if steps else 0.0
                s = list(self.canvas.state)
                for _ in range(steps):
                    s = self.physics.symplectic_euler_step(s, small, self.canvas.params, deriv_func)
                self.canvas.state = s
            # Winkel normalisieren (seltener, für stabilere Darstellung)
            self._norm_counter += 1
            if self._norm_counter >= getattr(self, 'normalize_every_n', 1):
                self.canvas.state = self.physics.normalize_angles(self.canvas.state)
                self._norm_counter = 0
            
            self.canvas.time += sim_dt

            # Energie-Überwachung (nur ohne Dämpfung sinnvoll)
            try:
                damping = float(self.canvas.params.get('damping', 0.0))
            except Exception:
                damping = 0.0
            if damping == 0.0:
                mode = 'double' if self.canvas.mode == 'double' else 'single'
                if self.energy_ref is None:
                    try:
                        self.energy_ref = self.physics.total_energy(self.canvas.state, self.canvas.params, mode=mode)
                    except Exception:
                        self.energy_ref = 0.0
                self._energy_accum += sim_dt
                if self._energy_accum >= self.energy_check_interval:
                    self._energy_accum = 0.0
                    try:
                        e = self.physics.total_energy(self.canvas.state, self.canvas.params, mode=mode)
                        e0 = self.energy_ref if self.energy_ref is not None else e
                        denom = max(1e-9, abs(e0))
                        self.energy_err = abs(e - e0) / denom
                    except Exception:
                        self.energy_err = 0.0

                    # Energie-Drift Anzeige aktualisieren
                    if hasattr(self, 'energy_label'):
                        try:
                            txt = f'ΔE/E: {self.energy_err * 100.0:.3f}%'
                            ui.delay(lambda: setattr(self.energy_label, 'text', txt), 0)
                        except Exception:
                            pass

                    # AutoSwitch oder dt_max-Anpassung
                    if self.autoswitch and self.integrator == 'symplectic' and self.energy_err > self.energy_threshold:
                        # Wechsel auf RK4 und Basiswerte setzen, Energie-Referenz neu setzen
                        self.integrator = 'rk4'
                        self.base_dt = 0.004
                        self.dt_max = 0.015
                        self.energy_ref = e
                        if hasattr(self, 'integrator_control'):
                            try:
                                ui.delay(lambda: setattr(self.integrator_control, 'selected_index', 0), 0)
                            except Exception:
                                pass
                        if hasattr(self, 'dtmax_slider'):
                            try:
                                ui.delay(lambda: (setattr(self.dtmax_slider, 'value', self.dt_max), setattr(self.dtmax_value, 'text', f'{self.dt_max:.3f}')), 0)
                            except Exception:
                                pass
                        if hasattr(self, 'basedt_slider'):
                            try:
                                ui.delay(lambda: (setattr(self.basedt_slider, 'value', self.base_dt), setattr(self.basedt_value, 'text', f'{self.base_dt:.3f}')), 0)
                            except Exception:
                                pass
                    else:
                        if self.energy_err > self.energy_threshold * 0.5:
                            self.dt_max = max(0.001, self.dt_max * 0.85)
                        else:
                            upper = 0.015 if self.integrator == 'rk4' else 0.03
                            self.dt_max = min(upper, self.dt_max * 1.05)
                        if hasattr(self, 'dtmax_value'):
                            try:
                                ui.delay(lambda: setattr(self.dtmax_value, 'text', f'{self.dt_max:.3f}'), 0)
                            except Exception:
                                pass
            
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
            # Startzustand anpassen
            self.start_state = list(self.canvas.state)
        else:
            self.canvas.mode = 'single'
            self.canvas.state = self.canvas.state[:2]
            self.l2_field.enabled = False
            self.m2_field.enabled = False
            # Startzustand anpassen
            self.start_state = list(self.canvas.state)
        
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

    def update_dt_max(self, sender):
        """Aktualisiert dt_max aus dem Slider"""
        try:
            self.dt_max = max(0.0005, float(sender.value))
        except Exception:
            pass
        self.dtmax_value.text = f'{self.dt_max:.3f}'

    def update_base_dt(self, sender):
        """Aktualisiert base_dt aus dem Slider"""
        try:
            self.base_dt = max(0.0005, float(sender.value))
        except Exception:
            pass
        self.basedt_value.text = f'{self.base_dt:.3f}'

    def change_integrator(self, sender):
        """Wechselt den Integrator-Modus"""
        idx = getattr(sender, 'selected_index', 0)
        if idx == 0:
            self.integrator = 'rk4'
            self.base_dt = 0.004
            self.dt_max = 0.015
        else:
            self.integrator = 'symplectic'
            self.base_dt = 0.008
            self.dt_max = 0.030
        # Energie-Referenz zurücksetzen
        self.energy_ref = None
        # Slider synchronisieren
        if hasattr(self, 'dtmax_slider'):
            try:
                self.dtmax_slider.value = self.dt_max
                self.dtmax_value.text = f'{self.dt_max:.3f}'
            except Exception:
                pass
        if hasattr(self, 'basedt_slider'):
            try:
                self.basedt_slider.value = self.base_dt
                self.basedt_value.text = f'{self.base_dt:.3f}'
            except Exception:
                pass

    def toggle_autoswitch(self, sender):
        """Schaltet AutoSwitch bei Energie-Drift um"""
        try:
            self.autoswitch = bool(sender.value)
        except Exception:
            self.autoswitch = True
    
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
