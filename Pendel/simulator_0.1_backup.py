# Pendelphysik-Simulation - Überarbeitete Version
# Wissenschaftliche Simulation von Einzel- und Doppelpendeln
# Überarbeitete Benutzeroberfläche mit verbesserter Funktionalität und wissenschaftlichem Design
#
# Features:
# - Physikalisch korrekte Simulation mit RK4-Integrator
# - Interaktive Parametersteuerung
# - Echtzeit-Visualisierung mit Spuren
# - Zeitbasierte Berechnungen und Markierungen
# - Responsive Benutzeroberfläche
# - Wissenschaftliches Design und Layout
#
# Verwendung:
# - Start/Stop: Simulation starten oder pausieren (Button oder Tap auf Zeichenfläche)
# - Reset: Simulation auf Anfangszustand zurücksetzen
# - Parameter: Längen, Massen, Dämpfung und Gravitation anpassen
# - Zeitsteuerung: Geschwindigkeit und automatische Stops
# - Berechnungen: Positionen zu bestimmten Zeitpunkten ermitteln und markieren
#
# Autor: Überarbeitete Version für verbesserte Benutzerfreundlichkeit
# Datum: September 2025

import ui
import math
import time
import threading


# ------------------------ Physik (DGL) -------------------------

def derivs_double(state, params):
    """Ableitung für Doppelpendel.
    state: [theta1, omega1, theta2, omega2]
    Winkel werden von der Vertikalen (nach unten) gemessen.
    """
    th1, w1, th2, w2 = state
    m1 = float(params['m1'])
    m2 = float(params['m2'])
    l1 = float(params['l1'])
    l2 = float(params['l2'])
    g = float(params['g'])
    damping = float(params.get('damping', 0.0))

    delta = th2 - th1

    denom = (2 * m1 + m2 - m2 * math.cos(2 * th1 - 2 * th2))
    if abs(denom) < 1e-9:
        denom = 1e-9

    num1 = -g * (2 * m1 + m2) * math.sin(th1)
    num1 += -m2 * g * math.sin(th1 - 2 * th2)
    num1 += -2 * math.sin(delta) * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * math.cos(delta))
    domega1 = num1 / (l1 * denom)

    num2 = 2 * math.sin(delta) * (w1 * w1 * l1 * (m1 + m2)
                                   + g * (m1 + m2) * math.cos(th1)
                                   + w2 * w2 * l2 * m2 * math.cos(delta))
    domega2 = num2 / (l2 * denom)

    if damping:
        domega1 -= damping * w1
        domega2 -= damping * w2

    return [w1, domega1, w2, domega2]


def derivs_single(state, params):
    """Ableitung für Einfachpendel.
    state: [theta, omega]
    """
    th, w = state
    g = float(params['g'])
    l = float(params['l1'])
    damping = float(params.get('damping', 0.0))
    dth = w
    domega = -(g / max(1e-9, l)) * math.sin(th)
    if damping:
        domega -= damping * w
    return [dth, domega]


def rk4_step(state, dt, params, f):
    """Klassischer RK4-Schritt für beliebig dimensionierten Zustand.
    f(state, params) -> Ableitungen gleicher Länge wie state.
    """
    s1 = state
    k1 = f(s1, params)
    s2 = [s1[i] + 0.5 * dt * k1[i] for i in range(len(s1))]
    k2 = f(s2, params)
    s3 = [s1[i] + 0.5 * dt * k2[i] for i in range(len(s1))]
    k3 = f(s3, params)
    s4 = [s1[i] + dt * k3[i] for i in range(len(s1))]
    k4 = f(s4, params)
    return [s1[i] + dt * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0 for i in range(len(s1))]


# ------------------------ Integratoren & Helfer -----------------

def symplectic_euler_step(state, dt, params, f):
    """Symplektischer Euler-Schritt (semi-implizit).
    Erwartet f(state, params) -> Ableitungen. Nutzt nur die Beschleunigungen.
    """
    n = len(state)
    if n == 4:
        th1, w1, th2, w2 = state
        d = f([th1, w1, th2, w2], params)
        a1 = d[1]
        a2 = d[3]
        w1 = w1 + dt * a1
        w2 = w2 + dt * a2
        th1 = th1 + dt * w1
        th2 = th2 + dt * w2
        return [th1, w1, th2, w2]
    elif n == 2:
        th, w = state
        d = f([th, w], params)
        a = d[1]
        w = w + dt * a
        th = th + dt * w
        return [th, w]
    else:
        # Fallback: klassischer Euler (sollte nicht vorkommen)
        d = f(state, params)
        return [state[i] + dt * d[i] for i in range(n)]


def rk4_integrate_substeps(state, dt_total, dt_max, params, f):
    """Integriert dt_total via RK4 in Teil-Schritten, jeder <= dt_max."""
    steps = max(1, int(math.ceil(abs(dt_total) / max(1e-9, dt_max))))
    dt = float(dt_total) / steps
    s = list(state)
    for _ in range(steps):
        s = rk4_step(s, dt, params, f)
    return s


