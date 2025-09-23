import { useCallback, useEffect, useRef, useState } from "react";

type Mode = "double" | "single";
type Integrator = "rk4" | "symplectic";

type Vec2 = [number, number];
type Vec4 = [number, number, number, number];

type Params = {
  m1: number;
  m2: number;
  l1: number;
  l2: number;
  g: number;
  damping: number;
};

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function normalizeAngle(angle: number): number {
  const twoPi = Math.PI * 2;
  let a = (angle + Math.PI) % twoPi;
  if (a < 0) a += twoPi;
  return a - Math.PI;
}

function normalizeAngles(state: number[]): number[] {
  const s = state.slice();
  if (s.length >= 2) s[0] = normalizeAngle(s[0]);
  if (s.length >= 4) s[2] = normalizeAngle(s[2]);
  return s;
}

function derivsSingle(state: Vec2, params: Params): Vec2 {
  const [th, w] = state;
  const g = params.g;
  const l = Math.max(1e-9, params.l1);
  const damping = params.damping || 0;
  const dth = w;
  let domega = -(g / l) * Math.sin(th);
  if (damping) domega -= damping * w;
  return [dth, domega];
}

function derivsDouble(state: Vec4, params: Params): Vec4 {
  const [th1, w1, th2, w2] = state;
  const m1 = params.m1, m2 = params.m2;
  const l1 = params.l1, l2 = params.l2;
  const g = params.g;
  const damping = params.damping || 0;

  const delta = th1 - th2;
  const cosDelta = Math.cos(delta);
  const sinDelta = Math.sin(delta);
  const denom = (2 * m1 + m2 - m2 * Math.cos(2 * delta)) || 1e-9;

  let num1 = -g * (2 * m1 + m2) * Math.sin(th1);
  num1 -= m2 * g * Math.sin(th1 - 2 * th2);
  num1 -= 2 * sinDelta * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * cosDelta);
  let domega1 = num1 / (l1 * denom);

  const num2 = 2 * sinDelta * (w1 * w1 * l1 * (m1 + m2) + g * (m1 + m2) * Math.cos(th1) + w2 * w2 * l2 * m2 * cosDelta);
  let domega2 = num2 / (l2 * denom);

  if (damping) {
    domega1 -= damping * w1;
    domega2 -= damping * w2;
  }

  return [w1, domega1, w2, domega2];
}

function rk4Step<T extends number[]>(state: T, dt: number, params: Params, f: (s: T, p: Params) => T): T {
  const k1 = f(state, params);
  const s2 = state.map((v, i) => v + 0.5 * dt * (k1[i] as number)) as T;
  const k2 = f(s2, params);
  const s3 = state.map((v, i) => v + 0.5 * dt * (k2[i] as number)) as T;
  const k3 = f(s3, params);
  const s4 = state.map((v, i) => v + dt * (k3[i] as number)) as T;
  const k4 = f(s4, params);
  const out = state.map((v, i) => v + (dt * ((k1[i] as number) + 2 * (k2[i] as number) + 2 * (k3[i] as number) + (k4[i] as number))) / 6) as T;
  return out;
}

function symplecticEulerStep(state: number[], dt: number, params: Params, f: (s: number[], p: Params) => number[]): number[] {
  const n = state.length;
  if (n === 4) {
    let [th1, w1, th2, w2] = state as Vec4;
    const d = f([th1, w1, th2, w2], params);
    const a1 = d[1];
    const a2 = d[3];
    w1 = w1 + dt * a1;
    w2 = w2 + dt * a2;
    th1 = th1 + dt * w1;
    th2 = th2 + dt * w2;
    return [th1, w1, th2, w2];
  } else if (n === 2) {
    let [th, w] = state as Vec2;
    const d = f([th, w], params);
    const a = d[1];
    w = w + dt * a;
    th = th + dt * w;
    return [th, w];
  }
  const d = f(state, params);
  return state.map((v, i) => v + dt * d[i]);
}

