# WhaleApp 🐋

A tiny demo web application built with **Python 3 standard library only** –
no third-party packages required.

## Run locally

```bash
python3 app.py
# → Listening on http://0.0.0.0:8080
curl http://localhost:8080/
# → Hello from WhaleApp
```

## Run with Docker

```bash
docker build -t whaleapp .
docker run --rm -p 8080:8080 whaleapp
curl http://localhost:8080/
```

## Project layout

```
whaleapp/
├── app.py       # HTTP server (< 40 lines, stdlib only)
├── Dockerfile   # Minimal Python 3 image
└── README.md    # This file
```
