from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from server.physics import (
    choose_dt_max,
    double_pendulum_derivatives,
    normalize_angles,
    positions_from_state,
    rk4_integrate_substeps,
    single_pendulum_derivatives,
    symplectic_euler_step,
    total_energy,
)


@dataclass
class SimulationSession:
    """Holds the per-session simulation state and parameters."""

    mode: str = "double"  # "double" or "single"
    state: List[float] = field(default_factory=lambda: [math.radians(45.0), 0.0, math.radians(-30.0), 0.0])
    params: Dict[str, float] = field(
        default_factory=lambda: {
            "m1": 1.0,
            "m2": 1.0,
            "l1": 1.0,
            "l2": 1.0,
            "g": 9.81,
            "damping": 0.0,
        }
    )

    integrator: str = "rk4"  # "rk4" | "symplectic"
    base_dt: float = 0.004
    dt_max: float = 0.015
    time_scale: float = 1.0
    sim_time: float = 0.0

    energy_ref: float | None = None
    energy_err: float = 0.0
    energy_check_interval: float = 0.5
    _energy_accum: float = 0.0
    autoswitch: bool = True
    energy_threshold: float = 0.1

    normalize_every_n: int = 1
    _norm_counter: int = 0

    trail_enabled: bool = True
    trail_max_points: int = 300
    trail_points: List[Tuple[float, float]] = field(default_factory=list)

    def step(self, dt: float) -> None:
        """Advance the simulation by dt seconds, with sub-stepping and monitoring."""
        # pick derivatives
        if self.mode == "double":
            deriv = double_pendulum_derivatives
            energy_mode = "double"
        else:
            deriv = single_pendulum_derivatives
            energy_mode = "single"

        if self.integrator == "rk4":
            dtmx = min(self.dt_max, choose_dt_max(self.state, base_dt=self.base_dt, max_dt=self.dt_max))
            self.state = rk4_integrate_substeps(self.state, dt, dtmx, self.params, deriv)
        else:
            # symplectic step(s)
            dtmx = min(self.dt_max, choose_dt_max(self.state, base_dt=max(0.008, self.base_dt * 2.0), max_dt=self.dt_max))
            steps = max(1, int(math.ceil(abs(dt) / max(1e-9, dtmx))))
            small = float(dt) / steps
            s = list(self.state)
            for _ in range(steps):
                s = symplectic_euler_step(s, small, self.params, deriv)
            self.state = s

        # occasional normalization
        self._norm_counter += 1
        if self._norm_counter >= self.normalize_every_n:
            self.state = normalize_angles(self.state)
            self._norm_counter = 0

        self.sim_time += dt

        # energy monitoring when no damping
        if float(self.params.get("damping", 0.0)) == 0.0:
            if self.energy_ref is None:
                try:
                    self.energy_ref = total_energy(self.state, self.params, mode=energy_mode)
                except Exception:
                    self.energy_ref = 0.0
            self._energy_accum += dt
            if self._energy_accum >= self.energy_check_interval:
                self._energy_accum = 0.0
                try:
                    e = total_energy(self.state, self.params, mode=energy_mode)
                    e0 = self.energy_ref if self.energy_ref is not None else e
                    denom = max(1e-9, abs(e0))
                    self.energy_err = abs(e - e0) / denom
                except Exception:
                    self.energy_err = 0.0

                if self.autoswitch and self.integrator == "symplectic" and self.energy_err > self.energy_threshold:
                    # switch to rk4 if drift too large
                    self.integrator = "rk4"
                    self.base_dt = 0.004
                    self.dt_max = 0.015
                    self.energy_ref = e
                else:
                    # adapt dt_max slightly
                    if self.energy_err > self.energy_threshold * 0.5:
                        self.dt_max = max(0.001, self.dt_max * 0.85)
                    else:
                        upper = 0.015 if self.integrator == "rk4" else 0.03
                        self.dt_max = min(upper, self.dt_max * 1.05)

        # trail update
        if self.trail_enabled:
            (x1, y1), (x2, y2) = positions_from_state(self.state, self.params)
            if self.mode == "double":
                self._append_trail_point(x2, y2)
            else:
                self._append_trail_point(x1, y1)

    def get_positions(self) -> Dict[str, float]:
        (x1, y1), (x2, y2) = positions_from_state(self.state, self.params)
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    def reset(self) -> None:
        self.state = [math.radians(45.0), 0.0, math.radians(-30.0), 0.0] if self.mode == "double" else [math.radians(45.0), 0.0]
        self.sim_time = 0.0
        self.energy_ref = None
        self.energy_err = 0.0
        self._energy_accum = 0.0
        self.trail_points.clear()

    def set_mode(self, mode: str) -> None:
        mode = (mode or "").lower()
        new_mode = "single" if mode.startswith("single") or mode.startswith("einfach") else "double"
        if new_mode == self.mode:
            return
        if new_mode == "single":
            th1, w1 = self.state[:2]
            self.state = [th1, w1]
        else:
            th1, w1 = self.state[:2]
            self.state = [th1, w1, math.radians(-30.0), 0.0]
        self.mode = new_mode
        self.reset()

    def _append_trail_point(self, x: float, y: float) -> None:
        self.trail_points.append((float(x), float(y)))
        if len(self.trail_points) > self.trail_max_points:
            self.trail_points.pop(0)

