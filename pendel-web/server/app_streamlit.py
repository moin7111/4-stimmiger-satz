from __future__ import annotations

import time
from typing import Tuple

import plotly.graph_objects as go
import streamlit as st

from server.sim_session import SimulationSession


def _ensure_session() -> SimulationSession:
    if "sim" not in st.session_state:
        st.session_state.sim = SimulationSession()
    if "running" not in st.session_state:
        st.session_state.running = False
    if "last_time" not in st.session_state:
        st.session_state.last_time = time.time()
    return st.session_state.sim


def _update_params_from_sidebar(sim: SimulationSession) -> None:
    # Mode
    mode_label = st.sidebar.selectbox("Modus", ["Doppelpendel", "Einzelpendel"], index=0 if sim.mode == "double" else 1)
    sim.set_mode("double" if mode_label == "Doppelpendel" else "single")

    # Lengths and masses
    l1 = st.sidebar.number_input("Länge 1 (m)", min_value=0.01, max_value=10.0, value=float(sim.params["l1"]), step=0.05)
    m1 = st.sidebar.number_input("Masse 1 (kg)", min_value=0.01, max_value=50.0, value=float(sim.params["m1"]), step=0.1)
    if sim.mode == "double":
        l2 = st.sidebar.number_input("Länge 2 (m)", min_value=0.01, max_value=10.0, value=float(sim.params["l2"]), step=0.05)
        m2 = st.sidebar.number_input("Masse 2 (kg)", min_value=0.01, max_value=50.0, value=float(sim.params["m2"]), step=0.1)
        sim.params.update({"l1": float(l1), "l2": float(l2), "m1": float(m1), "m2": float(m2)})
    else:
        sim.params.update({"l1": float(l1), "m1": float(m1)})

    # Physics & integrator
    g = st.sidebar.slider("Gravitation g (m/s²)", min_value=0.0, max_value=30.0, value=float(sim.params["g"]), step=0.1)
    damping = st.sidebar.slider("Dämpfung (1/s)", min_value=0.0, max_value=0.5, value=float(sim.params.get("damping", 0.0)), step=0.01)
    sim.params.update({"g": float(g), "damping": float(damping)})

    integrator_label = st.sidebar.radio("Integrator", ["Accurate (RK4)", "Fast (Symplectic)"] , index=0 if sim.integrator == "rk4" else 1)
    sim.integrator = "rk4" if integrator_label.startswith("Accurate") else "symplectic"

    base_dt = st.sidebar.slider("base_dt (s)", min_value=0.0005, max_value=0.02, value=float(sim.base_dt), step=0.0005)
    dt_max = st.sidebar.slider("dt_max (s)", min_value=0.001, max_value=0.05, value=float(sim.dt_max), step=0.001)
    sim.base_dt = float(base_dt)
    sim.dt_max = float(dt_max)

    time_scale = st.sidebar.slider("Geschwindigkeit", min_value=0.1, max_value=5.0, value=float(sim.time_scale), step=0.1)
    sim.time_scale = float(time_scale)

    autoswitch = st.sidebar.checkbox("AutoSwitch bei Energie-Drift", value=bool(sim.autoswitch))
    sim.autoswitch = bool(autoswitch)

    trail_enabled = st.sidebar.checkbox("Spur anzeigen", value=bool(sim.trail_enabled))
    sim.trail_enabled = bool(trail_enabled)
    if st.sidebar.button("Spur löschen"):
        sim.trail_points.clear()


def _origin_and_limits(sim: SimulationSession) -> Tuple[Tuple[float, float], float]:
    # world origin is hinge at (0, 0). For plotting, compute extent.
    l1 = float(sim.params["l1"]) ; l2 = float(sim.params.get("l2", 0.0))
    total_len = l1 + (l2 if sim.mode == "double" else 0.0)
    max_len = max(1.0, total_len)
    return (0.0, 0.0), max_len