def choose_dt_max(state, base_dt=0.005, max_dt=0.02):
    """Heuristische Wahl von dt_max basierend auf max. Winkelgeschwindigkeit."""
    if len(state) == 4:
        w_max = max(abs(state[1]), abs(state[3]))
    else:
        w_max = abs(state[1])
    if w_max <= 0.1:
        return max_dt
    dt = min(max_dt, base_dt / (1.0 + w_max))
    return max(1e-4, dt)


def total_energy(state, params, mode='double'):
    """Gesamtenergie (kinetisch + potenziell). Referenz y=0 am Aufhängepunkt."""
    g = float(params['g'])
    if mode == 'double' and len(state) == 4:
        th1, w1, th2, w2 = state
        m1 = float(params['m1']); m2 = float(params['m2'])
        l1 = float(params['l1']); l2 = float(params['l2'])
        # Geschwindigkeiten
        x1dot = l1 * w1 * math.cos(th1)
        y1dot = -l1 * w1 * math.sin(th1)
        x2dot = x1dot + l2 * w2 * math.cos(th2)
        y2dot = y1dot - l2 * w2 * math.sin(th2)
        KE = 0.5 * m1 * (x1dot * x1dot + y1dot * y1dot) + 0.5 * m2 * (x2dot * x2dot + y2dot * y2dot)
        # Potenzial
        y1 = -l1 * math.cos(th1)
        y2 = y1 - l2 * math.cos(th2)
        PE = m1 * g * y1 + m2 * g * y2
        return KE + PE
    else:
        th, w = state[:2]
        m = float(params['m1'])
        l = float(params['l1'])
        xdot = l * w * math.cos(th)
        ydot = -l * w * math.sin(th)
        KE = 0.5 * m * (xdot * xdot + ydot * ydot)
        y = -l * math.cos(th)
        PE = m * g * y
        return KE + PE

# ------------------------ Geometrie ----------------------------

def polar_to_xy(origin, angle, length):
    # Robust handling if origin is accidentally nested (e.g., ((x, y), ...))
    try:
        ox, oy = origin
        if isinstance(ox, (tuple, list)):
            # flatten one nesting level
            ox, oy = ox
        ox = float(ox)
        oy = float(oy)
        angle = float(angle)
        length = float(length)
    except Exception:
        # Best effort fallback
        ox = float(origin[0])
        oy = float(origin[1])
        angle = float(angle)
        length = float(length)
    x = ox + length * math.sin(angle)
    y = oy + length * math.cos(angle)
    return (x, y)


def xy_to_angle(origin, pt):
    dx = pt[0] - origin[0]
    dy = pt[1] - origin[1]
    return math.atan2(dx, dy)


def draw_text_at(text, x, y, *, font=('Helvetica', 12), color='#333333'):
    ui.set_color(color)
    w, h = ui.measure_string(text, font=font)
    ui.draw_string(text, (x, y, w, h), font=font)


# ------------------------ View --------------------------------

