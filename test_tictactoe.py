"""Unit tests for tic-tac-toe logic in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
import collections
import threading
import socket
import urllib.request
import urllib.parse
from http.server import HTTPServer

import app
from app import (
    check_winner,
    is_draw,
    make_move,
    _new_game,
    _parse_game_id,
    _get_or_create_game,
    _reset_game,
    render_tictactoe,
    _read_game_id,
    WhaleHandler,
)


# ---------------------------------------------------------------------------
# Helpers shared by store / HTTP tests (not collected by the test runner)
# ---------------------------------------------------------------------------

class _FakeHeaders:
    def __init__(self, d):
        self._d = d

    def get(self, name, default=""):
        return self._d.get(name, default)


class _FakeHandler:
    """Minimal stand-in for WhaleHandler used to test _read_game_id."""
    def __init__(self, cookie=None):
        self.headers = _FakeHeaders({"Cookie": cookie} if cookie else {})


def _save_games():
    """Return a snapshot of app.GAMES suitable for restoration.
    Each game dict is shallow-copied (board list shares identity with the
    original, but all callers clear GAMES before the snapshot is used).
    """
    return [(k, dict(v)) for k, v in app.GAMES.items()]


def _restore_games(snapshot):
    app.GAMES.clear()
    app.GAMES.update(snapshot)


def _start_server():
    """Bind an HTTPServer on a free ephemeral port and start serving in a daemon thread."""
    srv = HTTPServer(("127.0.0.1", 0), WhaleHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def _stop_server(srv):
    srv.shutdown()
    srv.server_close()


# ---------------------------------------------------------------------------
# check_winner
# ---------------------------------------------------------------------------

def test_check_winner_row():
    b = ["X", "X", "X", " ", " ", " ", " ", " ", " "]
    assert check_winner(b) == "X"

def test_check_winner_col():
    b = ["O", " ", " ", "O", " ", " ", "O", " ", " "]
    assert check_winner(b) == "O"

def test_check_winner_diag_main():
    b = ["X", " ", " ", " ", "X", " ", " ", " ", "X"]
    assert check_winner(b) == "X"

def test_check_winner_diag_anti():
    b = [" ", " ", "O", " ", "O", " ", "O", " ", " "]
    assert check_winner(b) == "O"

def test_check_winner_none():
    b = ["X", "O", "X", "O", "X", "O", "O", "X", "O"]
    # all lines blocked — no winner on this board
    assert check_winner(b) is None

def test_check_winner_empty():
    assert check_winner([" "] * 9) is None


# ---------------------------------------------------------------------------
# is_draw
# ---------------------------------------------------------------------------

def test_is_draw_full_no_winner():
    # X=0,2,5,6,7  O=1,3,4,8 — no winner
    b = ["X","O","X","O","O","X","X","X","O"]
    assert check_winner(b) is None
    assert is_draw(b) is True

def test_is_draw_not_full():
    b = ["X", "O", " ", " ", " ", " ", " ", " ", " "]
    assert is_draw(b) is False

def test_is_draw_full_with_winner():
    # is_draw only checks for absence of " "; it returns True on any full board,
    # even one with a winner.  make_move stops before calling is_draw when a
    # winner is already detected, so this path doesn't arise during gameplay.
    b = ["X","X","X","O","X","O","O","O","X"]  # full board; X wins diagonals
    assert check_winner(b) == "X"  # winner exists
    assert is_draw(b) is True      # is_draw independently returns True (board full)


# ---------------------------------------------------------------------------
# make_move
# ---------------------------------------------------------------------------

def test_make_move_basic():
    g = _new_game()
    make_move(g, 4)
    assert g["board"][4] == "X"
    assert g["turn"] == "O"
    assert g["done"] is False
    assert g["winner"] is None

def test_make_move_alternates_turns():
    g = _new_game()
    make_move(g, 0)  # X
    make_move(g, 1)  # O
    assert g["board"][0] == "X"
    assert g["board"][1] == "O"
    assert g["turn"] == "X"

def test_make_move_rejects_occupied():
    g = _new_game()
    make_move(g, 0)  # X at 0
    make_move(g, 0)  # O tries 0 — should be rejected
    assert g["board"][0] == "X"
    assert g["turn"] == "O"  # still O's turn

def test_make_move_rejects_out_of_range():
    g = _new_game()
    make_move(g, 9)   # out of range
    make_move(g, -1)  # out of range
    assert g["board"] == [" "] * 9
    assert g["turn"] == "X"

def test_make_move_detects_win():
    g = _new_game()
    # X wins top row: 0,1,2
    for cell in [0, 3, 1, 4, 2]:  # X:0 O:3 X:1 O:4 X:2
        make_move(g, cell)
    assert g["winner"] == "X"
    assert g["done"] is True

def test_make_move_detects_draw():
    g = _new_game()
    # sequence that produces a draw: X=0,2,5,6,7  O=1,3,4,8
    for cell in [0, 1, 2, 3, 5, 4, 6, 8, 7]:
        make_move(g, cell)
    assert g["winner"] is None
    assert g["done"] is True

def test_make_move_noop_after_game_over():
    g = _new_game()
    for cell in [0, 3, 1, 4, 2]:
        make_move(g, cell)
    assert g["done"] is True
    board_snapshot = g["board"][:]
    make_move(g, 5)  # should be ignored
    assert g["board"] == board_snapshot

def test_make_move_all_win_lines():
    """Every one of the 8 win lines should be detected."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        board = [" "] * 9
        board[a] = board[b] = board[c] = "X"
        assert check_winner(board) == "X", f"Failed for line ({a},{b},{c})"


