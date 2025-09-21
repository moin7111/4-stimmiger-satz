import Link from "next/link";

export default function Allocation() {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Zuteilung abgeschlossen</h1>
      <p className="text-gray-700">Lade die Tabellen mit den Ergebnissen herunter:</p>
      <div className="flex gap-3 flex-wrap">
        <Link href="/api/export?type=overall" className="px-3 py-2 border rounded">Gesamtliste (CSV)</Link>
        <Link href="/api/export?type=by-project-zip" className="px-3 py-2 border rounded">Projekte (ZIP, je Projekt CSV)</Link>
        <Link href="/api/export?type=by-class-zip" className="px-3 py-2 border rounded">Klassen (ZIP, je Klasse CSV)</Link>
      </div>
      <div className="pt-4">
        <Link href="/admin/settings" className="text-sm underline">Zurück zu Einstellungen</Link>
      </div>
    </div>
  );
}

export function getServerSideProps() {
  return { props: {} };
}