function rk4IntegrateSubsteps<T extends number[]>(state: T, dtTotal: number, dtMax: number, params: Params, f: (s: T, p: Params) => T): T {
  const steps = Math.max(1, Math.ceil(Math.abs(dtTotal) / Math.max(1e-9, dtMax)));
  const dt = dtTotal / steps;
  let s = state.slice() as T;
  for (let i = 0; i < steps; i++) {
    s = rk4Step(s, dt, params, f);
  }
  return s;
}

function chooseDtMax(state: number[], baseDt = 0.005, maxDt = 0.02): number {
  const wMax = state.length === 4 ? Math.max(Math.abs(state[1]), Math.abs(state[3])) : Math.abs(state[1]);
  if (wMax <= 0.1) return maxDt;
  const dt = Math.min(maxDt, baseDt / (1 + wMax));
  return Math.max(1e-4, dt);
}

function totalEnergy(state: number[], params: Params, mode: Mode): number {
  const g = params.g;
  if (mode === "double" && state.length === 4) {
    const [th1, w1, th2, w2] = state as Vec4;
    const m1 = params.m1, m2 = params.m2;
    const l1 = params.l1, l2 = params.l2;
    const x1dot = l1 * w1 * Math.cos(th1);
    const y1dot = -l1 * w1 * Math.sin(th1);
    const x2dot = x1dot + l2 * w2 * Math.cos(th2);
    const y2dot = y1dot - l2 * w2 * Math.sin(th2);
    const KE = 0.5 * m1 * (x1dot * x1dot + y1dot * y1dot) + 0.5 * m2 * (x2dot * x2dot + y2dot * y2dot);
    const y1 = -l1 * Math.cos(th1);
    const y2 = y1 - l2 * Math.cos(th2);
    const PE = m1 * g * y1 + m2 * g * y2;
    return KE + PE;
  } else {
    const [th, w] = state as Vec2;
    const m = params.m1;
    const l = params.l1;
    const xdot = l * w * Math.cos(th);
    const ydot = -l * w * Math.sin(th);
    const KE = 0.5 * m * (xdot * xdot + ydot * ydot);
    const y = -l * Math.cos(th);
    const PE = m * g * y;
    return KE + PE;
  }
}

function polarToXY(origin: { x: number; y: number }, angle: number, length: number): { x: number; y: number } {
  return {
    x: origin.x + length * Math.sin(angle),
    y: origin.y + length * Math.cos(angle),
  };
}

function xyToAngle(origin: { x: number; y: number }, pt: { x: number; y: number }): number {
  const dx = pt.x - origin.x;
  const dy = pt.y - origin.y;
  return Math.atan2(dx, dy);
}

