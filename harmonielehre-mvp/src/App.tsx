import React, { useMemo, useState } from "react";
import VexRenderer from "./renderer/VexRenderer";
import { parseProgression } from "./theory/parser";
import type { Mode } from "./theory/types";
import { evaluateUserVoicing } from "./theory/evaluator";
import { satbNoteStringsToMidi } from "./theory/pitch";
import { functionToChord } from "./theory/key";
import { generateLegalVoicingsForChord } from "./theory/voicing";

// Mode type is imported from theory/types

export default function App() {
  const [keySignature, setKeySignature] = useState<string>("C");
  const [mode, setMode] = useState<Mode>("major");
  const [progressionInput, setProgressionInput] = useState<string>("T DD7/3 D7 TP S6/4 T");
  const tokens = useMemo(() => parseProgression(progressionInput), [progressionInput]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [userVoicings, setUserVoicings] = useState<Array<{ S: string; A: string; T: string; B: string }>>([
    { S: "c/5", A: "e/4", T: "g/3", B: "c/3" },
  ]);
  const [issues, setIssues] = useState<string[]>([]);

  // Reset user voicings when tokens change
  React.useEffect(() => {
    if (tokens.length === 0) {
      setUserVoicings([{ S: "c/5", A: "e/4", T: "g/3", B: "c/3" }]);
      setCurrentIdx(0);
      return;
    }
    const prev = userVoicings;
    const next: Array<{ S: string; A: string; T: string; B: string }> = [...prev];
    while (next.length < tokens.length) next.push({ S: "c/5", A: "e/4", T: "g/3", B: "c/3" });
    if (next.length > tokens.length) next.length = tokens.length;
    setUserVoicings(next);
    if (currentIdx >= tokens.length) setCurrentIdx(0);
  }, [progressionInput]);

  function handleCheck() {
    if (tokens.length === 0) return;
    const ctx = { key: keySignature, mode } as const;
    const token = tokens[currentIdx];
    const prev = currentIdx > 0 ? satbNoteStringsToMidi(userVoicings[currentIdx - 1]) : null;
    const res = evaluateUserVoicing(ctx, token, prev, satbNoteStringsToMidi(userVoicings[currentIdx]));
    setIssues(res.issues.map((i) => i.message));
  }

  function handleAutoFill() {
    if (tokens.length === 0) return;
    const ctx = { key: keySignature, mode } as const;
    const token = tokens[currentIdx];
    const chord = functionToChord(ctx, token.func);
    const allowed = generateLegalVoicingsForChord(token, chord);
    if (allowed.length === 0) return;
    const choice = allowed[0];
    const toNote = (m: number) => midiToNote(choiceFn(m));
    function midiToNote(midi: number): string {
      const pcNames = ["c","c#","d","eb","e","f","f#","g","ab","a","bb","b"];
      const pc = ((midi % 12) + 12) % 12;
      const oct = Math.floor(midi / 12) - 1;
      return `${pcNames[pc]}/${oct}`;
    }
    function choiceFn(x: number) { return x; }
    const filled = { S: midiToNote(choice.S), A: midiToNote(choice.A), T: midiToNote(choice.T), B: midiToNote(choice.B) };
    const arr = userVoicings;
    const next: Array<{ S: string; A: string; T: string; B: string }> = [...arr];
    next[currentIdx] = filled;
    setUserVoicings(next);
  }

  return (
    <div style={{ padding: 16, maxWidth: 980, margin: "0 auto" }}>
      <h1>Harmonielehre MVP</h1>
      <Controls
        keySignature={keySignature}
        setKeySignature={setKeySignature}
        mode={mode}
        setMode={setMode}
        progressionInput={progressionInput}
        setProgressionInput={setProgressionInput}
      />
      <div style={{ marginTop: 16 }}>
        <p>
          Aktuelle Tonart: <strong>{keySignature} {mode === "major" ? "Dur" : "Moll"}</strong>
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tokens.map((t, idx) => (
            <span key={idx} style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #ccc", background: idx === currentIdx ? "#def" : "#f7f7f7" }}>
              {t.func}{t.inversion ? ` ${t.inversion}` : ""}{t.suspension ? ` (${t.suspension})` : ""}
            </span>
          ))}
        </div>
      </div>
      <hr />
      <p>Notation (Platzhalter-Noten) und Parser-Vorschau unten.</p>
      <VexRenderer notes={userVoicings[currentIdx] || { S: "c/5", A: "e/4", T: "g/3", B: "c/3" }} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 12 }}>
        {(["S", "A", "T", "B"] as const).map((p) => (
          <label key={p} style={{ display: "flex", flexDirection: "column" }}>
            {p}
            <input value={(userVoicings[currentIdx] as any)?.[p] ?? ""} onChange={(e: any) => { const next: Array<{ S: string; A: string; T: string; B: string }> = [...userVoicings]; next[currentIdx] = { ...(next[currentIdx] as any || {S:"",A:"",T:"",B:""}), [p]: e.target.value } as any; setUserVoicings(next); }} />
          </label>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}>Zurück</button>
        <button onClick={() => setCurrentIdx(Math.min(tokens.length - 1, currentIdx + 1))}>Weiter</button>
        <button onClick={handleAutoFill}>Auto-Fill</button>
        <button onClick={handleCheck}>Prüfen</button>
      </div>
      {issues.length > 0 && (
        <ul>
          {issues.map((m, idx) => (
            <li key={idx}>{m}</li>
          ))}
        </ul>
      )}
      <details style={{ marginTop: 16 }}>
        <summary>Parser-Output</summary>
        <pre>{JSON.stringify(tokens, null, 2)}</pre>
      </details>
    </div>
  );
}

function Controls(props: {
  keySignature: string;
  setKeySignature: (v: string) => void;
  mode: Mode;
  setMode: (v: Mode) => void;
  progressionInput: string;
  setProgressionInput: (v: string) => void;
}) {
  const keys = useMemo(
    () => ["C", "G", "D", "A", "E", "B", "F#", "C#", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"],
    []
  );
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <label>
        Tonart:
        <select value={props.keySignature} onChange={(e: any) => props.setKeySignature(e.target.value)}>
          {keys.map((k: string) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
      </label>
      <label>
        Modus:
        <select value={props.mode} onChange={(e: any) => props.setMode(e.target.value as Mode)}>
          <option value="major">Dur</option>
          <option value="minor">Moll</option>
        </select>
      </label>
      <label style={{ flex: 1, minWidth: 320 }}>
        Progression:
        <input
          style={{ width: "100%" }}
          value={props.progressionInput}
          onChange={(e: any) => props.setProgressionInput(e.target.value)}
          placeholder="z.B. T DD7/3 D7 TP S6/4 T"
        />
      </label>
      <button onClick={() => alert("Parser, Renderer, Checker folgen im nächsten Schritt")}>Weiter</button>
    </div>
  );
}

