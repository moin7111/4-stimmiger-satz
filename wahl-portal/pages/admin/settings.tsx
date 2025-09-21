import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/router";
import Link from "next/link";

type Settings = { selectionModel: "DIRECT" | "RANKED"; selectionStartAt?: string | null; selectionStartEnabled?: boolean };
type ClassGroup = { id: number; name: string };
type Project = { id: number; name: string; leader: string; description?: string | null; capacity: number; allowedClasses: { classGroupId: number; classGroup: { id: number; name: string } }[] };

export default function AdminSettings() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [classes, setClasses] = useState<ClassGroup[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [newClassName, setNewClassName] = useState("");
  const [projectForm, setProjectForm] = useState({ name: "", leader: "", description: "", capacity: 20, allowedClassIds: [] as number[] });
  const [msg, setMsg] = useState<string | null>(null);
  const [search, setSearch] = useState({ q: "", classGroupId: "", projectId: "" });
  type StudentSummary = {
    id: string;
    firstName: string;
    lastName: string;
    classGroupId: number;
    classGroup?: { id: number; name: string } | null;
    assignedProjectId?: number | null;
    assignedProject?: { id: number; name: string } | null;
    selections?: { rank: number; projectId: number }[];
  };

  const [results, setResults] = useState<StudentSummary[]>([]);
  const [editing, setEditing] = useState<StudentSummary | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      Promise.all([
        fetch("/api/settings").then((r) => r.json()),
        fetch("/api/class-groups").then((r) => r.json()),
        fetch("/api/projects").then((r) => r.json()),
      ]).then(([s, c, p]) => {
        setSettings(s);
        setClasses(c);
        setProjects(p);
      });
    }
  }, [status]);

  if (status === "loading") return null;
  if (!session) return <div className="p-6">Nicht autorisiert.</div>;

  const setModel = async (model: "DIRECT" | "RANKED") => {
    const res = await fetch("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selectionModel: model }) });
    if (res.ok) {
      setSettings(await res.json());
      setMsg("Gespeichert");
    }
  };

  const toLocalDatetimeValue = (iso?: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    const y = d.getFullYear();
    const m = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const h = pad(d.getHours());
    const min = pad(d.getMinutes());
    return `${y}-${m}-${day}T${h}:${min}`;
  };

  const addClass = async () => {
    if (!newClassName) return;
    const res = await fetch("/api/class-groups", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newClassName }) });
    if (res.ok) {
      const c = await res.json();
      setClasses((prev) => [...prev, c]);
      setNewClassName("");
    }
  };

  const addProject = async () => {
    const res = await fetch("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(projectForm) });
    if (res.ok) {
      const p = await res.json();
      setProjects((prev) => [...prev, p]);
      setProjectForm({ name: "", leader: "", description: "", capacity: 20, allowedClassIds: [] });
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Einstellungen</h1>
        <button onClick={() => signOut({ callbackUrl: "/" })} className="text-sm underline">Logout</button>
      </div>

      <section>
        <h2 className="text-xl font-semibold mb-2">Wahl-Modell</h2>
        <div className="flex items-center gap-4">
          <label className="inline-flex items-center gap-2">
            <input type="radio" name="model" checked={settings?.selectionModel === "DIRECT"} onChange={() => setModel("DIRECT")} />
            Direktwahl
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="radio" name="model" checked={settings?.selectionModel === "RANKED"} onChange={() => setModel("RANKED")} />
            Erst-/Zweit-/Drittwahl
          </label>
        </div>
        {msg && <p className="text-green-700 text-sm mt-2">{msg}</p>}
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={Boolean(settings?.selectionStartEnabled)}
              onChange={async (e) => {
                const res = await fetch("/api/settings", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ selectionStartEnabled: e.target.checked }),
                });
                if (res.ok) {
                  setSettings(await res.json());
                  setMsg(e.target.checked ? "Freigabe aktiviert" : "Freigabe deaktiviert");
                }
              }}
            />
            <span className="text-sm">Freigabe per Datum/Uhrzeit aktivieren</span>
          </label>
          <div className="flex items-center gap-2">
            <input
              type="datetime-local"
              className="border rounded p-2"
              value={toLocalDatetimeValue(settings?.selectionStartAt ?? null)}
              onChange={(e) => setSettings((prev) => (prev ? { ...prev, selectionStartAt: e.target.value ? new Date(e.target.value).toISOString() : null } : prev))}
            />
            <button
              onClick={async () => {
                const res = await fetch("/api/settings", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ selectionStartAt: settings?.selectionStartAt ?? null }),
                });
                if (res.ok) {
                  setSettings(await res.json());
                  setMsg("Startzeit aktualisiert");
                }
              }}
              className="px-3 py-2 border rounded"
            >
              Startzeit speichern
            </button>
          </div>
          
        </div>
        <div className="mt-4 flex gap-3">
          <button
            onClick={async () => {
              const confirmed = window.confirm(
                [
                  "Sicher, dass alles gelöscht werden soll?",
                  "\nDies entfernt unwiderruflich:",
                  "• alle Klassen",
                  "• alle Projekte",
                  "• alle Anmeldungen/Einträge und Ranglisten",
                  "• alle abgegebenen Wahlen (gewählte Projekte)",
                  "• alle Zuteilungen",
                  "\nEinstellungen werden auf Standard (Direktwahl) zurückgesetzt.",
                ].join("\n")
              );
              if (!confirmed) return;
              const confirmed2 = window.confirm(
                [
                  "Letzte Bestätigung",
                  "\nDiese Aktion kann NICHT rückgängig gemacht werden.",
                  "\nJetzt endgültig ALLES löschen?",
                ].join("\n")
              );
              if (!confirmed2) return;
              const res = await fetch("/api/admin/reset", { method: "POST" });
              if (res.ok) {
                setSettings({ selectionModel: "DIRECT" });
                setClasses([]);
                setProjects([]);
                setMsg("Alle Daten (Klassen, Projekte, Anmeldungen/Ranglisten, Wahlen und Zuteilungen) wurden gelöscht.");
              } else {
                try {
                  const body = await res.json();
                  setMsg(body?.error ? `Fehler: ${body.error}` : "Fehler beim Zurücksetzen");
                } catch {
                  setMsg("Fehler beim Zurücksetzen");
                }
              }
            }}
            className="px-3 py-2 border rounded"
          >
            Alles zurücksetzen
          </button>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Einträge suchen & bearbeiten</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          <input className="border rounded p-2" placeholder="Name (Teil)" value={search.q} onChange={(e) => setSearch((s) => ({ ...s, q: e.target.value }))} />
          <select className="border rounded p-2" value={search.classGroupId} onChange={(e) => setSearch((s) => ({ ...s, classGroupId: e.target.value }))}>
            <option value="">Alle Klassen</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select className="border rounded p-2" value={search.projectId} onChange={(e) => setSearch((s) => ({ ...s, projectId: e.target.value }))}>
            <option value="">Alle Projekte</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className="mt-2 flex gap-2">
          <button
            className="px-3 py-2 border rounded"
            onClick={async () => {
              const params = new URLSearchParams();
              if (search.q) params.set("q", search.q);
              if (search.classGroupId) params.set("classGroupId", search.classGroupId);
              if (search.projectId) params.set("projectId", search.projectId);
              const res = await fetch(`/api/students?${params.toString()}`);
              if (res.ok) setResults(await res.json());
            }}
          >
            Suchen
          </button>
          <button className="px-3 py-2 border rounded" onClick={() => { setSearch({ q: "", classGroupId: "", projectId: "" }); setResults([]); }}>Zurücksetzen</button>
        </div>
        {results.length > 0 && (
          <div className="mt-3 overflow-auto">
            <table className="w-full text-sm border">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2 border">Name</th>
                  <th className="text-left p-2 border">Klasse</th>
                  <th className="text-left p-2 border">Zuteilung</th>
                  <th className="text-left p-2 border">Aktion</th>
                </tr>
              </thead>
              <tbody>
                {results.map((s: StudentSummary) => (
                  <tr key={s.id} className="border-t">
                    <td className="p-2">{s.firstName} {s.lastName}</td>
                    <td className="p-2">{s.classGroup?.name}</td>
                    <td className="p-2">{s.assignedProject ? s.assignedProject.name : "–"}</td>
                    <td className="p-2"><button className="underline" onClick={() => setEditing(s)}>Bearbeiten</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {editing && (
          <div className="mt-4 p-4 border rounded">
            <h3 className="font-semibold mb-2">Eintrag bearbeiten</h3>
            <div className="grid gap-2 sm:grid-cols-3">
              <input className="border rounded p-2" value={editing.firstName} onChange={(e) => setEditing((prev) => (prev ? { ...prev, firstName: e.target.value } : prev))} />
              <input className="border rounded p-2" value={editing.lastName} onChange={(e) => setEditing((prev) => (prev ? { ...prev, lastName: e.target.value } : prev))} />
              <select className="border rounded p-2" value={editing.classGroupId} onChange={(e) => setEditing((prev) => (prev ? { ...prev, classGroupId: Number(e.target.value) } : prev))}>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            {settings?.selectionModel === "DIRECT" ? (
              <div className="mt-3">
                <label className="block text-sm mb-1">Zugeordnetes Projekt (optional)</label>
                <select className="border rounded p-2" value={editing.assignedProjectId ?? ""} onChange={(e) => setEditing((prev) => (prev ? { ...prev, assignedProjectId: e.target.value ? Number(e.target.value) : null } : prev))}>
                  <option value="">– keine –</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                {[1,2,3].map((rank) => (
                  <div key={rank}>
                    <label className="block text-sm mb-1">{rank}. Wahl</label>
                    <select
                      className="border rounded p-2 w-full"
                      value={editing.selections?.find((s) => s.rank === rank)?.projectId ?? ""}
                      onChange={(e) => {
                        const pid = e.target.value ? Number(e.target.value) : null;
                        setEditing((prev) => {
                          if (!prev) return prev;
                          const others = (prev.selections || []).filter((s) => s.rank !== rank);
                          if (pid && others.some((s) => s.projectId === pid)) {
                            return prev; // prevent duplicates client-side
                          }
                          return pid ? { ...prev, selections: [...others, { rank, projectId: pid }] } : { ...prev, selections: others };
                        });
                      }}
                    >
                      <option value="">– keine –</option>
                      {projects.map((p) => {
                        const chosenIds = new Set((editing.selections || []).filter((s) => s.rank !== rank).map((s) => s.projectId));
                        const disabled = chosenIds.has(p.id);
                        return <option key={p.id} value={p.id} disabled={disabled}>{p.name}{disabled ? " (bereits gewählt)" : ""}</option>;
                      })}
                    </select>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-3 flex gap-2">
              <button
                className="px-3 py-2 bg-blue-600 text-white rounded"
                onClick={async () => {
                  type UpdateStudentPayload = {
                    studentId: string;
                    firstName?: string;
                    lastName?: string;
                    classGroupId?: number;
                    assignedProjectId?: number | null;
                    choices?: { projectId: number; rank: number }[];
                  };
                  const payload: UpdateStudentPayload = {
                    studentId: editing.id,
                    firstName: editing.firstName,
                    lastName: editing.lastName,
                    classGroupId: editing.classGroupId,
                  };
                  if (settings?.selectionModel === "DIRECT") {
                    payload.assignedProjectId = editing.assignedProjectId ?? null;
                  } else {
                    const choices: { projectId: number; rank: number }[] = (editing.selections || [])
                      .filter((s) => typeof s.projectId === "number")
                      .map((s) => ({ projectId: s.projectId, rank: s.rank }))
                      .sort((a, b) => a.rank - b.rank);
                    // Ensure unique projects client-side
                    const unique = new Set(choices.map((c) => c.projectId));
                    if (unique.size !== choices.length) {
                      setMsg("Jedes Projekt darf nur einmal gewählt werden.");
                      return;
                    }
                    if (choices.length > 0) payload.choices = choices;
                  }
                  const res = await fetch("/api/students", {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                  });
                  if (res.ok) {
                    setMsg("Eintrag gespeichert");
                    setEditing(null);
                  }
                }}
              >
                Speichern
              </button>
              <button
                className="px-3 py-2 border rounded"
                onClick={async () => {
                  if (!editing) return;
                  const confirmed = window.confirm("Diesen Eintrag wirklich löschen?");
                  if (!confirmed) return;
                  const res = await fetch("/api/students", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: editing.id }) });
                  if (res.status === 204) {
                    setMsg("Eintrag gelöscht");
                    setEditing(null);
                    setResults((prev) => prev.filter((s) => s.id !== editing.id));
                  }
                }}
              >
                Löschen
              </button>
              <button className="px-3 py-2 border rounded" onClick={() => setEditing(null)}>Abbrechen</button>
            </div>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Klassen</h2>
        <div className="flex gap-2">
          <input className="border rounded p-2" placeholder="z. B. 11, 12, 9a" value={newClassName} onChange={(e) => setNewClassName(e.target.value)} />
          <button onClick={addClass} className="px-4 py-2 bg-blue-600 text-white rounded">Hinzufügen</button>
        </div>
        <ul className="mt-3 list-disc pl-6">
          {classes.map((c) => (
            <li key={c.id}>{c.name}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Projekte</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <input className="w-full border rounded p-2" placeholder="Name" value={projectForm.name} onChange={(e) => setProjectForm((f) => ({ ...f, name: e.target.value }))} />
            <input className="w-full border rounded p-2" placeholder="Leitung" value={projectForm.leader} onChange={(e) => setProjectForm((f) => ({ ...f, leader: e.target.value }))} />
            <textarea className="w-full border rounded p-2" placeholder="Beschreibung (optional)" value={projectForm.description} onChange={(e) => setProjectForm((f) => ({ ...f, description: e.target.value }))} />
            <input className="w-full border rounded p-2" type="number" min={1} placeholder="Teilnehmerzahl" value={projectForm.capacity} onChange={(e) => setProjectForm((f) => ({ ...f, capacity: Number(e.target.value) }))} />
            <div>
              <div className="text-sm font-medium mb-1">Erlaubte Klassen</div>
              <div className="flex flex-wrap gap-2">
                {classes.map((c) => {
                  const checked = projectForm.allowedClassIds.includes(c.id);
                  return (
                    <label key={c.id} className="inline-flex items-center gap-1 text-sm border rounded px-2 py-1">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) =>
                          setProjectForm((f) => ({
                            ...f,
                            allowedClassIds: e.target.checked
                              ? [...f.allowedClassIds, c.id]
                              : f.allowedClassIds.filter((x) => x !== c.id),
                          }))
                        }
                      />
                      {c.name}
                    </label>
                  );
                })}
              </div>
            </div>
            <button onClick={addProject} className="px-4 py-2 bg-blue-600 text-white rounded">Projekt anlegen</button>
          </div>
          <div>
            <ul className="space-y-2">
              {projects.map((p) => (
                <li key={p.id} className="border rounded p-3">
                  <div className="font-medium">{p.name}</div>
                  <div className="text-sm text-gray-600">{p.leader}</div>
                  <div className="text-sm">Kapazität: {p.capacity}</div>
                  <div className="text-xs text-gray-600">Klassen: {p.allowedClasses.map((ac) => ac.classGroup.name).join(", ") || "alle"}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Export</h2>
        <div className="flex gap-3 flex-wrap">
          <Link href="/api/export?type=overall" className="px-3 py-2 border rounded">Gesamtliste (CSV)</Link>
          <Link href="/api/export?type=by-project-zip" className="px-3 py-2 border rounded">Projekte (ZIP, je Projekt CSV)</Link>
          <Link href="/api/export?type=by-class-zip" className="px-3 py-2 border rounded">Klassen (ZIP, je Klasse CSV)</Link>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Zuteilung</h2>
        <div className="space-y-2">
          <div className="text-sm text-gray-700">Nur für Modus „Erst-/Zweit-/Drittwahl“ (Ranglisten-Modell)</div>
          <button
            onClick={async () => {
              await fetch("/api/allocate", { method: "POST" });
              router.push("/admin/allocation");
            }}
            className="px-4 py-2 bg-emerald-600 text-white rounded"
          >
            Zuteilen (nur Ranglisten-Modell)
          </button>
        </div>
      </section>
    </div>
  );
}

// Force Server-Side Rendering to avoid build-time prerendering on this admin page
// which can cause issues in certain hosting environments.
export function getServerSideProps() {
  return { props: {} };
}