# ---------------------------------------------------------------------------
# _parse_game_id
# ---------------------------------------------------------------------------

def test_parse_game_id_valid():
    gid = str(uuid.uuid4())
    raw = f"game_id={gid}"
    assert _parse_game_id(raw) == gid

def test_parse_game_id_missing():
    assert _parse_game_id("") is None
    assert _parse_game_id("other=foo") is None

def test_parse_game_id_invalid_uuid():
    assert _parse_game_id("game_id=not-a-uuid") is None
    assert _parse_game_id("game_id=12345") is None

def test_parse_game_id_non_canonical():
    # UUID with uppercase letters should be rejected
    gid = str(uuid.uuid4()).upper()
    assert _parse_game_id(f"game_id={gid}") is None


# ---------------------------------------------------------------------------
# _get_or_create_game
# ---------------------------------------------------------------------------

def test_get_or_create_game_creates_new():
    snap = _save_games()
    app.GAMES.clear()
    try:
        gid = str(uuid.uuid4())
        g = _get_or_create_game(gid)
        assert gid in app.GAMES
        assert g["board"] == [" "] * 9
        assert g["done"] is False
    finally:
        _restore_games(snap)


def test_get_or_create_game_returns_existing():
    snap = _save_games()
    app.GAMES.clear()
    try:
        gid = str(uuid.uuid4())
        g1 = _get_or_create_game(gid)
        g1["board"][0] = "X"
        g2 = _get_or_create_game(gid)
        assert g2 is g1
        assert g2["board"][0] == "X"
    finally:
        _restore_games(snap)


def test_get_or_create_game_lru_eviction():
    snap = _save_games()
    old_max = app.MAX_GAMES
    app.MAX_GAMES = 2
    app.GAMES.clear()
    try:
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        id3 = str(uuid.uuid4())
        _get_or_create_game(id1)  # LRU=id1
        _get_or_create_game(id2)  # LRU=id1
        # id1 should be evicted when id3 is created
        _get_or_create_game(id3)
        assert id1 not in app.GAMES
        assert id2 in app.GAMES
        assert id3 in app.GAMES
    finally:
        app.MAX_GAMES = old_max
        _restore_games(snap)