class PendulumView(ui.View):
    def __init__(self, model):
        self.model = model
        self.background_color = '#FFFFFF'
        self.dragging = None
        self.trail_points = []  # [(x,y)]
        self.stamps = []  # [{x,y,text}]
        self.max_grid = 60
        # Callbacks
        self.cb_toggle = None
        self.cb_reset = None
        self.cb_change_mode = None
        self.cb_set_speed = None
        self.cb_set_damping = None
        self.cb_toggle_trail = None
        self.cb_clear_trail = None
        self.set_needs_display()

    def attach_callbacks(self, *, on_toggle, on_reset, on_change_mode,
                          on_speed, on_damping, on_toggle_trail, on_clear_trail):
        self.cb_toggle = on_toggle
        self.cb_reset = on_reset
        self.cb_change_mode = on_change_mode
        self.cb_set_speed = on_speed
        self.cb_set_damping = on_damping
        self.cb_toggle_trail = on_toggle_trail
        self.cb_clear_trail = on_clear_trail

    def set_playing(self, playing: bool):
        # no visual control here; panel button handles title
        pass

    def draw(self):
        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)

        # Hintergrund
        ui.set_color('#FFFFFF')
        ui.Path.rect(0, 0, r.w, r.h).fill()

        # feines wissenschaftliches Raster
        ui.set_color((0.92, 0.92, 0.92, 1.0))
        grid = 50
        for x in range(0, int(r.w) + 1, grid):
            p = ui.Path()
            p.line_width = 0.5
            p.move_to(x, 0)
            p.line_to(x, r.h)
            p.stroke()
        for y in range(0, int(r.h) + 1, grid):
            p = ui.Path()
            p.line_width = 0.5
            p.move_to(0, y)
            p.line_to(r.w, y)
            p.stroke()

        # Achsen
        ui.set_color((0.75, 0.75, 0.75, 1.0))
        p = ui.Path()
        p.line_width = 1.0
        p.move_to(cx, 0)
        p.line_to(cx, r.h)
        p.stroke()

        # State lesen und zeichnen
        mode = self.model.mode
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter

        if mode == 'double':
            th1, w1, th2, w2 = self.model.state
            x1, y1 = polar_to_xy(origin, th1, l1)
            x2, y2 = polar_to_xy((x1, y1), th2, l2)
        else:
            th1, w1 = self.model.state
            x1, y1 = polar_to_xy(origin, th1, l1)
            x2, y2 = x1, y1  # für einheitliche Variablen

        # Trails zeichnen
        if self.trail_points and len(self.trail_points) > 1:
            total = len(self.trail_points)
            for i in range(1, total):
                alpha = max(0.08, 0.6 * (i / float(total)))
                ui.set_color((0.12, 0.47, 0.71, alpha))  # Blau
                p = ui.Path()
                p.line_width = 1.5
                p.move_to(self.trail_points[i - 1][0], self.trail_points[i - 1][1])
                p.line_to(self.trail_points[i][0], self.trail_points[i][1])
                p.stroke()

        # Stäbe
        ui.set_color('#424242')
        p = ui.Path()
        p.line_width = 2.0
        p.move_to(origin[0], origin[1])
        p.line_to(x1, y1)
        p.stroke()

        if mode == 'double':
            p2 = ui.Path()
            p2.line_width = 2.0
            p2.move_to(x1, y1)
            p2.line_to(x2, y2)
            p2.stroke()

        # Massen
        r1 = 12
        r2 = 10
        ui.set_color('#1565C0')
        ui.Path.oval(x1 - r1, y1 - r1, r1 * 2, r1 * 2).fill()
        if mode == 'double':
            ui.set_color('#D84315')
            ui.Path.oval(x2 - r2, y2 - r2, r2 * 2, r2 * 2).fill()

        # Aufhängung
        ui.set_color('#212121')
        ui.Path.oval(origin[0] - 4, origin[1] - 4, 8, 8).fill()

        # Stempel (Zeitmarken)
        ui.set_color('#0D47A1')
        for s in self.stamps:
            path = ui.Path.oval(s['x'] - 4, s['y'] - 4, 8, 8)
            path.line_width = 1.2
            path.stroke()
            draw_text_at(s['text'], s['x'] + 8, s['y'] - 10, font=('Helvetica', 10), color='#0D47A1')

        # Zeit-Anzeige
        draw_text_at('t = {:.2f} s'.format(self.model.sim_time), 12, r.h - 28, font=('Helvetica', 14), color='#333333')

    # Interaktion: Drag zum Setzen der Startwinkel, Tap für Play/Pause
    def touch_began(self, touch):
        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)

        mode = self.model.mode
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter
        if mode == 'double':
            th1, w1, th2, w2 = self.model.state
            x1, y1 = polar_to_xy(origin, th1, l1)
            x2, y2 = polar_to_xy((x1, y1), th2, l2)
        else:
            th1, w1 = self.model.state
            x1, y1 = polar_to_xy(origin, th1, l1)
            x2, y2 = x1, y1

        tx, ty = touch.location
        if (tx - x2) ** 2 + (ty - y2) ** 2 < 20 * 20 and self.model.mode == 'double':
            self.dragging = 'bob2'
        elif (tx - x1) ** 2 + (ty - y1) ** 2 < 20 * 20:
            self.dragging = 'bob1'
        else:
            self.dragging = 'maybe_toggle'
            self._tap_started = time.time()

    def touch_moved(self, touch):
        if not self.dragging:
            return

        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)
        tx, ty = touch.location

        if self.dragging == 'bob1':
            th1 = xy_to_angle(origin, (tx, ty))
            if self.model.mode == 'double':
                self.model.state[0] = th1
                self.model.state[1] = 0.0
            else:
                self.model.state[0] = th1
                self.model.state[1] = 0.0
            self.set_needs_display()
        elif self.dragging == 'bob2' and self.model.mode == 'double':
            th1 = self.model.state[0]
            l1 = self.model.params['l1'] * self.model.pixels_per_meter
            x1, y1 = polar_to_xy(origin, th1, l1)
            th2 = xy_to_angle((x1, y1), (tx, ty))
            self.model.state[2] = th2
            self.model.state[3] = 0.0
            self.set_needs_display()
        else:
            # Wenn Finger zu weit bewegt: Kein Tap
            try:
                px, py = touch.prev_location
            except Exception:
                px, py = touch.location
            dx = touch.location[0] - px
            dy = touch.location[1] - py
            if dx * dx + dy * dy > 36:
                self.dragging = None

    def touch_ended(self, touch):
        if self.dragging in ('bob1', 'bob2'):
            self.dragging = None
            return
        if self.dragging == 'maybe_toggle':
            self.dragging = None
            if self.cb_toggle:
                self.cb_toggle(self)


# ------------------------ Model -------------------------------

