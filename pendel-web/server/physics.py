"""
Numerical physics utilities for single and double pendulum simulation.

This module provides:
- Derivative functions for single and double pendulum
- RK4 and symplectic Euler integrators (with sub-stepping)
- Simple heuristics for adaptive dt_max
- Energy computation and angle normalization helpers
- Position helpers for visualization
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Sequence, Tuple

State = List[float]
Params = Dict[str, float]


def single_pendulum_derivatives(state: Sequence[float], params: Params) -> State:
    """Return derivatives [dtheta, domega] for a simple pendulum.

    Angles are measured from the vertical (downwards is 0 rad). Damping is linear.
    """
    theta, omega = state[:2]
    g = float(params["g"])  # m/s^2
    l = float(params["l1"])  # m
    damping = float(params.get("damping", 0.0))

    dtheta = omega
    domega = -(g / max(1e-9, l)) * math.sin(theta) - damping * omega
    return [dtheta, domega]


def double_pendulum_derivatives(state: Sequence[float], params: Params) -> State:
    """Return derivatives [dth1, dw1, dth2, dw2] for a double pendulum.

    Angles are measured from the vertical (downwards). Damping is linear.
    """
    th1, w1, th2, w2 = state[:4]
    m1 = float(params["m1"])
    m2 = float(params["m2"])
    l1 = float(params["l1"])
    l2 = float(params["l2"])
    g = float(params["g"])
    damping = float(params.get("damping", 0.0))

    delta = th1 - th2
    sin_delta = math.sin(delta)
    cos_delta = math.cos(delta)

    denom = (2.0 * m1 + m2 - m2 * math.cos(2.0 * delta))
    if abs(denom) < 1e-9:
        denom = 1e-9

    # First mass angular acceleration
    num1 = -g * (2.0 * m1 + m2) * math.sin(th1)
    num1 -= m2 * g * math.sin(th1 - 2.0 * th2)
    num1 -= 2.0 * sin_delta * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * cos_delta)
    a1 = num1 / (l1 * denom) - damping * w1

    # Second mass angular acceleration
    num2 = 2.0 * sin_delta * (
        w1 * w1 * l1 * (m1 + m2)
        + g * (m1 + m2) * math.cos(th1)
        + w2 * w2 * l2 * m2 * cos_delta
    )
    a2 = num2 / (l2 * denom) - damping * w2

    return [w1, a1, w2, a2]


def rk4_step(state: Sequence[float], dt: float, params: Params, deriv_func: Callable[[Sequence[float], Params], State]) -> State:
    """Perform one classical RK4 step for arbitrary state dimension."""
    s1 = list(state)
    k1 = deriv_func(s1, params)
    s2 = [s1[i] + 0.5 * dt * k1[i] for i in range(len(s1))]
    k2 = deriv_func(s2, params)
    s3 = [s1[i] + 0.5 * dt * k2[i] for i in range(len(s1))]
    k3 = deriv_func(s3, params)
    s4 = [s1[i] + dt * k3[i] for i in range(len(s1))]
    k4 = deriv_func(s4, params)
    return [s1[i] + dt * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) / 6.0 for i in range(len(s1))]


def symplectic_euler_step(state: Sequence[float], dt: float, params: Params, deriv_func: Callable[[Sequence[float], Params], State]) -> State:
    """Symplectic (semi-implicit) Euler step.

    For pendula, we update angular velocities using accelerations, then angles using new velocities.
    """
    n = len(state)
    if n == 4:
        th1, w1, th2, w2 = state[:4]
        d = deriv_func([th1, w1, th2, w2], params)
        a1 = d[1]
        a2 = d[3]
        w1 = w1 + dt * a1
        w2 = w2 + dt * a2
        th1 = th1 + dt * w1
        th2 = th2 + dt * w2
        return [th1, w1, th2, w2]
    if n == 2:
        th, w = state[:2]
        d = deriv_func([th, w], params)
        a = d[1]
        w = w + dt * a
        th = th + dt * w
        return [th, w]
    # Fallback to explicit Euler
    d = deriv_func(state, params)
    return [state[i] + dt * d[i] for i in range(n)]


def rk4_integrate_substeps(state: Sequence[float], dt_total: float, dt_max: float, params: Params, deriv_func: Callable[[Sequence[float], Params], State]) -> State:
    """Integrate dt_total using RK4 by splitting into sub-steps of size <= dt_max."""
    steps = max(1, int(math.ceil(abs(dt_total) / max(1e-9, dt_max))))
    dt = float(dt_total) / steps
    s = list(state)
    for _ in range(steps):
        s = rk4_step(s, dt, params, deriv_func)
    return s


def choose_dt_max(state: Sequence[float], base_dt: float = 0.005, max_dt: float = 0.02) -> float:
    """Heuristic choice of dt_max based on maximum angular velocity magnitude."""
    if len(state) >= 4:
        w_max = max(abs(state[1]), abs(state[3]))
    else:
        w_max = abs(state[1]) if len(state) > 1 else 0.0
    if w_max <= 0.1:
        return max_dt
    dt = min(max_dt, base_dt / (1.0 + w_max))
    return max(1e-4, dt)


def total_energy(state: Sequence[float], params: Params, mode: str = "double") -> float:
    """Total mechanical energy (kinetic + potential).

    Reference y=0 at the top hinge. Positive y is downwards in our geometry functions.
    """
    g = float(params["g"])  # m/s^2
    if mode == "double" and len(state) >= 4:
        th1, w1, th2, w2 = state[:4]
        m1 = float(params["m1"]) ; m2 = float(params["m2"])  # kg
        l1 = float(params["l1"]) ; l2 = float(params["l2"])  # m
        # velocities
        x1dot = l1 * w1 * math.cos(th1)
        y1dot = -l1 * w1 * math.sin(th1)
        x2dot = x1dot + l2 * w2 * math.cos(th2)
        y2dot = y1dot - l2 * w2 * math.sin(th2)
        KE = 0.5 * m1 * (x1dot * x1dot + y1dot * y1dot) + 0.5 * m2 * (x2dot * x2dot + y2dot * y2dot)
        # potential (downwards positive)
        y1 = -l1 * math.cos(th1)
        y2 = y1 - l2 * math.cos(th2)
        PE = m1 * g * y1 + m2 * g * y2
        return KE + PE
    # single pendulum
    th, w = state[:2]
    m = float(params["m1"]) ; l = float(params["l1"])  # kg, m
    xdot = l * w * math.cos(th)
    ydot = -l * w * math.sin(th)
    KE = 0.5 * m * (xdot * xdot + ydot * ydot)
    y = -l * math.cos(th)
    PE = m * g * y
    return KE + PE


def normalize_angles(state: Sequence[float]) -> State:
    """Normalize angular positions to [-pi, pi], preserving angular velocities."""
    def wrap(angle: float) -> float:
        two_pi = 2.0 * math.pi
        a = (angle + math.pi) % two_pi
        if a < 0:
            a += two_pi
        return a - math.pi

    s = list(state)
    if len(s) >= 2:
        s[0] = wrap(float(s[0]))
    if len(s) >= 4:
        s[2] = wrap(float(s[2]))
    return s


def positions_from_state(state: Sequence[float], params: Params) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Compute bob positions in meters relative to the hinge at (0, 0).

    Returns ((x1, y1), (x2, y2)). For single pendulum, (x2, y2) equals (x1, y1).
    """
    l1 = float(params["l1"]) ; l2 = float(params.get("l2", 0.0))
    if len(state) >= 4:
        th1, _, th2, _ = state[:4]
        x1 = l1 * math.sin(th1)
        y1 = l1 * math.cos(th1)
        x2 = x1 + l2 * math.sin(th2)
        y2 = y1 + l2 * math.cos(th2)
        return (x1, y1), (x2, y2)
    th1, _ = state[:2]
    x1 = l1 * math.sin(th1)
    y1 = l1 * math.cos(th1)
    return (x1, y1), (x1, y1)