# ---------------------------------------------------------------------------
# _reset_game
# ---------------------------------------------------------------------------

def test_reset_game_existing():
    snap = _save_games()
    app.GAMES.clear()
    try:
        gid = str(uuid.uuid4())
        g = _get_or_create_game(gid)
        make_move(g, 0)
        assert g["board"][0] == "X"
        _reset_game(gid)
        assert app.GAMES[gid]["board"] == [" "] * 9
    finally:
        _restore_games(snap)


def test_reset_game_new_entry():
    snap = _save_games()
    app.GAMES.clear()
    try:
        gid = str(uuid.uuid4())
        assert gid not in app.GAMES
        _reset_game(gid)
        assert gid in app.GAMES
        assert app.GAMES[gid]["board"] == [" "] * 9
    finally:
        _restore_games(snap)


def test_reset_game_lru_eviction():
    snap = _save_games()
    old_max = app.MAX_GAMES
    app.MAX_GAMES = 2
    app.GAMES.clear()
    try:
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        id3 = str(uuid.uuid4())
        _get_or_create_game(id1)
        _get_or_create_game(id2)
        _reset_game(id3)  # cache full; id1 should be evicted
        assert id1 not in app.GAMES
        assert id2 in app.GAMES
        assert id3 in app.GAMES
    finally:
        app.MAX_GAMES = old_max
        _restore_games(snap)


# ---------------------------------------------------------------------------
# render_tictactoe
# ---------------------------------------------------------------------------

def test_render_in_progress():
    g = _new_game()
    html = render_tictactoe(g)
    assert "Player <strong>X</strong>" in html
    assert "Tic-Tac-Toe" in html
    # all 9 board cells should be clickable buttons
    assert html.count('class="cell empty"') == 9


def test_render_winner():
    g = _new_game()
    g["board"] = ["X", "X", "X", " ", " ", " ", " ", " ", " "]
    g["winner"] = "X"
    g["done"] = True
    html = render_tictactoe(g)
    assert "wins!" in html
    assert "#2e7d32" in html


def test_render_draw():
    g = _new_game()
    g["board"] = ["X","O","X","O","O","X","X","X","O"]
    g["done"] = True
    html = render_tictactoe(g)
    assert "draw" in html
    assert "#e65100" in html


def test_render_filled_cells():
    g = _new_game()
    make_move(g, 0)  # X at 0
    make_move(g, 4)  # O at 4
    html = render_tictactoe(g)
    assert "#c62828" in html   # X colour
    assert "#1565c0" in html   # O colour (and default for empty-done)


# ---------------------------------------------------------------------------
# _read_game_id
# ---------------------------------------------------------------------------

def test_read_game_id_from_cookie():
    gid = str(uuid.uuid4())
    handler = _FakeHandler(cookie=f"game_id={gid}")
    result_id, is_new = _read_game_id(handler)
    assert result_id == gid
    assert is_new is False


def test_read_game_id_no_cookie():
    handler = _FakeHandler()
    result_id, is_new = _read_game_id(handler)
    # should mint a fresh UUID
    uuid.UUID(result_id, version=4)  # raises if not valid uuid4
    assert is_new is True


# ---------------------------------------------------------------------------
# HTTP integration
# ---------------------------------------------------------------------------

def test_http_root():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        assert resp.status == 200
        assert b"WhaleApp" in resp.read()
    finally:
        _stop_server(srv)


def test_http_tictactoe_get_mints_cookie():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/tictactoe")
        assert resp.status == 200
        cookie = resp.headers.get("Set-Cookie", "")
        assert "game_id=" in cookie
        html = resp.read().decode()
        assert "Tic-Tac-Toe" in html
    finally:
        _stop_server(srv)


