# Pendelphysik-Simulation - Minimalistisches Design
# Wissenschaftliche Simulation von Einzel- und Doppelpendeln
# Minimalistisches UI-Design mit verbesserter Fehlerbehandlung
#
# Features:
# - Physikalisch korrekte Simulation mit RK4-Integrator
# - Interaktive Parametersteuerung
# - Echtzeit-Visualisierung mit Spuren
# - Zeitbasierte Berechnungen und Markierungen
# - Minimalistisches, klares Design
#
# Verwendung:
# - Start/Stop: Simulation starten oder pausieren
# - Reset: Simulation auf Anfangszustand zurücksetzen
# - Parameter: Längen, Massen, Dämpfung und Gravitation anpassen
# - Zeitsteuerung: Geschwindigkeit und automatische Stops
# - Berechnungen: Positionen zu bestimmten Zeitpunkten ermitteln
#
# Autor: Überarbeitete Version für minimalistisches Design
# Datum: September 2025
#
# ---------------------------------------------------------------
import ui
import math
import time
import threading

# ---------- Physik: Doppelpendel-DGL (RK4) --------------------

def derivs(state, params):
    # state = [th1, w1, th2, w2]
    th1, w1, th2, w2 = state
    m1 = params['m1']; m2 = params['m2']
    l1 = params['l1']; l2 = params['l2']
    g = params['g']
    damping = params.get('damping', 0.0)

    delta = th2 - th1

    denom1 = (2*m1 + m2 - m2 * math.cos(2*th1 - 2*th2))
    denom2 = (2*m1 + m2 - m2 * math.cos(2*th1 - 2*th2))

    # avoid division by zero
    if abs(denom1) < 1e-6: denom1 = 1e-6
    if abs(denom2) < 1e-6: denom2 = 1e-6

    num1 = -g*(2*m1 + m2)*math.sin(th1)
    num1 += -m2*g*math.sin(th1 - 2*th2)
    num1 += -2*math.sin(delta)*m2*(w2*w2*l2 + w1*w1*l1*math.cos(delta))
    domega1 = num1 / (l1 * denom1)

    num2 = 2*math.sin(delta)*(w1*w1*l1*(m1+m2) + g*(m1+m2)*math.cos(th1) + w2*w2*l2*m2*math.cos(delta))
    domega2 = num2 / (l2 * denom2)

    # simple viscous damping on angular velocities
    if damping:
        domega1 -= damping * w1
        domega2 -= damping * w2

    return [w1, domega1, w2, domega2]


def rk4_step(state, dt, params):
    # classic RK4
    s1 = state
    k1 = derivs(s1, params)
    s2 = [s1[i] + 0.5*dt*k1[i] for i in range(4)]
    k2 = derivs(s2, params)
    s3 = [s1[i] + 0.5*dt*k2[i] for i in range(4)]
    k3 = derivs(s3, params)
    s4 = [s1[i] + dt*k3[i] for i in range(4)]
    k4 = derivs(s4, params)
    new = [s1[i] + dt*(k1[i] + 2*k2[i] + 2*k3[i] + k4[i])/6.0 for i in range(4)]
    return new

# Single pendulum special-case: set m2=0 effectively

# ---------- Hilfsfunktionen -----------------------------------

def polar_to_xy(origin, angle, length):
    # Robust gegen versehentlich verschachtelte Tupel
    try:
        ox, oy = origin
        if isinstance(ox, (tuple, list)):
            ox, oy = ox
        ox = float(ox)
        oy = float(oy)
        angle = float(angle)
        length = float(length)
    except Exception:
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
    # angle measured from vertical downwards (0 = down)
    angle = math.atan2(dx, dy)
    return angle

def draw_text_at(text, x, y, font=('Helvetica', 12)):
    # Helper: draw text at (x,y)
    if '\n' in text:
        # Render each line underneath the previous one
        lines = text.split('\n')
        line_height = ui.measure_string('Ag', font=font)[1]
        for idx, line in enumerate(lines):
            w, h = ui.measure_string(line, font=font)
            ui.draw_string(line, (x, y + idx * line_height, w, h), font=font)
    else:
        w, h = ui.measure_string(text, font=font)
        ui.draw_string(text, (x, y, w, h), font=font)

# ---------- Visual/Simulation View -----------------------------

