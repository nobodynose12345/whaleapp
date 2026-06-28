#!/usr/bin/env python3
"""WhaleApp – minimal HTTP server (stdlib only)."""

import collections
import http.cookies
import uuid
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "0.0.0.0"
PORT = 8080

# ---------------------------------------------------------------------------
# In-memory game store (capped LRU to prevent unbounded memory growth)
# ---------------------------------------------------------------------------

MAX_GAMES = 10_000
GAMES: collections.OrderedDict[str, dict] = collections.OrderedDict()


def _new_game() -> dict:
    return {"board": [" "] * 9, "turn": "X", "winner": None, "done": False}


def _get_or_create_game(game_id: str) -> dict:
    if game_id in GAMES:
        GAMES.move_to_end(game_id)  # mark as recently used
        return GAMES[game_id]
    if len(GAMES) >= MAX_GAMES:
        GAMES.popitem(last=False)  # evict least-recently-used entry
    GAMES[game_id] = _new_game()
    return GAMES[game_id]


def _reset_game(game_id: str) -> None:
    if game_id in GAMES:
        GAMES.move_to_end(game_id)
    elif len(GAMES) >= MAX_GAMES:
        GAMES.popitem(last=False)
    GAMES[game_id] = _new_game()


# ---------------------------------------------------------------------------
# Game logic
# ---------------------------------------------------------------------------

_WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diagonals
]


def check_winner(board: list) -> str | None:
    for a, b, c in _WIN_LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: list) -> bool:
    return " " not in board


def make_move(game: dict, idx: int) -> None:
    """Apply a move at board index idx.  No-op if invalid."""
    if game["done"]:
        return
    if not (0 <= idx <= 8):
        return
    if game["board"][idx] != " ":
        return
    game["board"][idx] = game["turn"]
    winner = check_winner(game["board"])
    if winner:
        game["winner"] = winner
        game["done"] = True
    elif is_draw(game["board"]):
        game["done"] = True
    else:
        game["turn"] = "O" if game["turn"] == "X" else "X"


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

def _parse_game_id(raw_cookie: str) -> str | None:
    """Return a validated UUID4 game_id from the Cookie header, or None."""
    if not raw_cookie:
        return None
    try:
        c = http.cookies.SimpleCookie(raw_cookie)
    except http.cookies.CookieError:
        return None
    if "game_id" not in c:
        return None
    value = c["game_id"].value
    try:
        parsed = uuid.UUID(value, version=4)
    except ValueError:
        return None
    # Ensure canonical form (rejects non-canonical hex strings)
    if str(parsed) != value:
        return None
    return value


def _read_game_id(handler: "WhaleHandler") -> tuple[str, bool]:
    """Return (game_id, is_new).  is_new=True when a fresh cookie was minted."""
    raw = handler.headers.get("Cookie", "")
    game_id = _parse_game_id(raw)
    if game_id:
        return game_id, False
    return str(uuid.uuid4()), True


