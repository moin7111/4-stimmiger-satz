import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/router";
import Link from "next/link";

type Settings = { selectionModel: "DIRECT" | "RANKED" };
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
                  "• alle Zuteilungen",
                  "\nEinstellungen werden auf Standard (Direktwahl) zurückgesetzt.",
                ].join("\n")
              );
              if (!confirmed) return;
              const res = await fetch("/api/admin/reset", { method: "POST" });
              if (res.ok) {
                setSettings({ selectionModel: "DIRECT" });
                setClasses([]);
                setProjects([]);
                setMsg("Alle Daten wurden gelöscht.");
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