def test_http_tictactoe_get_existing_cookie():
    """Subsequent GETs with an existing cookie must NOT set a new cookie."""
    srv = _start_server()
    try:
        port = srv.server_address[1]
        # First request — mint cookie
        resp1 = urllib.request.urlopen(f"http://127.0.0.1:{port}/tictactoe")
        cookie = resp1.headers.get("Set-Cookie", "")
        gid = cookie.split("game_id=")[1].split(";")[0]
        # Second request — reuse cookie
        req2 = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe",
            headers={"Cookie": f"game_id={gid}"},
        )
        resp2 = urllib.request.urlopen(req2)
        assert resp2.headers.get("Set-Cookie", "") == ""
    finally:
        _stop_server(srv)


def test_http_tictactoe_post_move():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        gid = str(uuid.uuid4())
        data = urllib.parse.urlencode({"cell": "4"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/move",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"game_id={gid}",
            },
        )
        resp = urllib.request.urlopen(req)  # follows 303 → GET /tictactoe
        assert resp.status == 200
        html = resp.read().decode()
        assert "Tic-Tac-Toe" in html
    finally:
        _stop_server(srv)


def test_http_tictactoe_post_new_game():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        gid = str(uuid.uuid4())
        # Make a move first
        data = urllib.parse.urlencode({"cell": "0"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/move",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"game_id={gid}",
            },
        )
        urllib.request.urlopen(req)
        # Now reset
        reset_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/new",
            data=b"",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"game_id={gid}",
            },
        )
        resp = urllib.request.urlopen(reset_req)  # follows 303
        assert resp.status == 200
        html = resp.read().decode()
        # After reset the board should show all empty cells (9 clickable cell buttons)
        assert html.count('class="cell empty"') == 9
    finally:
        _stop_server(srv)


def test_http_404():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/no-such-path")
            assert False, "expected HTTPError"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        _stop_server(srv)


def test_http_post_404():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/no-such-post",
                data=b"",
            )
            urllib.request.urlopen(req)
            assert False, "expected HTTPError"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        _stop_server(srv)


def test_http_tictactoe_move_no_cookie():
    """POST without a cookie → the 303 redirect must carry a Set-Cookie header."""
    srv = _start_server()
    try:
        port = srv.server_address[1]
        data = urllib.parse.urlencode({"cell": "0"}).encode()
        # Use a non-redirecting opener so we can inspect the raw 303 headers.
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                return None  # suppress redirect
        opener = urllib.request.build_opener(_NoRedirect)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/move",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            opener.open(req)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert "game_id=" in exc.headers.get("Set-Cookie", "")
        else:
            raise AssertionError("expected a 303 redirect")
    finally:
        _stop_server(srv)


def test_http_tictactoe_move_missing_cell():
    """POST /tictactoe/move with no cell param → KeyError → idx=-1 (no-op)."""
    srv = _start_server()
    try:
        port = srv.server_address[1]
        gid = str(uuid.uuid4())
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/move",
            data=b"no_cell=1",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"game_id={gid}",
            },
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
    finally:
        _stop_server(srv)


def test_http_tictactoe_move_invalid_cell():
    """POST /tictactoe/move with non-integer cell → ValueError → idx=-1 (no-op)."""
    srv = _start_server()
    try:
        port = srv.server_address[1]
        gid = str(uuid.uuid4())
        data = urllib.parse.urlencode({"cell": "notanumber"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/tictactoe/move",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"game_id={gid}",
            },
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
    finally:
        _stop_server(srv)

def test_http_bad_content_length():
    srv = _start_server()
    try:
        port = srv.server_address[1]
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        try:
            s.sendall(
                b"POST /tictactoe/move HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Type: application/x-www-form-urlencoded\r\n"
                b"Content-Length: notanumber\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            s.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
        finally:
            s.close()
        assert b"400" in response.split(b"\r\n")[0]
    finally:
        _stop_server(srv)


# ---------------------------------------------------------------------------
# run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