class PendulumView(ui.View):
    def __init__(self, model):
        self.model = model
        self.background_color = '#FAFAFA'
        self.set_needs_display()
        # for dragging
        self.dragging = None
        self._tap_candidate = False
        self._tap_start = 0.0
        # prepare double-buffer-like trail storage
        self.trail = []  # list of (x,y)
        # stamps: list of dicts with x,y,text
        self.stamps = []
        # callbacks (assigned by controller)
        self.cb_toggle = None
        self.cb_reset = None
        self.cb_change_mode = None
        self.cb_update_speed = None
        self.cb_update_damping = None
        self.cb_toggle_trail = None
        self.cb_clear_trail = None

        # build minimalistic HUD overlay
        self._build_hud()

    def _build_hud(self):
        # Minimalistisches HUD mit klarem Design
        hud = ui.View()
        hud.background_color = (1, 1, 1, 0.85)  # Weißer, semi-transparenter Hintergrund
        hud.corner_radius = 8
        hud.border_width = 0  # Kein Rahmen für cleanen Look
        hud.frame = (12, 12, 280, 140)  # Kompakter
        hud.flex = 'RB'

        y = 12

        # Simulationssteuerung - minimalistisch
        control_row = ui.View(frame=(8, y, 264, 32))

        # Start/Stop Button
        self.btn_play = ui.Button(frame=(0, 0, 60, 32))
        self.btn_play.title = 'Start'
        self.btn_play.font = ('Helvetica', 13)
        self.btn_play.corner_radius = 4
        self.btn_play.background_color = '#4CAF50'
        self.btn_play.tint_color = 'white'
        self.btn_play.action = lambda s: self.cb_toggle and self.cb_toggle(s)
        control_row.add_subview(self.btn_play)

        # Reset Button
        btn_reset = ui.Button(frame=(68, 0, 60, 32))
        btn_reset.title = 'Reset'
        btn_reset.font = ('Helvetica', 13)
        btn_reset.corner_radius = 4
        btn_reset.background_color = '#757575'
        btn_reset.tint_color = 'white'
        btn_reset.action = lambda s: self.cb_reset and self.cb_reset(s)
        control_row.add_subview(btn_reset)

        # Modus-Toggle (vereinfacht)
        self.mode_btn = ui.Button(frame=(136, 0, 128, 32))
        self.mode_btn.title = 'Doppelpendel'
        self.mode_btn.font = ('Helvetica', 12)
        self.mode_btn.corner_radius = 4
        self.mode_btn.background_color = '#2196F3'
        self.mode_btn.tint_color = 'white'
        self.mode_btn.action = self._toggle_mode
        control_row.add_subview(self.mode_btn)

        hud.add_subview(control_row)
        y += 40

        # Geschwindigkeit - minimalistisch
        speed_label = ui.Label(frame=(8, y, 60, 20))
        speed_label.text = 'Speed:'
        speed_label.font = ('Helvetica', 12)
        speed_label.text_color = '#333333'
        hud.add_subview(speed_label)

        self.speed_val_lbl = ui.Label(frame=(224, y, 48, 20))
        self.speed_val_lbl.alignment = ui.ALIGN_RIGHT
        self.speed_val_lbl.font = ('Helvetica-Bold', 12)
        self.speed_val_lbl.text = '1.0x'
        self.speed_val_lbl.text_color = '#333333'
        hud.add_subview(self.speed_val_lbl)

        self.speed_slider_small = ui.Slider(frame=(68, y, 154, 20))
        self.speed_slider_small.minimum_value = 0.1
        self.speed_slider_small.maximum_value = 3.0
        self.speed_slider_small.value = 1.0
        self.speed_slider_small.tint_color = '#2196F3'
        def on_speed(s):
            val = max(0.1, float(s.value))
            self.speed_val_lbl.text = '{:.1f}x'.format(val)
            if self.cb_update_speed:
                self.cb_update_speed(val)
        self.speed_slider_small.action = on_speed
        hud.add_subview(self.speed_slider_small)

        y += 28

        # Dämpfung - minimalistisch
        damp_label = ui.Label(frame=(8, y, 60, 20))
        damp_label.text = 'Damp:'
        damp_label.font = ('Helvetica', 12)
        damp_label.text_color = '#333333'
        hud.add_subview(damp_label)

        self.damp_val_lbl = ui.Label(frame=(224, y, 48, 20))
        self.damp_val_lbl.alignment = ui.ALIGN_RIGHT
        self.damp_val_lbl.font = ('Helvetica-Bold', 12)
        self.damp_val_lbl.text = '0.00'
        self.damp_val_lbl.text_color = '#333333'
        hud.add_subview(self.damp_val_lbl)

        self.damp_slider = ui.Slider(frame=(68, y, 154, 20))
        self.damp_slider.minimum_value = 0.0
        self.damp_slider.maximum_value = 0.1
        self.damp_slider.value = 0.0
        self.damp_slider.tint_color = '#2196F3'
        def on_damp(s):
            val = max(0.0, float(s.value))
            self.damp_val_lbl.text = '{:.2f}'.format(val)
            if self.cb_update_damping:
                self.cb_update_damping(val)
        self.damp_slider.action = on_damp
        hud.add_subview(self.damp_slider)

        y += 28

        # Spur-Steuerung - minimalistisch
        trail_label = ui.Label(frame=(8, y, 40, 24))
        trail_label.text = 'Trail:'
        trail_label.font = ('Helvetica', 12)
        trail_label.text_color = '#333333'
        hud.add_subview(trail_label)

        self.trail_switch = ui.Switch(frame=(48, y, 56, 24))
        self.trail_switch.value = True
        self.trail_switch.tint_color = '#2196F3'
        self.trail_switch.action = lambda s: self.cb_toggle_trail and self.cb_toggle_trail(bool(s.value))
        hud.add_subview(self.trail_switch)

        # Clear Trail Button
        btn_clear = ui.Button(frame=(112, y, 60, 24))
        btn_clear.title = 'Clear'
        btn_clear.font = ('Helvetica', 11)
        btn_clear.corner_radius = 4
        btn_clear.background_color = '#E0E0E0'
        btn_clear.tint_color = '#333333'
        btn_clear.action = lambda s: self.cb_clear_trail and self.cb_clear_trail()
        hud.add_subview(btn_clear)

        self.add_subview(hud)
        self.hud = hud

    def _toggle_mode(self, sender):
        # Toggle zwischen Doppel- und Einfachpendel
        if self.mode_btn.title == 'Doppelpendel':
            self.mode_btn.title = 'Einfachpendel'
            if self.cb_change_mode:
                # Simuliere SegmentedControl mit selected_index = 1
                class FakeSender:
                    selected_index = 1
                self.cb_change_mode(FakeSender())
        else:
            self.mode_btn.title = 'Doppelpendel'
            if self.cb_change_mode:
                # Simuliere SegmentedControl mit selected_index = 0
                class FakeSender:
                    selected_index = 0
                self.cb_change_mode(FakeSender())

    def set_playing(self, playing):
        self.btn_play.title = 'Pause' if playing else 'Start'
        self.btn_play.background_color = '#FF9800' if playing else '#4CAF50'

    def draw(self):
        # drawing callback - minimalistisches Design
        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15  # pivot near top
        origin = (cx, cy)

        # Klarer, weißer Hintergrund
        ui.set_color('#FAFAFA')
        ui.Path.rect(0, 0, r.w, r.h).fill()

        # Sehr dezentes Gitter
        ui.set_color((0.9, 0.9, 0.9, 0.5))
        grid_spacing = 50
        for x in range(0, int(r.w), grid_spacing):
            path = ui.Path()
            path.line_width = 0.5
            path.move_to(x, 0)
            path.line_to(x, r.h)
            path.stroke()
        for y in range(0, int(r.h), grid_spacing):
            path = ui.Path()
            path.line_width = 0.5
            path.move_to(0, y)
            path.line_to(r.w, y)
            path.stroke()

        # compute bob positions from model state
        th1, w1, th2, w2 = self.model.state
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter

        x1, y1 = polar_to_xy(origin, th1, l1)
        x2, y2 = polar_to_xy((x1,y1), th2, l2)

        # draw trails (for second bob) - minimalistisch
        if self.trail and len(self.trail) > 1:
            # Fehlerbehandlung für ui.Path
            try:
                for i in range(1, len(self.trail)):
                    alpha = max(0.1, 0.5 * (i / len(self.trail)))
                    ui.set_color((0.13, 0.59, 0.95, alpha))  # Blau mit Transparenz
                    path = ui.Path()
                    if path is not None:  # Überprüfung ob Path erstellt wurde
                        path.line_width = 1.5
                        path.move_to(self.trail[i-1][0], self.trail[i-1][1])
                        path.line_to(self.trail[i][0], self.trail[i][1])
                        path.stroke()
            except Exception as e:
                # Fehler ignorieren und weitermachen
                pass

        # rods - minimalistisch
        ui.set_color('#424242')

        # Erste Stange
        try:
            p = ui.Path()
            if p is not None:
                p.line_width = 2
                p.move_to(origin[0], origin[1])
                p.line_to(x1, y1)
                p.stroke()
        except:
            pass

        # Zweite Stange
        try:
            p2 = ui.Path()
            if p2 is not None:
                p2.line_width = 2
                p2.move_to(x1, y1)
                p2.line_to(x2, y2)
                p2.stroke()
        except:
            pass

        # bobs - minimalistisches Design
        r1 = 12
        r2 = 10

        # Erste Masse
        ui.set_color('#2196F3')  # Material Blue
        ui.Path.oval(x1-r1, y1-r1, r1*2, r1*2).fill()

        # Zweite Masse
        ui.set_color('#FF5722')  # Material Deep Orange
        ui.Path.oval(x2-r2, y2-r2, r2*2, r2*2).fill()

        # show pivot - minimalistisch
        ui.set_color('#424242')
        ui.Path.oval(origin[0]-4, origin[1]-4, 8, 8).fill()

        # draw stamps - Zeitmarkierungen
        ui.set_color('#2196F3')
        for s in self.stamps:
            path = ui.Path.oval(s['x']-4, s['y']-4, 8, 8)
            path.line_width = 1.5
            path.stroke()
            draw_text_at(s['text'], s['x']+8, s['y']-8, font=('Helvetica', 10))

        # Zeit-Anzeige - minimalistisch
        ui.set_color('#424242')
        time_text = 't = {:.2f} s'.format(self.model.sim_time)
        draw_text_at(time_text, 12, r.h - 30, font=('Helvetica', 14))

    # Touch handling: allow dragging of first or second bob to set start angles
    def touch_began(self, touch):
        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)
        th1, w1, th2, w2 = self.model.state
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter
        x1, y1 = polar_to_xy(origin, th1, l1)
        x2, y2 = polar_to_xy((x1,y1), th2, l2)

        tx, ty = touch.location
        if (tx-x2)**2 + (ty-y2)**2 < 20*20:
            self.dragging = 'bob2'
        elif (tx-x1)**2 + (ty-y1)**2 < 20*20:
            self.dragging = 'bob1'
        else:
            self.dragging = None
            self._tap_candidate = True
            try:
                self._tap_start = touch.timestamp
            except Exception:
                self._tap_start = time.time()

    def touch_moved(self, touch):
        if not self.dragging:
            # if finger moves too far, cancel tap candidate
            try:
                px, py = touch.prev_location
            except Exception:
                px, py = touch.location
            dx = touch.location[0] - px
            dy = touch.location[1] - py
            if dx*dx + dy*dy > 36:
                self._tap_candidate = False
            return
        r = self.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)
        tx, ty = touch.location

        if self.dragging == 'bob1':
            # set th1 from origin->touch
            th1 = xy_to_angle(origin, (tx,ty))
            # update state angles, zero velocities
            self.model.state[0] = th1
            self.model.state[1] = 0.0
            # also update second bob position to keep geometry (keep current th2)
            self.set_needs_display()
        elif self.dragging == 'bob2':
            # compute angle of second relative to first bob's position
            th1 = self.model.state[0]
            l1 = self.model.params['l1'] * self.model.pixels_per_meter
            x1, y1 = polar_to_xy(origin, th1, l1)
            th2 = xy_to_angle((x1,y1), (tx,ty))
            self.model.state[2] = th2
            self.model.state[3] = 0.0
            self.set_needs_display()

    def touch_ended(self, touch):
        if self.dragging:
            self.dragging = None
            return
        # toggle play/pause on simple tap
        if self._tap_candidate:
            self._tap_candidate = False
            if self.cb_toggle:
                self.cb_toggle(self)
        self.dragging = None

    # hooks from controller
    def attach_callbacks(self, *, on_toggle, on_reset, on_change_mode, on_speed, on_damping, on_toggle_trail, on_clear_trail):
        self.cb_toggle = on_toggle
        self.cb_reset = on_reset
        self.cb_change_mode = on_change_mode
        self.cb_update_speed = on_speed
        self.cb_update_damping = on_damping
        self.cb_toggle_trail = on_toggle_trail
        self.cb_clear_trail = on_clear_trail

        # sync HUD initial values
        self.speed_slider_small.value = 1.0
        self.speed_val_lbl.text = '1.0x'
        self.damp_slider.value = 0.0
        self.damp_val_lbl.text = '0.00'