def _build_figure(sim: SimulationSession) -> go.Figure:
    from server.physics import positions_from_state

    (x1_m, y1_m), (x2_m, y2_m) = positions_from_state(sim.state, sim.params)
    # Invert y for plotting (upwards positive)
    x1, y1 = x1_m, -y1_m
    x2, y2 = x2_m, -y2_m

    origin, max_len = _origin_and_limits(sim)
    ox, oy = origin
    pad = max_len * 0.2

    # Trail
    trail_x = []
    trail_y = []
    if sim.trail_enabled and sim.trail_points:
        for px, py in sim.trail_points:
            trail_x.append(px)
            trail_y.append(-py)

    fig = go.Figure()

    # rods
    fig.add_trace(go.Scatter(x=[ox, x1], y=[oy, y1], mode="lines", line=dict(color="#374151", width=4), hoverinfo="skip", showlegend=False))
    if sim.mode == "double":
        fig.add_trace(go.Scatter(x=[x1, x2], y=[y1, y2], mode="lines", line=dict(color="#374151", width=4), hoverinfo="skip", showlegend=False))

    # bobs
    fig.add_trace(go.Scatter(x=[x1], y=[y1], mode="markers", marker=dict(size=16, color="#2563EB"), hoverinfo="skip", showlegend=False))
    if sim.mode == "double":
        fig.add_trace(go.Scatter(x=[x2], y=[y2], mode="markers", marker=dict(size=14, color="#DC2626"), hoverinfo="skip", showlegend=False))

    # hinge
    fig.add_trace(go.Scatter(x=[ox], y=[oy], mode="markers", marker=dict(size=10, color="#1F2937"), hoverinfo="skip", showlegend=False))

    # trail as faded line (single color)
    if trail_x and trail_y and len(trail_x) > 1:
        fig.add_trace(go.Scatter(x=trail_x, y=trail_y, mode="lines", line=dict(color="rgba(31,119,180,0.6)", width=2), hoverinfo="skip", showlegend=False))

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(scaleanchor="y", scaleratio=1.0, range=[-max_len - pad, max_len + pad], showgrid=True, zeroline=False),
        yaxis=dict(range=[-max_len - pad, max_len + pad], showgrid=True, zeroline=False),
        dragmode=False,
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Pendel-Simulator", layout="wide")
    sim = _ensure_session()

    st.title("Pendel-Simulator")
    st.caption("Realtime Visualisierung – RK4 oder symplektischer Euler, Spur, Energie-Drift")

    # Controls
    _update_params_from_sidebar(sim)

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        if not st.session_state.get("running", False):
            if st.button("Start", type="primary"):
                st.session_state.running = True
                st.session_state.last_time = time.time()
        else:
            if st.button("Stop", type="secondary"):
                st.session_state.running = False
    with col_b:
        if st.button("Reset"):
            sim.reset()
            st.session_state.last_time = time.time()
    with col_c:
        st.metric("ΔE/E", f"{sim.energy_err * 100.0:.3f}%")

    # autorefresh when running
    if st.session_state.get("running", False):
        st_autorefresh = st.autorefresh(interval=33, key="pendel_autorefresh")

    # step simulation once per rerun when running
    now = time.time()
    dt = max(0.0, (now - float(st.session_state.get("last_time", now))))
    st.session_state.last_time = now
    if st.session_state.get("running", False):
        # cap dt to avoid large jumps
        dt = min(dt, 0.05) * float(sim.time_scale)
        try:
            sim.step(dt)
        except Exception:
            # on any runtime error, pause to avoid tight loop
            st.session_state.running = False

    # draw plot
    fig = _build_figure(sim)
    st.plotly_chart(fig, use_container_width=True, config={"staticPlot": False, "displayModeBar": False})

    # Show state quick view
    with st.expander("Details (State)", expanded=False):
        st.write({
            "mode": sim.mode,
            "state": sim.state,
            "params": sim.params,
            "integrator": sim.integrator,
            "dt_max": sim.dt_max,
            "base_dt": sim.base_dt,
            "sim_time": sim.sim_time,
            "energy_err": sim.energy_err,
            "trail_len": len(sim.trail_points),
        })


if __name__ == "__main__":
    main()

