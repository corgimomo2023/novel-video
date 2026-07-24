# 小說影片工作室

Production MVP for `video.example.com`.

## Stack

- React + TypeScript + Vite + Tailwind
- FastAPI + Python stdlib SQLite
- Signed HttpOnly admin session cookie
- Local media volume + FFmpeg Mock GPU worker
- SSE progress endpoint
- Single Docker container behind Nginx

## Local run

```bash
cp .env.example .env
# Set a real password and session secret
sudo docker compose up -d --build novel-video
curl http://127.0.0.1:8094/api/health
```

## Tests

```bash
(cd backend && .venv/bin/python -m pytest -q)
(cd frontend && npm test && npm run lint && npm run build)
```

## GPU boundary

`GPU_PROVIDER=mock` produces real MP4 placeholder clips without GPU cost. RunPod integration will replace only the provider/worker boundary; projects, shots, jobs, UI, storage and FFmpeg lifecycle remain unchanged.

Secrets stay in `.env` and must never be committed. Important data is under `./data`.