# ---------- Model (zustand + simulation-loop) ------------------

class PendulumModel(object):
    def __init__(self):
        # physical parameters (SI units)
        self.params = {
            'm1': 1.0,
            'm2': 1.0,
            'l1': 1.0,   # meters
            'l2': 1.0,
            'g': 9.81,
            'damping': 0.0
        }
        # initial state: theta measured from vertical (downwards)
        self.state = [math.radians(120), 0.0, math.radians(-10), 0.0]
        self.sim_time = 0.0
        self.running = False
        self.time_scale = 1.0  # speed multiplier
        self.dt = 0.01  # base timestep for integrator
        self.pixels_per_meter = 180.0  # scaling for drawing
        self.trail_max = 300
        self.trail = []
        self.trail_enabled = True
        self.stop_at = None  # if set, simulation will stop at this sim_time

    def step(self, dt):
        # advance by dt (already includes time_scale externally)
        self.state = rk4_step(self.state, dt, self.params)
        self.sim_time += dt

    def reset(self):
        self.state = [math.radians(120), 0.0, math.radians(-10), 0.0]
        self.sim_time = 0.0
        self.trail = []
        self.stop_at = None

    def single_step_silent(self, t):
        # compute state at given time (from initial state) and stamp on the scene
        s = [math.radians(120), 0.0, math.radians(-10), 0.0]
        params = self.params.copy()
        dt = 0.005
        steps = max(1, int(abs(t) / dt))
        dt = t / steps
        for i in range(steps):
            s = rk4_step(s, dt, params)
        return s

