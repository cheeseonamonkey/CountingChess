from datetime import datetime
import chess
import pandas as pd
from functools import lru_cache
from multiprocessing import Pool
from Sunfish import evaluate_fen

WIN = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}


# Cache FEN evaluations
@lru_cache(maxsize=20000)
def cached_eval(fen, depth):
    return evaluate_fen(fen, depth=depth)[0]


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

    def safe_int(x):
        try:
            return int(x)
        except:
            return 0

    white_elo = safe_int(g.headers.get("WhiteElo", 0))
    black_elo = safe_int(g.headers.get("BlackElo", 0))
    perspective_elo = white_elo if color == "white" else black_elo
    opponent_elo = black_elo if color == "white" else white_elo

    return dict(winner=w,
                perspective_user=user,
                perspective_color=color,
                game_outcome=("win" if w == color else
                              "draw" if w == "draw" else "loss"),
                white_elo=white_elo,
                black_elo=black_elo,
                perspective_elo=perspective_elo,
                opponent_elo=opponent_elo,
                date=g.headers.get("Date", ""))


def process_moves(game, perspective_color, depth=(1, 2)):
    b = game.board()
    seq = []
    for n, move in enumerate(game.mainline_moves(), 1):
        is_persp = (perspective_color == "white") == b.turn
        if is_persp:
            eval_before = cached_eval(b.fen(), depth=depth[0])
            if perspective_color == "black":
                eval_before = -eval_before
        b.push(move)
        if not is_persp:
            continue
        score = cached_eval(b.fen(), depth=depth[1])
        if perspective_color == "black":
            score = -score
        cpl = max(0, eval_before - score)
        seq.append(dict(move_num=n, eval=score, centipawn_loss=cpl))
    return pd.DataFrame(seq)


def process_game(game, user, depth=(1, 2)):
    meta = game_meta(game, user)
    if not meta['perspective_color']:
        return None
    moves = process_moves(game, meta['perspective_color'], depth)
    if moves.empty:
        return None
    meta.update(num_moves=len(moves), avg_acpl=moves['centipawn_loss'].mean())
    return {'meta': meta, 'moves': moves}


def _process_game_wrapper(args):
    return process_game(*args)


def process_games_list(games,
                       depth=(1, 2),
                       parallel=True,
                       show_progress=False):
    # Build task list
    tasks = [(g, user, depth)
             for g in games for user in (g.headers.get("White", ""),
                                         g.headers.get("Black", ""))]

    # Process with or without parallel
    if parallel:
        with Pool() as pool:
            if show_progress:
                from tqdm import tqdm
                results = list(
                    tqdm(pool.imap(_process_game_wrapper, tasks),
                         total=len(tasks),
                         desc="Processing games"))
            else:
                results = pool.map(_process_game_wrapper, tasks)
    else:
        if show_progress:
            from tqdm import tqdm
            results = [
                process_game(g, u, depth)
                for g, u, depth in tqdm(tasks, desc="Processing games")
            ]
        else:
            results = [process_game(g, u, depth) for g, u, depth in tasks]

    # Combine results
    rows = []
    for i, res in enumerate(results):
        if not res:
            continue
        m, mv = res['meta'], res['moves']
        mv['game_id'] = i // 2
        for k in [
                'perspective_user', 'game_outcome', 'perspective_elo',
                'opponent_elo'
        ]:
            mv[k] = m[k]
        rows.append(mv)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
