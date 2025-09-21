import { useEffect, useState } from "react";
import Link from "next/link";

type ClassGroup = { id: number; name: string };

export default function Home() {
  const [classes, setClasses] = useState<ClassGroup[]>([]);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [classGroupId, setClassGroupId] = useState<number | null>(null);
  const [studentId, setStudentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/class-groups").then(async (r) => setClasses(await r.json()));
  }, []);

  async function createStudent(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!firstName || !lastName || !classGroupId) {
      setError("Bitte alle Felder ausfüllen.");
      return;
    }
    const res = await fetch("/api/students", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ firstName, lastName, classGroupId }),
    });
    if (!res.ok) {
      setError("Anmeldung fehlgeschlagen.");
      return;
    }
    const s = await res.json();
    setStudentId(s.id);
  }

  if (studentId) {
    return (
      <div className="max-w-xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-4">Wahlportal</h1>
        <p className="mb-6">Danke {firstName} {lastName}. Weiter zur Auswahl:</p>
        <Link href={`/select?studentId=${studentId}`} className="px-4 py-2 bg-blue-600 text-white rounded">Zur Auswahl</Link>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Wahlportal - Anmeldung</h1>
      <form onSubmit={createStudent} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Vorname</label>
          <input className="w-full border rounded p-2" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm font-medium">Nachname</label>
          <input className="w-full border rounded p-2" value={lastName} onChange={(e) => setLastName(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm font-medium">Klasse</label>
          <select className="w-full border rounded p-2" value={classGroupId ?? ""} onChange={(e) => setClassGroupId(Number(e.target.value))}>
            <option value="" disabled>Bitte wählen</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">Weiter</button>
      </form>

      <div className="mt-8">
        <Link href="/admin/login" className="text-sm underline">Admin Login</Link>
      </div>
    </div>
  );
}