# ---------- Controller / App ----------------------------------

class PendulumApp(object):
    def __init__(self):
        self.model = PendulumModel()
        # root view with responsive layout
        self.view = ui.View()
        self.view.name = 'Pendel Simulation'
        self.view.background_color = '#FAFAFA'
        self.setup_layout()
        self.running = False
        # periodic timer
        self.timer = None

    def setup_layout(self):
        # Minimalistisches Layout
        self.draw_view = PendulumView(self.model)
        self.draw_view.frame = (0, 0, 700, 700)
        self.draw_view.flex = 'WH'
        self.view.add_subview(self.draw_view)

        # Minimalistischer Kontrollbereich
        ctrl_width = 280
        ctrl = ui.View(frame=(700, 0, ctrl_width, 700))
        ctrl.flex = 'LH'
        ctrl.background_color = '#FFFFFF'

        y = 20

        # Titel
        title_label = ui.Label(frame=(20, y, ctrl_width-40, 30))
        title_label.text = 'PENDEL SIMULATION'
        title_label.font = ('Helvetica-Bold', 16)
        title_label.text_color = '#333333'
        title_label.alignment = ui.ALIGN_CENTER
        y += 40

        # Separator
        sep = ui.View(frame=(20, y, ctrl_width-40, 1))
        sep.background_color = '#E0E0E0'
        ctrl.add_subview(sep)
        y += 20

        # Hauptsteuerung
        self.btn_run = ui.Button(frame=(20, y, 110, 36))
        self.btn_run.title = 'Start'
        self.btn_run.font = ('Helvetica', 14)
        self.btn_run.corner_radius = 4
        self.btn_run.background_color = '#4CAF50'
        self.btn_run.tint_color = 'white'
        self.btn_run.action = self.toggle_run
        ctrl.add_subview(self.btn_run)

        btn_reset = ui.Button(frame=(140, y, 110, 36))
        btn_reset.title = 'Reset'
        btn_reset.font = ('Helvetica', 14)
        btn_reset.corner_radius = 4
        btn_reset.background_color = '#757575'
        btn_reset.tint_color = 'white'
        btn_reset.action = lambda sender: self.reset()
        ctrl.add_subview(btn_reset)
        y += 50

        # Modus
        mode_label = ui.Label(frame=(20, y, 100, 20))
        mode_label.text = 'Modus:'
        mode_label.font = ('Helvetica', 13)
        mode_label.text_color = '#666666'
        ctrl.add_subview(mode_label)

        self.mode_seg = ui.SegmentedControl(frame=(20, y+24, ctrl_width-40, 32))
        self.mode_seg.segments = ['Doppel', 'Einfach']
        self.mode_seg.selected_index = 0
        self.mode_seg.tint_color = '#2196F3'
        self.mode_seg.action = self.change_mode
        ctrl.add_subview(self.mode_seg)
        y += 70

        # Parameter Section
        param_label = ui.Label(frame=(20, y, ctrl_width-40, 20))
        param_label.text = 'PARAMETER'
        param_label.font = ('Helvetica-Bold', 12)
        param_label.text_color = '#666666'
        ctrl.add_subview(param_label)
        y += 30

        # Längen
        l1_label = ui.Label(frame=(20, y, 80, 20))
        l1_label.text = 'Länge 1:'
        l1_label.font = ('Helvetica', 12)
        l1_label.text_color = '#666666'
        ctrl.add_subview(l1_label)

        self.l1_field = ui.TextField(frame=(100, y, 60, 24))
        self.l1_field.text = '1.0'
        self.l1_field.font = ('Helvetica', 12)
        self.l1_field.border_width = 1
        self.l1_field.border_color = '#E0E0E0'
        self.l1_field.corner_radius = 4
        ctrl.add_subview(self.l1_field)

        l2_label = ui.Label(frame=(20, y+30, 80, 20))
        l2_label.text = 'Länge 2:'
        l2_label.font = ('Helvetica', 12)
        l2_label.text_color = '#666666'
        ctrl.add_subview(l2_label)

        self.l2_field = ui.TextField(frame=(100, y+30, 60, 24))
        self.l2_field.text = '1.0'
        self.l2_field.font = ('Helvetica', 12)
        self.l2_field.border_width = 1
        self.l2_field.border_color = '#E0E0E0'
        self.l2_field.corner_radius = 4
        ctrl.add_subview(self.l2_field)
        y += 70

        # Massen
        m1_label = ui.Label(frame=(20, y, 80, 20))
        m1_label.text = 'Masse 1:'
        m1_label.font = ('Helvetica', 12)
        m1_label.text_color = '#666666'
        ctrl.add_subview(m1_label)

        self.m1_field = ui.TextField(frame=(100, y, 60, 24))
        self.m1_field.text = '1.0'
        self.m1_field.font = ('Helvetica', 12)
        self.m1_field.border_width = 1
        self.m1_field.border_color = '#E0E0E0'
        self.m1_field.corner_radius = 4
        ctrl.add_subview(self.m1_field)

        m2_label = ui.Label(frame=(20, y+30, 80, 20))
        m2_label.text = 'Masse 2:'
        m2_label.font = ('Helvetica', 12)
        m2_label.text_color = '#666666'
        ctrl.add_subview(m2_label)

        self.m2_field = ui.TextField(frame=(100, y+30, 60, 24))
        self.m2_field.text = '1.0'
        self.m2_field.font = ('Helvetica', 12)
        self.m2_field.border_width = 1
        self.m2_field.border_color = '#E0E0E0'
        self.m2_field.corner_radius = 4
        ctrl.add_subview(self.m2_field)
        y += 70

        # Simulation Settings
        sim_label = ui.Label(frame=(20, y, ctrl_width-40, 20))
        sim_label.text = 'SIMULATION'
        sim_label.font = ('Helvetica-Bold', 12)
        sim_label.text_color = '#666666'
        ctrl.add_subview(sim_label)
        y += 30

        # Geschwindigkeit
        speed_label = ui.Label(frame=(20, y, 80, 20))
        speed_label.text = 'Speed:'
        speed_label.font = ('Helvetica', 12)
        speed_label.text_color = '#666666'
        ctrl.add_subview(speed_label)

        self.speed_slider = ui.Slider(frame=(20, y+24, ctrl_width-60, 20))
        self.speed_slider.minimum_value = 0.1
        self.speed_slider.maximum_value = 3.0
        self.speed_slider.value = 1.0
        self.speed_slider.tint_color = '#2196F3'
        self.speed_slider.action = lambda s: self.update_speed_value(float(s.value))
        ctrl.add_subview(self.speed_slider)

        self.speed_label = ui.Label(frame=(ctrl_width-40, y+24, 30, 20))
        self.speed_label.text = '1.0x'
        self.speed_label.font = ('Helvetica-Bold', 11)
        self.speed_label.text_color = '#333333'
        self.speed_label.alignment = ui.ALIGN_RIGHT
        ctrl.add_subview(self.speed_label)
        y += 60

        # Dämpfung
        damp_label = ui.Label(frame=(20, y, 80, 20))
        damp_label.text = 'Dämpfung:'
        damp_label.font = ('Helvetica', 12)
        damp_label.text_color = '#666666'
        ctrl.add_subview(damp_label)

        self.damping_slider = ui.Slider(frame=(20, y+24, ctrl_width-60, 20))
        self.damping_slider.minimum_value = 0.0
        self.damping_slider.maximum_value = 0.1
        self.damping_slider.value = 0.0
        self.damping_slider.tint_color = '#2196F3'
        self.damping_slider.action = lambda s: self.update_damping(float(s.value))
        ctrl.add_subview(self.damping_slider)

        self.damping_label = ui.Label(frame=(ctrl_width-40, y+24, 30, 20))
        self.damping_label.text = '0.00'
        self.damping_label.font = ('Helvetica-Bold', 11)
        self.damping_label.text_color = '#333333'
        self.damping_label.alignment = ui.ALIGN_RIGHT
        ctrl.add_subview(self.damping_label)
        y += 60

        # Trail Control
        trail_label = ui.Label(frame=(20, y, 60, 24))
        trail_label.text = 'Spur:'
        trail_label.font = ('Helvetica', 12)
        trail_label.text_color = '#666666'
        ctrl.add_subview(trail_label)

        trail_switch = ui.Switch(frame=(80, y, 56, 24))
        trail_switch.value = True
        trail_switch.tint_color = '#2196F3'
        trail_switch.action = lambda s: self.toggle_trail(bool(s.value))
        ctrl.add_subview(trail_switch)

        btn_clear = ui.Button(frame=(150, y, 80, 24))
        btn_clear.title = 'Clear Trail'
        btn_clear.font = ('Helvetica', 11)
        btn_clear.corner_radius = 4
        btn_clear.background_color = '#E0E0E0'
        btn_clear.tint_color = '#333333'
        btn_clear.action = lambda s: self.clear_trail()
        ctrl.add_subview(btn_clear)
        y += 40

        # Zeitsteuerung
        time_label = ui.Label(frame=(20, y, ctrl_width-40, 20))
        time_label.text = 'ZEIT'
        time_label.font = ('Helvetica-Bold', 12)
        time_label.text_color = '#666666'
        ctrl.add_subview(time_label)
        y += 30

        stop_label = ui.Label(frame=(20, y, 80, 20))
        stop_label.text = 'Stop bei:'
        stop_label.font = ('Helvetica', 12)
        stop_label.text_color = '#666666'
        ctrl.add_subview(stop_label)

        self.stop_field = ui.TextField(frame=(100, y, 60, 24))
        self.stop_field.placeholder = 't (s)'
        self.stop_field.font = ('Helvetica', 12)
        self.stop_field.border_width = 1
        self.stop_field.border_color = '#E0E0E0'
        self.stop_field.corner_radius = 4
        ctrl.add_subview(self.stop_field)

        btn_setstop = ui.Button(frame=(170, y, 60, 24))
        btn_setstop.title = 'Set'
        btn_setstop.font = ('Helvetica', 11)
        btn_setstop.corner_radius = 4
        btn_setstop.background_color = '#2196F3'
        btn_setstop.tint_color = 'white'
        btn_setstop.action = self.set_stop_time
        ctrl.add_subview(btn_setstop)
        y += 40

        # Position berechnen
        calc_label = ui.Label(frame=(20, y, 80, 20))
        calc_label.text = 'Pos bei t:'
        calc_label.font = ('Helvetica', 12)
        calc_label.text_color = '#666666'
        ctrl.add_subview(calc_label)

        self.compute_field = ui.TextField(frame=(100, y, 60, 24))
        self.compute_field.placeholder = 't (s)'
        self.compute_field.font = ('Helvetica', 12)
        self.compute_field.border_width = 1
        self.compute_field.border_color = '#E0E0E0'
        self.compute_field.corner_radius = 4
        ctrl.add_subview(self.compute_field)

        btn_compute = ui.Button(frame=(170, y, 60, 24))
        btn_compute.title = 'Mark'
        btn_compute.font = ('Helvetica', 11)
        btn_compute.corner_radius = 4
        btn_compute.background_color = '#FF9800'
        btn_compute.tint_color = 'white'
        btn_compute.action = self.compute_and_stamp
        ctrl.add_subview(btn_compute)
        y += 40

        # Results area
        self.stamps_label = ui.TextView(frame=(20, y, ctrl_width-40, 100))
        self.stamps_label.editable = False
        self.stamps_label.font = ('Courier', 10)
        self.stamps_label.background_color = '#F5F5F5'
        self.stamps_label.corner_radius = 4
        ctrl.add_subview(self.stamps_label)

        self.view.add_subview(ctrl)
        self.ctrl = ctrl

        # connect HUD callbacks to controller methods
        self.draw_view.attach_callbacks(
            on_toggle=self.toggle_run,
            on_reset=lambda s: self.reset(),
            on_change_mode=self.change_mode,
            on_speed=self.update_speed_value,
            on_damping=self.update_damping,
            on_toggle_trail=self.toggle_trail,
            on_clear_trail=self.clear_trail,
        )

        # Initiale Werte synchronisieren
        self.update_speed_value(1.0)
        self.update_damping(0.0)

        # ensure initial layout fits the screen
        self.view.layout = self._layout_root
        self._layout_root()

    # Control callbacks
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
        self.btn_run.background_color = '#FF9800'
        self._start_timer()
        self.draw_view.set_playing(True)

    def pause(self):
        self.model.running = False
        self.btn_run.title = 'Start'
        self.btn_run.background_color = '#4CAF50'
        self._stop_timer()
        self.draw_view.set_playing(False)

    def reset(self):
        self.model.reset()
        self.draw_view.trail = []
        self.draw_view.stamps = []
        self.stamps_label.text = ''
        self.draw_view.set_needs_display()

    def change_mode(self, sender):
        # Synchronisiere Modus
        if hasattr(sender, 'selected_index'):
            idx = sender.selected_index
        else:
            idx = 0 if sender.title == 'Doppelpendel' else 1

        if idx == 1:
            # Einfachpendel -> set m2=0 to reduce to single pendulum
            self.model.params['m2'] = 0.0
        else:
            # Doppelpendel
            self.model.params['m2'] = 1.0

    def update_speed_value(self, val):
        val = max(0.1, float(val))
        self.model.time_scale = val
        # Update Labels
        if hasattr(self, 'speed_label'):
            self.speed_label.text = '{:.1f}x'.format(val)
        if hasattr(self.draw_view, 'speed_val_lbl'):
            self.draw_view.speed_val_lbl.text = '{:.1f}x'.format(val)

    def update_damping(self, val):
        val = max(0.0, float(val))
        self.model.params['damping'] = val
        # Update Labels
        if hasattr(self, 'damping_label'):
            self.damping_label.text = '{:.2f}'.format(val)
        if hasattr(self.draw_view, 'damp_val_lbl'):
            self.draw_view.damp_val_lbl.text = '{:.2f}'.format(val)

    def toggle_trail(self, enabled):
        self.model.trail_enabled = bool(enabled)
        if not enabled:
            self.clear_trail()

    def clear_trail(self):
        self.draw_view.trail = []
        self.draw_view.set_needs_display()

    def set_stop_time(self, sender):
        try:
            v = float(self.stop_field.text)
            if v <= 0:
                self.model.stop_at = None
            else:
                self.model.stop_at = v
        except Exception:
            self.model.stop_at = None

    def compute_and_stamp(self, sender):
        # compute state at given time and stamp on the scene
        try:
            t = float(self.compute_field.text)
        except Exception:
            return
        s = self.model.single_step_silent(t)
        # convert to pixel coordinates
        r = self.draw_view.bounds
        cx = r.w * 0.5
        cy = r.h * 0.15
        origin = (cx, cy)
        l1 = self.model.params['l1'] * self.model.pixels_per_meter
        l2 = self.model.params['l2'] * self.model.pixels_per_meter
        x1, y1 = polar_to_xy(origin, s[0], l1)
        x2, y2 = polar_to_xy((x1,y1), s[2], l2)
        text = 't={:.2f}'.format(t)
        # add stamp
        stamp = {'x': x2, 'y': y2, 'text': text}
        self.draw_view.stamps.append(stamp)
        # update textual stamps
        prev = self.stamps_label.text
        entry = 't={:.2f}s: x={:.3f}, y={:.3f}\n'.format(t, x2/self.model.pixels_per_meter, y2/self.model.pixels_per_meter)
        self.stamps_label.text = entry + prev
        self.draw_view.set_needs_display()

    # Timer management
    def _start_timer(self):
        # run update loop in background thread to not block UI
        if self.timer:
            return
        self._timer_stop = False
        def loop():
            last = time.time()
            while self.model.running and not self._timer_stop:
                now = time.time()
                real_dt = now - last
                last = now
                # scaled dt
                dt = real_dt * self.model.time_scale
                # clamp dt so integrator remains stable
                steps = max(1, int(dt / self.model.dt))
                small_dt = dt / steps
                for i in range(steps):
                    self.model.step(small_dt)
                # update trail with second bob position
                r = self.draw_view.bounds
                cx = r.w * 0.5
                cy = r.h * 0.15
                origin = (cx, cy)
                l1 = self.model.params['l1'] * self.model.pixels_per_meter
                l2 = self.model.params['l2'] * self.model.pixels_per_meter
                x1, y1 = polar_to_xy(origin, self.model.state[0], l1)
                x2, y2 = polar_to_xy((x1,y1), self.model.state[2], l2)
                if self.model.trail_enabled:
                    self.draw_view.trail.append((x2,y2))
                    if len(self.draw_view.trail) > self.model.trail_max:
                        self.draw_view.trail.pop(0)
                    # copy trail to view for drawing
                    self.draw_view.trail = list(self.draw_view.trail)

                # check stop condition
                if self.model.stop_at is not None and self.model.sim_time >= self.model.stop_at:
                    # automatically pause
                    self.pause()
                    break

                # request redraw on main thread
                ui.delay(self.draw_view.set_needs_display, 0)
                # sleep a small amount
                time.sleep(0.016)  # ~60 Hz
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()
        self.timer = t

    def _stop_timer(self):
        self._timer_stop = True
        self.timer = None

    def present(self):
        # present the assembled UI
        self.view.present('fullscreen', hide_title_bar=False)

    # responsive layout for root view
    def _layout_root(self, *args, **kwargs):
        r = self.view.bounds
        total_w = r.w
        total_h = r.h
        ctrl_w = 280
        spacing = 12
        if total_w >= 980:
            # two columns
            self.draw_view.frame = (0, 0, total_w - ctrl_w - spacing, total_h)
            self.ctrl.frame = (total_w - ctrl_w - spacing, 0, ctrl_w, total_h)
        else:
            # stacked, controls below
            ctrl_h = min(360, total_h * 0.42)
            self.draw_view.frame = (0, 0, total_w, total_h - ctrl_h - spacing)
            self.ctrl.frame = (0, total_h - ctrl_h, total_w, ctrl_h)


# Run the app
if __name__ == '__main__':
    app = PendulumApp()
    app.present()