class PendulumModel(object):
    def __init__(self):
        self.params = {
            'm1': 1.0,
            'm2': 1.0,
            'l1': 1.0,
            'l2': 1.0,
            'g': 9.81,
            'damping': 0.0,
        }
        self.mode = 'double'  # 'double' | 'single'
        self.state = [math.radians(120), 0.0, math.radians(-10), 0.0]
        self.sim_time = 0.0
        self.running = False
        self.time_scale = 1.0
        # Basis-Integrationsparameter
        self.dt = 0.01  # veraltet für alten Loop, bleibt als Fallback
        self.integrator = 'rk4'  # 'rk4' | 'symplectic'
        self.base_dt = 0.005  # RK4 Substep Baseline
        self.dt_max = 0.02  # Obergrenze für Substeps/Schritte
        self.energy_ref = None
        self.energy_err = 0.0
        self.energy_check_interval = 0.5  # in Simulationssekunden
        self._energy_accum = 0.0
        self.autoswitch = True
        self.energy_threshold = 0.1  # 10% erlaubter Fehler bevor Maßnahmen
        self.pixels_per_meter = 180.0
        self.trail_enabled = True
        self.trail_max = 300
        self.stop_at = None

    def set_mode(self, mode: str):
        mode = 'single' if str(mode).lower().startswith('single') or str(mode).lower().startswith('einfach') else 'double'
        if mode == self.mode:
            return
        if mode == 'single':
            # Reduziere auf [th1, w1]
            th1 = self.state[0]
            w1 = self.state[1]
            self.state = [th1, w1]
        else:
            # Erweitere auf Doppelpendel, setze th2/w2 klein
            th1 = self.state[0]
            w1 = self.state[1]
            self.state = [th1, w1, math.radians(-10), 0.0]
        self.mode = mode

    def reset(self):
        if self.mode == 'double':
            self.state = [math.radians(120), 0.0, math.radians(-10), 0.0]
        else:
            self.state = [math.radians(60), 0.0]
        self.sim_time = 0.0
        self.stop_at = None
        self.energy_ref = None
        self.energy_err = 0.0
        self._energy_accum = 0.0

    def step(self, dt):
        # Legacy-Einzelschritt via RK4 für kleine dt (weiterhin für state_at_time genutzt)
        if self.mode == 'double':
            self.state = rk4_step(self.state, dt, self.params, derivs_double)
        else:
            self.state = rk4_step(self.state, dt, self.params, derivs_single)
        self.sim_time += dt

    def integrate(self, dt_total: float):
        # Wähle DGL
        if self.mode == 'double':
            f = derivs_double
            mode = 'double'
        else:
            f = derivs_single
            mode = 'single'

        # Energy-Referenz initialisieren (nur ohne Dämpfung sinnvoll)
        if self.energy_ref is None and float(self.params.get('damping', 0.0)) == 0.0:
            try:
                self.energy_ref = total_energy(self.state, self.params, mode=mode)
            except Exception:
                self.energy_ref = 0.0

        # Integrationsschritte ausführen
        if self.integrator == 'rk4':
            dtmx = min(self.dt_max, choose_dt_max(self.state, base_dt=self.base_dt, max_dt=self.dt_max))
            self.state = rk4_integrate_substeps(self.state, dt_total, dtmx, self.params, f)
        else:
            # Symplektischer Euler, günstig und stabil – ggf. adaptives dt_max
            dtmx = min(self.dt_max, choose_dt_max(self.state, base_dt=max(0.008, self.base_dt * 2.0), max_dt=self.dt_max))
            steps = max(1, int(math.ceil(abs(dt_total) / max(1e-9, dtmx))))
            small = float(dt_total) / steps
            s = list(self.state)
            for _ in range(steps):
                s = symplectic_euler_step(s, small, self.params, f)
            self.state = s

        self.sim_time += dt_total

        # Energie überwachen, bei Dämpfung überspringen
        if float(self.params.get('damping', 0.0)) == 0.0:
            self._energy_accum += dt_total
            if self._energy_accum >= self.energy_check_interval:
                self._energy_accum = 0.0
                try:
                    e = total_energy(self.state, self.params, mode=mode)
                    e0 = self.energy_ref if self.energy_ref is not None else e
                    denom = max(1e-9, abs(e0))
                    self.energy_err = abs(e - e0) / denom
                except Exception:
                    self.energy_err = 0.0

                # Autoadaption / Autoswitch
                if self.autoswitch and self.integrator == 'symplectic' and self.energy_err > self.energy_threshold:
                    self.integrator = 'rk4'
                else:
                    # einfache dt_max-Anpassung
                    if self.energy_err > self.energy_threshold * 0.5:
                        self.dt_max = max(0.001, self.dt_max * 0.8)
                    else:
                        self.dt_max = min(0.05, self.dt_max * 1.05)

    def state_at_time(self, t: float):
        # unabhängige Vorwärtsintegration vom Reset-Zustand
        if self.mode == 'double':
            s = [math.radians(120), 0.0, math.radians(-10), 0.0]
            f = derivs_double
        else:
            s = [math.radians(60), 0.0]
            f = derivs_single
        params = self.params.copy()
        total = max(1, int(abs(t) / 0.005))
        small = float(t) / total
        for _ in range(total):
            s = rk4_step(s, small, params, f)
        return s


# ------------------------ Controller/App ----------------------

