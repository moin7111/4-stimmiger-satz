import { useEffect, useState } from "react";
import Link from "next/link";

type Student = { id: string; firstName: string; lastName: string; classGroup?: { id: number; name: string } | null };
type Summary = { total: number; assigned: number; unassigned: number; rank1: number; rank2: number; rank3: number };

export default function Allocation() {
  const [unassigned, setUnassigned] = useState<Student[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    // Load unassigned list and allocation summary after allocation
    const load = async () => {
      try {
        const [unassignedRes] = await Promise.all([
          fetch(`/api/students?unassigned=true&take=5000`),
        ]);
        if (unassignedRes.ok) {
          setUnassigned(await unassignedRes.json());
        }
        const stored = typeof window !== "undefined" ? sessionStorage.getItem("allocationSummary") : null;
        if (stored) setSummary(JSON.parse(stored));
      } catch {}
    };
    load();
  }, []);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Zuteilung abgeschlossen</h1>
      <p className="text-gray-700">Lade die Tabellen mit den Ergebnissen herunter:</p>
      <div className="flex gap-3 flex-wrap">
        <Link href="/api/export?type=overall" className="px-3 py-2 border rounded">Gesamtliste (CSV)</Link>
        <Link href="/api/export?type=by-project-zip" className="px-3 py-2 border rounded">Projekte (ZIP, je Projekt CSV)</Link>
        <Link href="/api/export?type=by-class-zip" className="px-3 py-2 border rounded">Klassen (ZIP, je Klasse CSV)</Link>
      </div>
      {summary && (
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <div><span className="font-medium">Gesamt:</span> {summary.total}</div>
          <div><span className="font-medium">Zugeordnet:</span> {summary.assigned}</div>
          <div><span className="font-medium">Nicht zugeteilt:</span> {summary.unassigned}</div>
          <div><span className="font-medium">1. Wahl:</span> {summary.rank1}</div>
          <div><span className="font-medium">2. Wahl:</span> {summary.rank2}</div>
          <div><span className="font-medium">3. Wahl:</span> {summary.rank3}</div>
        </div>
      )}
      {unassigned.length > 0 && (
        <div className="mt-6">
          <h2 className="text-xl font-semibold mb-2">Nicht zugeteilt</h2>
          <div className="overflow-auto">
            <table className="w-full text-sm border">
              <thead className="bg-gray-50 text-black">
                <tr>
                  <th className="text-left p-2 border">Name</th>
                  <th className="text-left p-2 border">Klasse</th>
                </tr>
              </thead>
              <tbody>
                {unassigned.map((s) => (
                  <tr key={s.id} className="border-t">
                    <td className="p-2">{s.firstName} {s.lastName}</td>
                    <td className="p-2">{s.classGroup?.name || "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="pt-4">
        <Link href="/admin/settings" className="text-sm underline">Zurück zu Einstellungen</Link>
      </div>
    </div>
  );
}

export function getServerSideProps() {
  return { props: {} };
}

