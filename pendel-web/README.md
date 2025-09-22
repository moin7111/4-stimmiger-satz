## Pendel-Simulator (Streamlit, isoliert)

Isolierte Web-App (separates Projekt, Container, vHost) – keinerlei Berührung mit `wahl-portal`.

### Features
- RK4 oder symplektischer Euler, Sub-Steps, Energie-Drift-Monitoring
- Plotly-Visualisierung inklusive Spur
- Pro-Session State via Streamlit Session-State

### Lokal starten (ohne Docker)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run server/app_streamlit.py --server.port 8501 --server.headless true
```

### Docker
```bash
docker build -t pendel-web:latest .
docker run --rm -p 127.0.0.1:18501:8501 \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --name pendel-web pendel-web:latest
```
Oder mit Compose:
```bash
docker compose up -d --build
```

### NGINX vHost (Beispiel)
`deploy/nginx/pendel.conf` anpassen (`server_name`) und aktivieren. Wichtig: Upgrades/WebSocket sind erlaubt, Proxy läuft nur gegen 127.0.0.1:18501.

### Sicherheit / Trennung
- Eigener Container, non-root, `cap_drop: ALL`, read-only FS
- Port nur auf `127.0.0.1` gebunden; externer Zugriff nur via separatem vHost/Reverse Proxy
- Kein gemeinsames Volume/Netzwerk mit `wahl-portal`

### PaaS (Render/Railway)
- `requirements.txt` + `Procfile` vorhanden
- Start: `web: streamlit run server/app_streamlit.py --server.port $PORT --server.headless true`