class PendulumApp(object):
    def __init__(self):
        self.model = PendulumModel()
        self.view = ui.View(name='Pendel Simulation – Simulator 0.1')
        self.view.background_color = '#FFFFFF'
        self.timer_thread = None
        self._timer_stop = False

        # Layout
        self.draw_view = PendulumView(self.model)
        self.draw_view.flex = 'H'
        self.view.add_subview(self.draw_view)

        self.ctrl = ui.View()
        self.ctrl.flex = 'H'
        self.ctrl.background_color = '#FAFAFA'
        self.view.add_subview(self.ctrl)

        # Steuerelemente aufbauen
        self._build_controls()

        # Coupling callbacks
        self.draw_view.attach_callbacks(on_toggle=self.toggle_run,
                                        on_reset=lambda s: self.reset(),
                                        on_change_mode=self.change_mode,
                                        on_speed=self.update_speed,
                                        on_damping=self.update_damping,
                                        on_toggle_trail=self.toggle_trail,
                                        on_clear_trail=self.clear_trail)

        # Layout callback
        self.view.layout = self._layout_root
        self._layout_root()

    # ---------- UI Aufbau ----------
    def _build_controls(self):
        ctrl = self.ctrl
        y = 16
        pad = 18
        width = 280

        # Titel
        title = ui.Label(frame=(16, y, width - 32, 28))
        title.text = 'Pendel – Wissenschaftliche Steuerung'
        title.font = ('Helvetica-Bold', 14)
        title.text_color = '#222222'
        title.alignment = ui.ALIGN_CENTER
        ctrl.add_subview(title)
        y += 36

        def add_separator(ypos):
            sep = ui.View(frame=(16, ypos, width - 32, 1))
            sep.background_color = '#E0E0E0'
            ctrl.add_subview(sep)

        # Run/Reset
        self.btn_run = ui.Button(frame=(16, y, 120, 36))
        self.btn_run.title = 'Start'
        self.btn_run.font = ('Helvetica', 14)
        self.btn_run.corner_radius = 6
        self.btn_run.background_color = '#2E7D32'
        self.btn_run.tint_color = 'white'
        self.btn_run.action = self.toggle_run
        ctrl.add_subview(self.btn_run)

        btn_reset = ui.Button(frame=(width - 16 - 120, y, 120, 36))
        btn_reset.title = 'Reset'
        btn_reset.font = ('Helvetica', 14)
        btn_reset.corner_radius = 6
        btn_reset.background_color = '#757575'
        btn_reset.tint_color = 'white'
        btn_reset.action = lambda s: self.reset()
        ctrl.add_subview(btn_reset)
        y += 48
        add_separator(y)
        y += 14

        # Modus
        label = ui.Label(frame=(16, y, 80, 20))
        label.text = 'Modus'
        label.text_color = '#555555'
        label.font = ('Helvetica', 12)
        ctrl.add_subview(label)

        self.mode_seg = ui.SegmentedControl(frame=(16, y + 22, width - 32, 28))
        self.mode_seg.segments = ['Doppel', 'Einfach']
        self.mode_seg.selected_index = 0
        self.mode_seg.tint_color = '#1565C0'
        self.mode_seg.action = self.change_mode
        ctrl.add_subview(self.mode_seg)
        y += 60
        add_separator(y)
        y += 14

        # Parameter – Längen
        l1_lbl = ui.Label(frame=(16, y, 100, 20))
        l1_lbl.text = 'Länge 1 (m)'
        l1_lbl.text_color = '#555555'
        l1_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(l1_lbl)
        self.l1_field = ui.TextField(frame=(width - 16 - 80, y, 80, 24))
        self.l1_field.text = '1.0'
        self.l1_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.l1_field.font = ('Menlo', 12)
        self.l1_field.border_width = 1
        self.l1_field.border_color = '#DDDDDD'
        self.l1_field.corner_radius = 4
        ctrl.add_subview(self.l1_field)
        y += 32

        l2_lbl = ui.Label(frame=(16, y, 100, 20))
        l2_lbl.text = 'Länge 2 (m)'
        l2_lbl.text_color = '#555555'
        l2_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(l2_lbl)
        self.l2_field = ui.TextField(frame=(width - 16 - 80, y, 80, 24))
        self.l2_field.text = '1.0'
        self.l2_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.l2_field.font = ('Menlo', 12)
        self.l2_field.border_width = 1
        self.l2_field.border_color = '#DDDDDD'
        self.l2_field.corner_radius = 4
        ctrl.add_subview(self.l2_field)
        y += 36

        # Parameter – Massen
        m1_lbl = ui.Label(frame=(16, y, 100, 20))
        m1_lbl.text = 'Masse 1 (kg)'
        m1_lbl.text_color = '#555555'
        m1_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(m1_lbl)
        self.m1_field = ui.TextField(frame=(width - 16 - 80, y, 80, 24))
        self.m1_field.text = '1.0'
        self.m1_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.m1_field.font = ('Menlo', 12)
        self.m1_field.border_width = 1
        self.m1_field.border_color = '#DDDDDD'
        self.m1_field.corner_radius = 4
        ctrl.add_subview(self.m1_field)
        y += 32

        m2_lbl = ui.Label(frame=(16, y, 100, 20))
        m2_lbl.text = 'Masse 2 (kg)'
        m2_lbl.text_color = '#555555'
        m2_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(m2_lbl)
        self.m2_field = ui.TextField(frame=(width - 16 - 80, y, 80, 24))
        self.m2_field.text = '1.0'
        self.m2_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.m2_field.font = ('Menlo', 12)
        self.m2_field.border_width = 1
        self.m2_field.border_color = '#DDDDDD'
        self.m2_field.corner_radius = 4
        ctrl.add_subview(self.m2_field)
        y += 36
        add_separator(y)
        y += 14

        # Gravitation
        g_lbl = ui.Label(frame=(16, y, 120, 20))
        g_lbl.text = 'Gravitation g (m/s²)'
        g_lbl.text_color = '#555555'
        g_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(g_lbl)
        self.g_slider = ui.Slider(frame=(16, y + 24, width - 90, 20))
        self.g_slider.minimum_value = 1.0
        self.g_slider.maximum_value = 20.0
        self.g_slider.value = 9.81
        self.g_slider.tint_color = '#1565C0'
        self.g_slider.action = lambda s: self.update_g(float(s.value))
        ctrl.add_subview(self.g_slider)
        self.g_val = ui.Label(frame=(width - 64, y + 24, 48, 20))
        self.g_val.alignment = ui.ALIGN_RIGHT
        self.g_val.text = '9.81'
        self.g_val.font = ('Menlo', 12)
        self.g_val.text_color = '#222222'
        ctrl.add_subview(self.g_val)
        y += 54

        # Dämpfung
        damp_lbl = ui.Label(frame=(16, y, 120, 20))
        damp_lbl.text = 'Dämpfung (1/s)'
        damp_lbl.text_color = '#555555'
        damp_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(damp_lbl)
        self.damping_slider = ui.Slider(frame=(16, y + 24, width - 90, 20))
        self.damping_slider.minimum_value = 0.0
        self.damping_slider.maximum_value = 0.1
        self.damping_slider.value = 0.0
        self.damping_slider.tint_color = '#1565C0'
        self.damping_slider.action = lambda s: self.update_damping(float(s.value))
        ctrl.add_subview(self.damping_slider)
        self.damping_val = ui.Label(frame=(width - 64, y + 24, 48, 20))
        self.damping_val.alignment = ui.ALIGN_RIGHT
        self.damping_val.text = '0.00'
        self.damping_val.font = ('Menlo', 12)
        self.damping_val.text_color = '#222222'
        ctrl.add_subview(self.damping_val)
        y += 54
        add_separator(y)
        y += 14

        # Geschwindigkeit
        sp_lbl = ui.Label(frame=(16, y, 120, 20))
        sp_lbl.text = 'Geschwindigkeit'
        sp_lbl.text_color = '#555555'
        sp_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(sp_lbl)
        self.speed_slider = ui.Slider(frame=(16, y + 24, width - 90, 20))
        self.speed_slider.minimum_value = 0.1
        self.speed_slider.maximum_value = 10.0
        self.speed_slider.value = 1.0
        self.speed_slider.tint_color = '#1565C0'
        self.speed_slider.action = lambda s: self.update_speed(float(s.value))
        ctrl.add_subview(self.speed_slider)
        self.speed_val = ui.Label(frame=(width - 64, y + 24, 48, 20))
        self.speed_val.alignment = ui.ALIGN_RIGHT
        self.speed_val.text = '1.0x'
        self.speed_val.font = ('Menlo', 12)
        self.speed_val.text_color = '#222222'
        ctrl.add_subview(self.speed_val)
        y += 54
        add_separator(y)
        y += 14

        # Integrator-Modus
        int_lbl = ui.Label(frame=(16, y, 160, 20))
        int_lbl.text = 'Integrator'
        int_lbl.text_color = '#555555'
        int_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(int_lbl)
        self.int_seg = ui.SegmentedControl(frame=(16, y + 22, width - 32, 28))
        self.int_seg.segments = ['Accurate (RK4)', 'Fast (Symplectic)']
        self.int_seg.selected_index = 0
        self.int_seg.tint_color = '#1565C0'
        self.int_seg.action = self.change_integrator
        ctrl.add_subview(self.int_seg)
        y += 60
        add_separator(y)
        y += 14

        # AutoSwitch
        auto_lbl = ui.Label(frame=(16, y, 200, 24))
        auto_lbl.text = 'AutoSwitch bei Energie-Drift'
        auto_lbl.font = ('Helvetica', 12)
        auto_lbl.text_color = '#555555'
        ctrl.add_subview(auto_lbl)
        self.autosw_switch = ui.Switch(frame=(width - 16 - 60, y, 60, 24))
        self.autosw_switch.value = True
        self.autosw_switch.action = lambda s: self.toggle_autoswitch(bool(s.value))
        ctrl.add_subview(self.autosw_switch)
        y += 36
        add_separator(y)
        y += 14

        # Spur
        trail_lbl = ui.Label(frame=(16, y, 80, 24))
        trail_lbl.text = 'Spur'
        trail_lbl.font = ('Helvetica', 12)
        trail_lbl.text_color = '#555555'
        ctrl.add_subview(trail_lbl)
        self.trail_switch = ui.Switch(frame=(70, y, 60, 24))
        self.trail_switch.value = True
        self.trail_switch.action = lambda s: self.toggle_trail(bool(s.value))
        ctrl.add_subview(self.trail_switch)
        btn_clear = ui.Button(frame=(140, y, width - 156, 24))
        btn_clear.title = 'Clear Trail'
        btn_clear.font = ('Helvetica', 11)
        btn_clear.corner_radius = 4
        btn_clear.background_color = '#E0E0E0'
        btn_clear.tint_color = '#333333'
        btn_clear.action = lambda s: self.clear_trail()
        ctrl.add_subview(btn_clear)
        y += 36
        add_separator(y)
        y += 14

        # Zeitsteuerung
        stop_lbl = ui.Label(frame=(16, y, 100, 20))
        stop_lbl.text = 'Stop bei t (s)'
        stop_lbl.text_color = '#555555'
        stop_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(stop_lbl)
        self.stop_field = ui.TextField(frame=(width - 16 - 80, y, 80, 24))
        self.stop_field.placeholder = 'z.B. 10'
        self.stop_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.stop_field.font = ('Menlo', 12)
        self.stop_field.border_width = 1
        self.stop_field.border_color = '#DDDDDD'
        self.stop_field.corner_radius = 4
        ctrl.add_subview(self.stop_field)
        y += 36

        calc_lbl = ui.Label(frame=(16, y, 100, 20))
        calc_lbl.text = 'Markiere t (s)'
        calc_lbl.text_color = '#555555'
        calc_lbl.font = ('Helvetica', 12)
        ctrl.add_subview(calc_lbl)
        self.compute_field = ui.TextField(frame=(16, y + 24, 80, 24))
        self.compute_field.placeholder = 'z.B. 3.5'
        self.compute_field.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
        self.compute_field.font = ('Menlo', 12)
        self.compute_field.border_width = 1
        self.compute_field.border_color = '#DDDDDD'
        self.compute_field.corner_radius = 4
        ctrl.add_subview(self.compute_field)
        btn_mark = ui.Button(frame=(106, y + 24, width - 122, 24))
        btn_mark.title = 'Mark'
        btn_mark.font = ('Helvetica', 11)
        btn_mark.corner_radius = 4
        btn_mark.background_color = '#FF9800'
        btn_mark.tint_color = 'white'
        btn_mark.action = self.compute_and_stamp
        ctrl.add_subview(btn_mark)
        y += 54

        self.stamps_log = ui.TextView(frame=(16, y, width - 32, 120))
        self.stamps_log.editable = False
        self.stamps_log.font = ('Menlo', 10)
        self.stamps_log.background_color = '#F5F5F5'
        self.stamps_log.corner_radius = 4
        ctrl.add_subview(self.stamps_log)

    # ---------- Layout ----------
    def _layout_root(self, *args, **kwargs):
        r = self.view.bounds
        total_w, total_h = r.w, r.h
        ctrl_w = 300
        spacing = 12
        side_pad = 12

        # Safe-Area berücksichtigen (sofern verfügbar)
        insets = getattr(self.view, 'safe_area_insets', None)
        try:
            inset_left = float(getattr(insets, 'left', 0) or 0)
            inset_right = float(getattr(insets, 'right', 0) or 0)
            inset_top = float(getattr(insets, 'top', 0) or 0)
            inset_bottom = float(getattr(insets, 'bottom', 0) or 0)
        except Exception:
            inset_left = inset_right = inset_top = inset_bottom = 0.0

        if total_w >= 980:
            # Zwei Spalten: Zeichenfläche links, Steuerpanel rechts mit Abstand
            left_x = side_pad + inset_left
            ctrl_x = total_w - inset_right - side_pad - ctrl_w
            draw_w = max(100, ctrl_x - spacing - left_x)
            self.draw_view.frame = (left_x, 0, draw_w, total_h)
            self.ctrl.frame = (ctrl_x, 0, ctrl_w, total_h)
        else:
            # Gestapelt untereinander auf kleineren Displays
            ctrl_h = min(420, total_h * 0.48)
            content_w = max(100, total_w - side_pad - inset_left - side_pad - inset_right)
            left_x = side_pad + inset_left
            self.draw_view.frame = (left_x, 0, content_w, total_h - ctrl_h)
            self.ctrl.frame = (left_x, total_h - ctrl_h, content_w, ctrl_h)

    # ---------- Controller-Aktionen ----------
    def toggle_run(self, sender):
        if self.model.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.model.running:
            return
        self.model.running = True
        self.btn_run.title = 'Pause'
        self.btn_run.background_color = '#EF6C00'
        self._start_timer()
        self.draw_view.set_playing(True)

    def pause(self):
        self.model.running = False
        self.btn_run.title = 'Start'
        self.btn_run.background_color = '#2E7D32'
        self._stop_timer()
        self.draw_view.set_playing(False)

    def reset(self):
        self.model.reset()
        self.draw_view.trail_points = []
        self.draw_view.stamps = []
        self.stamps_log.text = ''
        self.draw_view.set_needs_display()

    def change_mode(self, sender):
        idx = getattr(sender, 'selected_index', 0)
        if idx == 1:
            self.model.set_mode('single')
            # Felder für l2/m2 deaktivieren
            self.l2_field.enabled = False
            self.m2_field.enabled = False
        else:
            self.model.set_mode('double')
            self.l2_field.enabled = True
            self.m2_field.enabled = True

    def update_speed(self, val: float):
        val = max(0.1, float(val))
        self.model.time_scale = val
        self.speed_val.text = '{:.1f}x'.format(val)

    def change_integrator(self, sender):
        idx = getattr(sender, 'selected_index', 0)
        if idx == 0:
            self.model.integrator = 'rk4'
            # Präzisere Voreinstellungen
            self.model.base_dt = 0.004
            self.model.dt_max = 0.015
        else:
            self.model.integrator = 'symplectic'
            # Schnellere, robuste Voreinstellungen
            self.model.base_dt = 0.008
            self.model.dt_max = 0.035
        # Energie-Referenz neu setzen bei Moduswechsel
        self.model.energy_ref = None

    def update_damping(self, val: float):
        val = max(0.0, float(val))
        self.model.params['damping'] = val
        self.damping_val.text = '{:.2f}'.format(val)

    def update_g(self, val: float):
        self.model.params['g'] = float(val)
        self.g_val.text = '{:.2f}'.format(val)

    def toggle_trail(self, enabled: bool):
        self.model.trail_enabled = bool(enabled)
        if not enabled:
            self.clear_trail()

    def toggle_autoswitch(self, enabled: bool):
        self.model.autoswitch = bool(enabled)

    def clear_trail(self):
        self.draw_view.trail_points = []
        self.draw_view.set_needs_display()

    def set_stop_time(self, sender=None):
        try:
            v = float(self.stop_field.text)
            if v <= 0:
                self.model.stop_at = None
            else:
                self.model.stop_at = v
        except Exception:
            self.model.stop_at = None

    def _apply_param_fields(self):
        # Übernimmt Textfelder in params (mit Fallbacks)
        try:
            self.model.params['l1'] = max(1e-6, float(self.l1_field.text))
        except Exception:
            pass
        try:
            self.model.params['l2'] = max(1e-6, float(self.l2_field.text))
        except Exception:
            pass
        try:
            self.model.params['m1'] = max(1e-6, float(self.m1_field.text))
        except Exception:
            pass
        try:
            self.model.params['m2'] = max(0.0, float(self.m2_field.text))
        except Exception:
            pass

    def compute_and_stamp(self, sender):
        # Anwenden aktueller Parameter
        self._apply_param_fields()
        # Stop-Grenze übernehmen
        self.set_stop_time()

        try:
            t = float(self.compute_field.text)
        except Exception:
            return

        s = self.model.state_at_time(t)
        r = self.draw_view.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter

        if self.model.mode == 'double':
            x1, y1 = polar_to_xy(origin, s[0], l1)
            x2, y2 = polar_to_xy((x1, y1), s[2], l2)
            px, py = x2, y2
        else:
            x1, y1 = polar_to_xy(origin, s[0], l1)
            px, py = x1, y1

        stamp = {'x': px, 'y': py, 'text': 't={:.2f}s'.format(t)}
        self.draw_view.stamps.append(stamp)
        entry = 't={:.2f}s: x={:.3f} m, y={:.3f} m\n'.format(
            t, px / self.model.pixels_per_meter, py / self.model.pixels_per_meter)
        self.stamps_log.text = entry + self.stamps_log.text
        self.draw_view.set_needs_display()

    # ---------- Timer/Loop ----------
    def _start_timer(self):
        if self.timer_thread:
            return
        self._timer_stop = False

        def loop():
            last = time.time()
            while self.model.running and not self._timer_stop:
                now = time.time()
                real_dt = now - last
                last = now
                dt = real_dt * self.model.time_scale

                # Parameter ggf. übernehmen (sanft):
                self._apply_param_fields()
                self.set_stop_time()

                # Integriere mit neuem Integrator + Substepping intern
                try:
                    self.model.integrate(dt)
                except Exception:
                    # Fallback auf alten kleinen Step, falls etwas schief geht
                    steps = max(1, int(dt / max(1e-4, self.model.dt)))
                    small = dt / steps
                    for _ in range(steps):
                        self.model.step(small)

                # Trail aktualisieren
                r = self.draw_view.bounds
                cx = r.w * 0.5
                cy = r.h * 0.15
                origin = (cx, cy)
                l1 = self.model.params['l1'] * self.model.pixels_per_meter
                l2 = self.model.params['l2'] * self.model.pixels_per_meter
                if self.model.mode == 'double':
                    x1, y1 = polar_to_xy(origin, self.model.state[0], l1)
                    x2, y2 = polar_to_xy((x1, y1), self.model.state[2], l2)
                    px, py = x2, y2
                else:
                    x1, y1 = polar_to_xy(origin, self.model.state[0], l1)
                    px, py = x1, y1

                if self.model.trail_enabled:
                    self.draw_view.trail_points.append((px, py))
                    if len(self.draw_view.trail_points) > self.model.trail_max:
                        self.draw_view.trail_points.pop(0)
                    # Kopie für sicheren Draw
                    self.draw_view.trail_points = list(self.draw_view.trail_points)

                # Auto-Stop
                if self.model.stop_at is not None and self.model.sim_time >= self.model.stop_at:
                    ui.delay(lambda: self.pause(), 0)
                    break

                # Redraw im Hauptthread + Energieanzeige evtl. künftig
                ui.delay(self.draw_view.set_needs_display, 0)
                time.sleep(0.016)

        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()
        self.timer_thread = t

    def _stop_timer(self):
        self._timer_stop = True
        self.timer_thread = None

    # ---------- Start ----------
    def present(self):
        self.view.present('fullscreen', hide_title_bar=False)


if __name__ == '__main__':
    app = PendulumApp()
    app.present()

