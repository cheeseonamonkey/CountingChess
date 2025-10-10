
from datetime import datetime
import chess, numpy as np, pandas as pd, Sunfish

WIN = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}
METRICS = [
    'openness', 'development', 'mobility', 'sharpness', 'center_control',
    'king_safety', 'pawn_structure', 'space', 'piece_coordination'
]

def _parse_dt(d, t=""):
    if not d or d == "????.??.??":
        return None
    try:
        return datetime.fromisoformat(d.replace('.', '-') + (" " + t).strip())
    except:
        return None

def game_meta(g, user):
    r = g.headers.get("Result", "*")
    w = WIN.get(r, "unknown")
    white, black = g.headers.get("White", ""), g.headers.get("Black", "")
    color = "white" if user == white else "black" if user == black else None
    dt = _parse_dt(g.headers.get("UTCDate", g.headers.get("Date", "")), g.headers.get("UTCTime", ""))

    def safe_int(x): 
        try: return int(x)
        except: return 0

    white_elo, black_elo = safe_int(g.headers.get("WhiteElo", 0)), safe_int(g.headers.get("BlackElo", 0))
    perspective_elo = white_elo if color == "white" else black_elo
    opponent_elo = black_elo if color == "white" else white_elo

    return dict(
        winner=w,
        perspective_user=user,
        perspective_color=color,
        game_outcome=("win" if w == color else "draw" if w == "draw" else "loss"),
        opening=g.headers.get("Opening", ""),
        eco=g.headers.get("ECO", ""),
        time_control=g.headers.get("TimeControl", ""),
        white_elo=white_elo,
        black_elo=black_elo,
        perspective_elo=perspective_elo,
        opponent_elo=opponent_elo,
        date=g.headers.get("Date", ""),
        day_of_week=dt.strftime('%A') if dt else "",
        hour=dt.hour if dt else -1,
        resigned_or_abandoned=("resign" in g.headers.get("Termination", "").lower()
                               or "abandon" in g.headers.get("Termination", "").lower()
                               or r == "*")
    )

def _phase(move_num):
    return "opening" if move_num <= 10 else "middlegame" if move_num <= 40 else "endgame"

def process_moves(game, perspective_color, time_control):
    # Parse time control to get base time in seconds
    base_time = 0
    if time_control:
        try:
            base_time = int(time_control.split('+')[0]) if '+' in time_control else int(time_control)
        except:
            base_time = 0

    b, node = game.board(), game
    prev_clock = None
    seq = []

    for n, move in enumerate(game.mainline_moves(), 1):
        from_piece = b.piece_at(move.from_square)
        is_persp = (perspective_color == "white") == b.turn
        is_cap = b.is_capture(move)
        if is_persp:
            eval_before = Sunfish.evaluate_fen(b.fen(), result=None)
            if perspective_color == "black":
                eval_before = -eval_before
        b.push(move)
        node = node.next()
        if not is_persp:
            continue
        clk = node.clock() or None
        tspent_raw = int(prev_clock - clk) if prev_clock and clk else 0
        tspent = (tspent_raw / base_time) if base_time > 0 else 0
        prev_clock = clk
        score = Sunfish.evaluate_fen(b.fen(), result=None)
        if perspective_color == "black":
            score = -score
        cpl = max(0, eval_before - score)
        metrics = Sunfish.calculate_metrics(b.fen())
        if perspective_color == "black":
            metrics = {k: -v if isinstance(v, (int, float)) else v for k, v in metrics.items()}
        phase = _phase(n)
        material = sum([p.piece_type * (1 if p.color == b.turn else -1) for _, p in b.piece_map().items()]) if b.piece_map() else 0
        seq.append(dict(
            move_num=n,
            eval=score,
            centipawn_loss=cpl,
            time_spent=tspent,
            last_piece=chess.piece_name(from_piece.piece_type) if from_piece else "",
            is_premove=tspent_raw < 1,
            is_capture=is_cap,
            phase=phase,
            material=material,
            **{k: metrics.get(k, 0) for k in METRICS}
        ))
    return pd.DataFrame(seq)

def process_game(game, user):
    meta = game_meta(game, user)
    if not meta['perspective_color']:
        return None
    moves = process_moves(game, meta['perspective_color'], meta['time_control'])
    if moves.empty:
        return None
    moves['eval_delta'] = moves['eval'].diff().abs().fillna(0)
    meta.update(
        num_moves=len(moves),
        avg_time=moves['time_spent'].mean(),
        avg_acpl=moves['centipawn_loss'].mean(),
        longest_think=moves['time_spent'].max(),
        eval_volatility=moves['eval_delta'].std(),
        material_swing=(moves['material'].max() - moves['material'].min())
    )
    return {'meta': meta, 'moves': moves}

def process_games_list(games):
    rows = []
    for i, g in enumerate(games):
        for user in (g.headers.get("White", ""), g.headers.get("Black", "")):
            res = process_game(g, user)
            if not res:
                continue
            m, mv = res['meta'], res['moves']
            mv['game_id'] = i
            for k in ['perspective_user', 'game_outcome', 'opening', 'eco',
                      'perspective_elo', 'opponent_elo', 'time_control',
                      'day_of_week', 'hour', 'resigned_or_abandoned']:
                mv[k] = m[k]
            rows.append(mv)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
