"""Unit tests for tic-tac-toe logic in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
import collections
from app import (
    check_winner,
    is_draw,
    make_move,
    _new_game,
    _parse_game_id,
)


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
    # even if full, a winner means it's not a draw (check_winner returns first)
    b = ["X","X","X","O","O"," ","O"," "," "]
    assert is_draw(b) is False


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
