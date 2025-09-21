Wahl-Portal
===========

Funktionen
----------
- Anmeldung: Vorname, Nachname, Klasse wählen
- Auswahl: Direktwahl oder Erst-/Zweit-/Drittwahl (umschaltbar im Admin)
- Admin: Login mit Passwort, Einstellungen, Klassen und Projekte verwalten
- Zuteilung: Einfaches Losverfahren nach Priorität (1 vor 2 vor 3)
- Export: CSV gesamt, CSV nach Projekten, ZIP pro Klasse

Tech Stack
----------
- Next.js (Pages Router, TypeScript, Tailwind)
- Prisma + SQLite (lokal)
- NextAuth Credentials (Passwort-Login für Admin)

Entwicklung
-----------
1. Env anlegen (.env)
```
DATABASE_URL="file:./dev.db"
NEXTAUTH_SECRET="change-me-in-prod"
NEXTAUTH_URL="http://localhost:3000"
ADMIN_PASSWORD="admin-change-me"
```
2. Prisma migrieren und starten
```
npm run prisma:migrate
npm run dev
```

Seiten
------
- /: Schüler-Anmeldung (Vorname, Nachname, Klasse)
- /select?studentId=…: Projektauswahl je nach Modell
- /admin/login: Admin Login
- /admin/settings: Einstellungen, Klassen/Projekte, Export, Zuteilung

Render Deployment (GitHub Auto-Deploy)
--------------------------------------
1. Repository nach GitHub pushen
2. Render Web Service erstellen (Node 18+)
3. Build Command: `npm run build`
4. Start Command: `npm start`
5. Environment Vars setzen:
   - `DATABASE_URL` (z. B. `file:./dev.db` für SQLite oder eine externe DB)
   - `NEXTAUTH_SECRET` (lange zufällige Zeichenkette)
   - `NEXTAUTH_URL` (Produktions-URL)
   - `ADMIN_PASSWORD` (Admin-Passwort)
6. (Optional) Prisma bei Erststart migrieren: `npx prisma migrate deploy`

Hinweise
--------
- Für echte Produktion empfiehlt sich Postgres statt SQLite.
- Bei Direktwahl wird Kapazität pro Projekt sofort geprüft.
- Bei Ranglistenwahl werden Wahlen gespeichert und via Admin „Zuteilen“ verteilt.
