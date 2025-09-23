import { useEffect, useState } from "react";
import { useRouter } from "next/router";

type Project = {
  id: number;
  name: string;
  leader: string;
  description?: string | null;
  capacity: number;
  allowedClasses: { classGroupId: number; classGroup: { id: number; name: string } }[];
  studentsAssigned?: { id: string }[];
};

type Settings = { selectionModel: "DIRECT" | "RANKED"; selectionStartAt?: string | null; selectionStartEnabled?: boolean };

export default function Select() {
  const router = useRouter();
  const studentId = (router.query.studentId as string) || "";
  const [studentClassId, setStudentClassId] = useState<number | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [choice1, setChoice1] = useState<number | "">("");
  const [choice2, setChoice2] = useState<number | "">("");
  const [choice3, setChoice3] = useState<number | "">("");
  const [directChoice, setDirectChoice] = useState<number | "">("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/settings").then(async (r) => setSettings(await r.json()));
    fetch("/api/projects").then(async (r) => setProjects(await r.json()));
    if (studentId) {
      fetch(`/api/students?id=${studentId}`).then(async (r) => {
        const s = await r.json();
        if (r.ok) setStudentClassId(s.classGroupId);
      });
    }
  }, [studentId]);

  const visibleProjects = projects.filter((p) =>
    p.allowedClasses.length === 0 || (studentClassId !== null && p.allowedClasses.some((ac) => ac.classGroupId === studentClassId)),
  );

  const projectById = new Map(visibleProjects.map((p) => [p.id, p] as const));

  const truncate = (text: string, max: number) => (text.length > max ? text.slice(0, max - 1) + "…" : text);
  const optionLabel = (p: Project) => `${p.name} – ${p.leader}${p.description ? ` — ${truncate(p.description, 70)}` : ""}`;

  const rankedSubmit = async () => {
    setError(null);
    const choices = [choice1, choice2, choice3]
      .filter((v) => v !== "")
      .map((v, idx) => ({ projectId: Number(v), rank: idx + 1 }));
    if (choices.length === 0) {
      setError("Bitte mindestens eine Wahl angeben.");
      return;
    }
    const res = await fetch("/api/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ studentId, choices }),
    });
    if (!res.ok) {
      setError("Speichern fehlgeschlagen.");
      return;
    }
    router.push("/thanks");
  };

  const directSubmit = async () => {
    setError(null);
    if (directChoice === "") {
      setError("Bitte ein Projekt wählen.");
      return;
    }
    const res = await fetch("/api/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ studentId, projectId: Number(directChoice) }),
    });
    const body = await res.json();
    if (!res.ok) {
      setError(body?.error || "Speichern fehlgeschlagen.");
      return;
    }
    router.push("/thanks");
  };

  if (!settings) return null;

  const startGateActive = Boolean(settings.selectionStartEnabled) && settings.selectionStartAt ? new Date(settings.selectionStartAt) : null;
  const notYetOpen = startGateActive ? new Date() < startGateActive : false;

  return (
    <div className="max-w-3xl mx-auto p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Projektauswahl</h1>
      {notYetOpen ? (
        <div className="p-4 border rounded bg-yellow-900/30 border-yellow-700 text-yellow-200">
          Die Projektauswahl ist noch nicht freigeschaltet.
          {startGateActive && (
            <div className="text-sm mt-1">Start: {new Date(startGateActive).toLocaleString()}</div>
          )}
        </div>
      ) : settings.selectionModel === "RANKED" ? (
        <div className="space-y-6">
          <div className="p-4 rounded border border-gray-700 bg-gray-900/40">
            <label className="block text-sm font-medium mb-2">Erstwunsch</label>
            <select
              className="w-full border border-gray-700 rounded p-2 bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={choice1}
              onChange={(e) => setChoice1(Number(e.target.value))}
            >
              <option value="">Bitte wählen</option>
              {visibleProjects.map((p) => (
                <option key={p.id} value={p.id}>{optionLabel(p)}</option>
              ))}
            </select>
            {choice1 !== "" && (
              <div className="mt-2 text-sm text-gray-300">
                {(projectById.get(Number(choice1))?.description || "Keine Beschreibung vorhanden.")}
              </div>
            )}
          </div>
          <div className="p-4 rounded border border-gray-700 bg-gray-900/40">
            <label className="block text-sm font-medium mb-2">Zweitwunsch</label>
            <select
              className="w-full border border-gray-700 rounded p-2 bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={choice2}
              onChange={(e) => setChoice2(Number(e.target.value))}
            >
              <option value="">Bitte wählen</option>
              {visibleProjects.map((p) => (
                <option key={p.id} value={p.id}>{optionLabel(p)}</option>
              ))}
            </select>
            {choice2 !== "" && (
              <div className="mt-2 text-sm text-gray-300">
                {(projectById.get(Number(choice2))?.description || "Keine Beschreibung vorhanden.")}
              </div>
            )}
          </div>
          <div className="p-4 rounded border border-gray-700 bg-gray-900/40">
            <label className="block text-sm font-medium mb-2">Drittwunsch</label>
            <select
              className="w-full border border-gray-700 rounded p-2 bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={choice3}
              onChange={(e) => setChoice3(Number(e.target.value))}
            >
              <option value="">Bitte wählen</option>
              {visibleProjects.map((p) => (
                <option key={p.id} value={p.id}>{optionLabel(p)}</option>
              ))}
            </select>
            {choice3 !== "" && (
              <div className="mt-2 text-sm text-gray-300">
                {(projectById.get(Number(choice3))?.description || "Keine Beschreibung vorhanden.")}
              </div>
            )}
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          {message && <p className="text-green-700 text-sm">{message}</p>}
          <button onClick={rankedSubmit} className="px-4 py-2 bg-blue-600 text-white rounded">Speichern</button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-4 rounded border border-gray-700 bg-gray-900/40">
            <label className="block text-sm font-medium mb-2">Projekt</label>
            <select
              className="w-full border border-gray-700 rounded p-2 bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={directChoice}
              onChange={(e) => setDirectChoice(Number(e.target.value))}
            >
              <option value="">Bitte wählen</option>
              {visibleProjects.map((p) => (
                <option key={p.id} value={p.id}>{optionLabel(p)}</option>
              ))}
            </select>
            {directChoice !== "" && (
              <div className="mt-2 text-sm text-gray-300">
                {(projectById.get(Number(directChoice))?.description || "Keine Beschreibung vorhanden.")}
              </div>
            )}
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          {message && <p className="text-green-700 text-sm">{message}</p>}
          <button onClick={directSubmit} className="px-4 py-2 bg-blue-600 text-white rounded">Speichern</button>
        </div>
      )}
    </div>
  );
}