export default function Pendel() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const animRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<Mode>("double");
  const [state, setState] = useState<number[]>([Math.PI * 120 / 180, 0, Math.PI * -10 / 180, 0]);
  const [simTime, setSimTime] = useState(0);
  const [trail, setTrail] = useState<Array<{ x: number; y: number }>>([]);
  const [trailEnabled, setTrailEnabled] = useState(true);
  const [pixelsPerMeter, setPixelsPerMeter] = useState(180);
  const [timeScale, setTimeScale] = useState(1.0);
  const [integrator, setIntegrator] = useState<Integrator>("rk4");
  const [baseDt, setBaseDt] = useState(0.004);
  const [dtMax, setDtMax] = useState(0.015);
  const [energyRef, setEnergyRef] = useState<number | null>(null);
  const energyAccRef = useRef(0);
  const [energyErr, setEnergyErr] = useState(0);
  const [autoswitch, setAutoswitch] = useState(true);
  const energyThreshold = 0.1;
  const [, setStartState] = useState<number[]>([Math.PI * 120 / 180, 0, Math.PI * -10 / 180, 0]);

  const [params, setParams] = useState<Params>({
    m1: 1,
    m2: 1,
    l1: 1,
    l2: 1,
    g: 9.81,
    damping: 0,
  });

  // Draw function
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    // background
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, width, height);

    // grid
    ctx.strokeStyle = "#E5E7EB";
    ctx.lineWidth = 0.5;
    const grid = 50;
    for (let x = 0; x <= width; x += grid) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    }
    for (let y = 0; y <= height; y += grid) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }

    const originX = width / 2;
    const originY = height * 0.2;
    const l1 = params.l1 * pixelsPerMeter;
    const l2 = params.l2 * pixelsPerMeter;

    let x1 = originX, y1 = originY;
    let x2 = originX, y2 = originY;
    if (mode === "double" && state.length === 4) {
      const [th1, , th2] = state as Vec4;
      const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
      const p2 = polarToXY({ x: p1.x, y: p1.y }, th2, l2);
      x1 = p1.x; y1 = p1.y; x2 = p2.x; y2 = p2.y;
    } else {
      const [th1] = state as Vec2;
      const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
      x1 = p1.x; y1 = p1.y; x2 = x1; y2 = y1;
    }

    // trail
    if (trailEnabled && trail.length > 1) {
      for (let i = 1; i < trail.length; i++) {
        const alpha = 0.3 + 0.7 * (i / trail.length);
        ctx.strokeStyle = `rgba(31, 99, 181, ${alpha.toFixed(3)})`;
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(trail[i - 1].x, trail[i - 1].y); ctx.lineTo(trail[i].x, trail[i].y); ctx.stroke();
      }
    }

    // rods
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(originX, originY); ctx.lineTo(x1, y1); ctx.stroke();
    if (mode === "double") {
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    }

    // masses
    ctx.fillStyle = "#2563EB";
    ctx.beginPath(); ctx.ellipse(x1, y1, 10, 10, 0, 0, Math.PI * 2); ctx.fill();
    if (mode === "double") {
      ctx.fillStyle = "#DC2626";
      ctx.beginPath(); ctx.ellipse(x2, y2, 8, 8, 0, 0, Math.PI * 2); ctx.fill();
    }

    // pivot
    ctx.fillStyle = "#1F2937";
    ctx.beginPath(); ctx.ellipse(originX, originY, 5, 5, 0, 0, Math.PI * 2); ctx.fill();

    // time text
    ctx.fillStyle = "#374151";
    ctx.font = "14px Helvetica";
    ctx.fillText(`Zeit: ${simTime.toFixed(2)} s`, 10, height - 20);
  }, [canvasRef, params, pixelsPerMeter, mode, state, trailEnabled, trail, simTime]);

  // Resize canvas and compute pixels per meter based on container
  useEffect(() => {
    function handleResize() {
      const canvas = canvasRef.current; const container = containerRef.current;
      if (!canvas || !container) return;
      const rect = container.getBoundingClientRect();
      const width = Math.max(320, rect.width);
      const height = Math.max(360, rect.height);
      canvas.width = Math.floor(width);
      canvas.height = Math.floor(height);
      const ppm = Math.max(100, Math.min(260, Math.floor(Math.min(width, height) * 0.22)));
      setPixelsPerMeter(ppm);
    }
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Simulation loop
  useEffect(() => {
    if (!running) {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      animRef.current = null;
      lastTsRef.current = null;
      return;
    }
    const step = (ts: number) => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const elapsedMs = ts - lastTsRef.current;
      lastTsRef.current = ts;
      const realDt = elapsedMs / 1000;
      const dtTotal = Math.max(0, realDt * timeScale);
      const f: (s: number[], p: Params) => number[] =
        mode === "double"
          ? ((s: number[], p: Params) => derivsDouble(s as Vec4, p))
          : ((s: number[], p: Params) => derivsSingle(s as Vec2, p));
      const modeStr: Mode = mode;
      let nextState: number[];
      if (integrator === "rk4") {
        const dtmx = Math.min(dtMax, chooseDtMax(state, baseDt, dtMax));
        nextState = rk4IntegrateSubsteps<number[]>(state, dtTotal, dtmx, params, f);
      } else {
        const dtmx = Math.min(dtMax, chooseDtMax(state, Math.max(0.008, baseDt * 2), dtMax));
        const steps = Math.max(1, Math.ceil(Math.abs(dtTotal) / Math.max(1e-9, dtmx)));
        const small = dtTotal / steps;
        let s = state.slice();
        for (let i = 0; i < steps; i++) s = symplecticEulerStep(s, small, params, f);
        nextState = s;
      }
      nextState = normalizeAngles(nextState);
      setState(nextState);
      setSimTime((t: number) => t + dtTotal);

      // Energy check (without damping)
      if ((params.damping || 0) === 0) {
        energyAccRef.current += dtTotal;
        let eRef = energyRef;
        if (eRef == null) {
          eRef = totalEnergy(nextState, params, modeStr);
          setEnergyRef(eRef);
        }
        if (energyAccRef.current >= 0.5) {
          energyAccRef.current = 0;
          const e = totalEnergy(nextState, params, modeStr);
          const denom = Math.max(1e-9, Math.abs(eRef ?? e));
          const err = Math.abs(e - (eRef ?? e)) / denom;
          setEnergyErr(err);
          if (autoswitch && integrator === "symplectic" && err > energyThreshold) {
            setIntegrator("rk4");
            setBaseDt(0.004);
            setDtMax(0.015);
            setEnergyRef(e);
          } else {
            if (err > energyThreshold * 0.5) setDtMax((v: number) => Math.max(0.001, v * 0.85));
            else setDtMax((v: number) => Math.min(integrator === "rk4" ? 0.015 : 0.03, v * 1.05));
          }
        }
      }

      // trail
      if (trailEnabled) {
        const canvas = canvasRef.current;
        if (canvas) {
          const width = canvas.width; const height = canvas.height;
          const originX = width / 2; const originY = height * 0.2;
          const l1 = params.l1 * pixelsPerMeter; const l2 = params.l2 * pixelsPerMeter;
          let px: number, py: number;
          if (mode === "double" && nextState.length === 4) {
            const [th1, , th2] = nextState as Vec4;
            const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
            const p2 = polarToXY({ x: p1.x, y: p1.y }, th2, l2);
            px = p2.x; py = p2.y;
          } else {
            const [th1] = nextState as Vec2;
            const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
            px = p1.x; py = p1.y;
          }
          setTrail((arr: Array<{ x: number; y: number }>) => {
            const n = arr.length;
            const copy = n > 300 ? arr.slice(n - 299) : arr.slice();
            copy.push({ x: px, y: py });
            return copy;
          });
        }
      }

      draw();
      animRef.current = requestAnimationFrame(step);
    };
    animRef.current = requestAnimationFrame(step);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      animRef.current = null;
    };
  }, [running, state, mode, params, timeScale, integrator, baseDt, dtMax, trailEnabled, pixelsPerMeter, energyRef, autoswitch, draw]);

  // (moved draw above)

  // Drag interaction
  const dragRef = useRef<null | "bob1" | "bob2">(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onPointerDown = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      const tx = e.clientX - rect.left; const ty = e.clientY - rect.top;
      const originX = canvas.width / 2; const originY = canvas.height * 0.2;
      const l1 = params.l1 * pixelsPerMeter;
      let x1: number, y1: number, x2: number, y2: number;
      if (mode === "double" && state.length === 4) {
        const [th1, , th2] = state as Vec4;
        const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
        const p2 = polarToXY({ x: p1.x, y: p1.y }, th2, l2);
        x1 = p1.x; y1 = p1.y; x2 = p2.x; y2 = p2.y;
      } else {
        const [th1] = state as Vec2;
        const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
        x1 = p1.x; y1 = p1.y; x2 = x1; y2 = y1;
      }
      if (mode === "double" && (tx - x2) ** 2 + (ty - y2) ** 2 < 20 * 20) dragRef.current = "bob2";
      else if ((tx - x1) ** 2 + (ty - y1) ** 2 < 20 * 20) dragRef.current = "bob1";
      else dragRef.current = null;
      if (dragRef.current && running) setRunning(false);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!dragRef.current) return;
      const rect = canvas.getBoundingClientRect();
      const tx = e.clientX - rect.left; const ty = e.clientY - rect.top;
      const originX = canvas.width / 2; const originY = canvas.height * 0.2;
      const l1 = params.l1 * pixelsPerMeter; const l2 = params.l2 * pixelsPerMeter;
      if (dragRef.current === "bob1") {
        const th1 = xyToAngle({ x: originX, y: originY }, { x: tx, y: ty });
        if (mode === "double") setState((prev: number[]) => {
          const prev4 = prev as Vec4; return normalizeAngles([th1, 0, prev4[2], prev4[3]]);
        });
        else setState(() => normalizeAngles([th1, 0]));
        setStartState(() => {
          if (mode === "double") return [th1, 0, (state as Vec4)[2], (state as Vec4)[3]];
          return [th1, 0];
        });
      } else if (dragRef.current === "bob2" && mode === "double") {
        const th1 = (state as Vec4)[0];
        const p1 = polarToXY({ x: originX, y: originY }, th1, l1);
        const th2 = xyToAngle({ x: p1.x, y: p1.y }, { x: tx, y: ty });
        setState((prev: number[]) => {
          const prev4 = prev as Vec4; return normalizeAngles([prev4[0], prev4[1], th2, 0]);
        });
        setStartState([th1, (state as Vec4)[1], th2, 0]);
      }
      draw();
    };

    const onPointerUp = () => {
      dragRef.current = null;
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    return () => {
      canvas.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [canvasRef, params, pixelsPerMeter, mode, state, running, draw]);

  function toggleRun() {
    setRunning((r: boolean) => !r);
  }

  function doReset() {
    setRunning(false);
    if (mode === "double") {
      const s: Vec4 = [Math.PI * 120 / 180, 0, Math.PI * -10 / 180, 0];
      setState(s);
      setStartState(s);
    } else {
      const s: Vec2 = [Math.PI * 60 / 180, 0];
      setState(s);
      setStartState(s);
    }
    setSimTime(0);
    setTrail([]);
    setEnergyRef(null);
    setEnergyErr(0);
  }

  function applyMode(next: Mode) {
    if (next === mode) return;
    if (next === "single") {
      const [th1, w1] = state as Vec2;
      setState([th1, w1]);
    } else {
      const [th1, w1] = (state.length === 2 ? state : [state[0], state[1]]) as Vec2;
      setState([th1, w1, Math.PI * -10 / 180, 0]);
    }
    setMode(next);
    setTrail([]);
  }

  function applyParam(field: keyof Params, value: number) {
    setParams((p: Params) => ({ ...p, [field]: value }));
  }

  function clearTrail() {
    setTrail([]);
  }

  // Initial draw once mounted
  useEffect(() => { draw(); }, [draw]);

  return (
    <div className="min-h-screen p-4" style={{ background: "#F3F4F6" }}>
      <div className="mx-auto" style={{ maxWidth: 1200 }}>
        <h1 className="text-2xl font-bold mb-4">Pendel Simulator</h1>
        <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 300px" }}>
          <div ref={containerRef} className="bg-white rounded border" style={{ minHeight: 420 }}>
            <canvas ref={canvasRef} className="w-full h-full" style={{ touchAction: "none", width: "100%", height: "100%", display: "block" }} />
          </div>
          <div className="bg-white rounded border p-3">
            <div className="text-center font-semibold mb-2">Steuerung</div>
            <div className="flex gap-2 mb-3">
              <button className="px-3 py-2 rounded text-white" style={{ background: running ? "#EF4444" : "#10B981" }} onClick={toggleRun}>{running ? "Stop" : "Start"}</button>
              <button className="px-3 py-2 rounded text-white" style={{ background: "#6B7280" }} onClick={doReset}>Reset</button>
            </div>

            <div className="h-px bg-gray-200 my-2" />

            <label className="block text-sm mb-1">Modus</label>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <button className={`px-2 py-2 rounded border ${mode === "double" ? "bg-blue-600 text-white" : "bg-gray-50"}`} onClick={() => applyMode("double")}>Doppelpendel</button>
              <button className={`px-2 py-2 rounded border ${mode === "single" ? "bg-blue-600 text-white" : "bg-gray-50"}`} onClick={() => applyMode("single")}>Einzelpendel</button>
            </div>

            <div className="h-px bg-gray-200 my-2" />

            <div className="grid grid-cols-2 gap-2 mb-2 items-center">
              <label className="text-sm">Länge 1 (m)</label>
              <input className="border rounded p-1 text-right" value={params.l1} onChange={(e) => applyParam("l1", clamp(parseFloat(e.target.value), 1e-6, 10))} />
              <label className="text-sm">Länge 2 (m)</label>
              <input disabled={mode !== "double"} className="border rounded p-1 text-right" value={params.l2} onChange={(e) => applyParam("l2", clamp(parseFloat(e.target.value), 1e-6, 10))} />
              <label className="text-sm">Masse 1 (kg)</label>
              <input className="border rounded p-1 text-right" value={params.m1} onChange={(e) => applyParam("m1", clamp(parseFloat(e.target.value), 1e-6, 100))} />
              <label className="text-sm">Masse 2 (kg)</label>
              <input disabled={mode !== "double"} className="border rounded p-1 text-right" value={params.m2} onChange={(e) => applyParam("m2", clamp(parseFloat(e.target.value), 0, 100))} />
            </div>

            <div className="h-px bg-gray-200 my-2" />

            <div className="mb-3">
              <label className="block text-sm">Gravitation (m/s²): {params.g.toFixed(2)}</label>
              <input type="range" min={0} max={20} step={0.01} value={params.g} onChange={(e) => applyParam("g", parseFloat(e.target.value))} className="w-full" />
            </div>

            <div className="mb-3">
              <label className="block text-sm">Dämpfung: {params.damping.toFixed(2)}</label>
              <input type="range" min={0} max={0.5} step={0.01} value={params.damping} onChange={(e) => applyParam("damping", parseFloat(e.target.value))} className="w-full" />
            </div>

            <div className="mb-3">
              <label className="block text-sm">Geschwindigkeit: {timeScale.toFixed(1)}x</label>
              <input type="range" min={0.1} max={3} step={0.1} value={timeScale} onChange={(e) => setTimeScale(parseFloat(e.target.value))} className="w-full" />
            </div>

            <div className="h-px bg-gray-200 my-2" />

            <label className="block text-sm mb-1">Integrator</label>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <button className={`px-2 py-2 rounded border ${integrator === "rk4" ? "bg-blue-600 text-white" : "bg-gray-50"}`} onClick={() => { setIntegrator("rk4"); setBaseDt(0.004); setDtMax(0.015); setEnergyRef(null); }}>Accurate (RK4)</button>
              <button className={`px-2 py-2 rounded border ${integrator === "symplectic" ? "bg-blue-600 text-white" : "bg-gray-50"}`} onClick={() => { setIntegrator("symplectic"); setBaseDt(0.008); setDtMax(0.03); setEnergyRef(null); }}>Fast (Symplectic)</button>
            </div>

            <div className="grid grid-cols-2 gap-2 items-center mb-2">
              <label className="text-sm">dt_max (s)</label>
              <input type="number" className="border rounded p-1 text-right" value={dtMax} step={0.001} onChange={(e) => setDtMax(clamp(parseFloat(e.target.value), 0.0005, 0.05))} />
              <label className="text-sm">base_dt (s)</label>
              <input type="number" className="border rounded p-1 text-right" value={baseDt} step={0.001} onChange={(e) => setBaseDt(clamp(parseFloat(e.target.value), 0.0005, 0.05))} />
            </div>

            <div className="grid grid-cols-2 gap-2 items-center mb-2">
              <label className="text-sm">AutoSwitch</label>
              <input type="checkbox" checked={autoswitch} onChange={(e) => setAutoswitch(e.target.checked)} />
            </div>

            <div className="text-xs text-gray-600 mb-2">ΔE/E: {energyRef == null ? "—" : `${(energyErr * 100).toFixed(3)}%`}</div>

            <div className="h-px bg-gray-200 my-2" />

            <div className="grid grid-cols-2 gap-2 items-center mb-2">
              <label className="text-sm">Spur anzeigen</label>
              <input type="checkbox" checked={trailEnabled} onChange={(e) => setTrailEnabled(e.target.checked)} />
              <div />
              <button className="px-2 py-1 rounded border" onClick={clearTrail}>Spur löschen</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

