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

## Routes

| Path | Description |
|------|-------------|
| `/` | Hello world |
| `/tictactoe` | Playable 3×3 tic-tac-toe (two-player, server-side state) |

## Project layout

```
whaleapp/
├── app.py                    # HTTP server (stdlib only)
├── test_tictactoe.py         # Unit + integration tests
├── requirements-dev.txt      # Dev dependencies (coverage)
├── .coveragerc               # Coverage configuration
├── .github/workflows/ci.yml  # CI: run tests + coverage on push/PR
├── Dockerfile                # Minimal Python 3 image
└── README.md                 # This file
```

## Tests & coverage

```bash
# Install dev dependencies (coverage)
pip install -r requirements-dev.txt

# Run tests only
python3 test_tictactoe.py

# Run tests with coverage report
coverage run test_tictactoe.py
coverage report -m         # text summary with missing lines
coverage html              # HTML report in htmlcov/
```

CI runs on every push and PR via GitHub Actions; the build fails if
coverage drops below the `fail_under` threshold set in `.coveragerc`.