_COOKIE_ATTRS = "Path=/; HttpOnly; SameSite=Lax"


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def render_tictactoe(game: dict) -> str:
    board = game["board"]

    # Status message
    if game["winner"]:
        status = f"🎉 Player <strong>{game['winner']}</strong> wins!"
        status_color = "#2e7d32"
    elif game["done"]:
        status = "It's a <strong>draw</strong>!"
        status_color = "#e65100"
    else:
        status = f"Player <strong>{game['turn']}</strong>'s turn"
        status_color = "#1565c0"

    # Build board cells
    cells_html = ""
    for i, cell in enumerate(board):
        if cell == " " and not game["done"]:
            # Clickable cell – submits a form POST
            cells_html += f"""
        <form method="post" action="/tictactoe/move" style="margin:0;padding:0;">
          <input type="hidden" name="cell" value="{i}">
          <button type="submit" class="cell empty" aria-label="Cell {i}"></button>
        </form>"""
        else:
            color = "#c62828" if cell == "X" else "#1565c0"
            cells_html += f"""
        <div class="cell filled" style="color:{color};">{cell if cell != " " else ""}</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tic-Tac-Toe – WhaleApp</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background: #f0f4f8;
    }}
    h1 {{ font-size: 2rem; margin-bottom: 0.25rem; color: #212121; }}
    .subtitle {{ color: #555; margin-bottom: 1.5rem; font-size: 0.95rem; }}
    .status {{
      font-size: 1.2rem;
      margin-bottom: 1.25rem;
      color: {status_color};
    }}
    .board {{
      display: grid;
      grid-template-columns: repeat(3, 100px);
      grid-template-rows: repeat(3, 100px);
      gap: 6px;
      background: #90a4ae;
      padding: 6px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,.15);
    }}
    .cell {{
      width: 100px;
      height: 100px;
      background: #fff;
      border: none;
      border-radius: 4px;
      font-size: 2.8rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .cell.empty {{
      cursor: pointer;
      transition: background .15s;
    }}
    .cell.empty:hover {{ background: #e3f2fd; }}
    .cell.filled {{ font-family: inherit; }}
    .new-game {{
      margin-top: 1.5rem;
      display: inline-block;
      padding: 0.6rem 1.4rem;
      background: #1976d2;
      color: #fff;
      text-decoration: none;
      border-radius: 6px;
      font-size: 1rem;
      border: none;
      cursor: pointer;
    }}
    .new-game:hover {{ background: #1565c0; }}
    .home {{ margin-top: 0.75rem; font-size: 0.85rem; color: #555; text-decoration: none; }}
    .home:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>🐋 Tic-Tac-Toe</h1>
  <p class="subtitle">Two players · X goes first</p>
  <p class="status">{status}</p>
  <div class="board">
    {cells_html}
  </div>
  <form method="post" action="/tictactoe/new">
    <button type="submit" class="new-game">New Game</button>
  </form>
  <a href="/" class="home">← Back to WhaleApp</a>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class WhaleHandler(BaseHTTPRequestHandler):

    def _send_html(self, html: str, status: int = 200,
                   extra_headers: list | None = None) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or []):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str,
                  extra_headers: list | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (extra_headers or []):
            self.send_header(name, value)
        self.end_headers()

    def _read_body(self) -> str | None:
        """Read and return the request body.  Returns None and sends 400 on a
        malformed Content-Length header; returns '' when length is 0 or absent."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return None  # sentinel: 400 already sent
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8", errors="replace")

    # ---- GET ---------------------------------------------------------------

    def do_GET(self):
        if self.path == "/":
            body = b"Hello from WhaleApp\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/tictactoe":
            game_id, is_new = _read_game_id(self)
            game = _get_or_create_game(game_id)
            extra: list = []
            if is_new:
                extra.append(("Set-Cookie",
                               f"game_id={game_id}; {_COOKIE_ATTRS}"))
            self._send_html(render_tictactoe(game), extra_headers=extra)

        else:
            self.send_response(404)
            self.end_headers()

    # ---- POST --------------------------------------------------------------

    def do_POST(self):
        game_id, is_new = _read_game_id(self)
        extra: list = []
        if is_new:
            extra.append(("Set-Cookie",
                           f"game_id={game_id}; {_COOKIE_ATTRS}"))

        if self.path == "/tictactoe/move":
            body = self._read_body()
            if body is None:
                return  # 400 already sent by _read_body
            params = urllib.parse.parse_qs(body)
            try:
                idx = int(params["cell"][0])
            except (KeyError, ValueError, IndexError):
                idx = -1
            game = _get_or_create_game(game_id)
            make_move(game, idx)
            self._redirect("/tictactoe", extra_headers=extra)

        elif self.path == "/tictactoe/new":
            self._read_body()  # drain any body; ignore errors — we redirect regardless
            _reset_game(game_id)
            self._redirect("/tictactoe", extra_headers=extra)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # quieter logs
        print(f"[WhaleApp] {self.address_string()} – {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), WhaleHandler)
    print(f"[WhaleApp] Listening on http://{HOST}:{PORT}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WhaleApp] Shutting down.")
        server.server_close()
