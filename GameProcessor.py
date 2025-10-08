from datetime import datetime
import chess
import Sunfish
import pandas as pd
import numpy as np

WINNER_MAP = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}
METRIC_KEYS = [
    'openness', 'development', 'mobility', 'sharpness', 'center_control',
    'king_safety', 'pawn_structure', 'space'
]


def parse_datetime(utc_date, utc_time=""):
    if not utc_date or utc_date == "????.??.??":
        return None
    try:
        return datetime.fromisoformat(
            f"{utc_date.replace('.', '-')} {utc_time}".strip())
    except:
        return None


def process_game(game, perspective_user=None, verbose=False):
    result = game.headers.get("Result", "*")
    winner = WINNER_MAP.get(result, "unknown")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    termination = game.headers.get("Termination", "").lower()

    perspective_color = "white" if perspective_user == white else "black" if perspective_user else None
    outcome = "win" if winner == perspective_color else "draw" if winner == "draw" else "loss"

    dt = parse_datetime(
        game.headers.get("UTCDate", game.headers.get("Date", "")),
        game.headers.get("UTCTime", ""))

    resigned_or_abandoned = ("resign" in termination
                             or "abandon" in termination or result == "*")

    game_meta = {
        'winner': winner,
        'perspective_user': perspective_user,
        'perspective_color': perspective_color,
        'game_outcome': outcome,
        'opening': game.headers.get("Opening", ""),
        'eco': game.headers.get("ECO", ""),
        'time_control': game.headers.get("TimeControl", ""),
        'white_elo': game.headers.get("WhiteElo", ""),
        'black_elo': game.headers.get("BlackElo", ""),
        'date': game.headers.get("Date", ""),
        'day_of_week': dt.strftime('%A') if dt else "",
        'hour': dt.hour if dt else -1,
        'resigned_or_abandoned': resigned_or_abandoned,
    }

    if verbose:
        print(f"\n{'='*60}\nGame: {white} vs {black}")
        print(
            f"Result: {result} → {winner.upper()} wins\nOpening: {game_meta['opening']}"
        )
        if dt:
            print(
                f"When: {dt.strftime('%Y-%m-%d %H:%M')} ({game_meta['day_of_week']})"
            )
        if perspective_user:
            print(
                f"Perspective: {perspective_user} ({perspective_color}) → {outcome.upper()}"
            )
        if resigned_or_abandoned:
            print("⚠️ Game ended by resignation or abandonment.")
        print(f"{'='*60}")

    moves = {
        k: []
        for k in [
            'move_num', 'eval', *METRIC_KEYS, 'time_spent', 'centipawn_loss',
            'last_piece_type_moved', 'is_premove'
        ]
    }
    board, node = game.board(), game
    prev_clock = prev_eval = queen_dev_turn = castle_turn = None
    castle_type = ""

    for move in game.mainline_moves():
        is_perspective = (perspective_color == "white") == board.turn
        move_san = board.san(move)
        piece = board.piece_at(move.from_square)

        if is_perspective:
            if piece and piece.piece_type == chess.QUEEN and not queen_dev_turn:
                queen_dev_turn = len(moves['move_num']) + 1
            if move_san in ('O-O', 'O-O-O') and not castle_turn:
                castle_turn, castle_type = len(moves['move_num']) + 1, move_san

        board.push(move)
        node = node.next()
        if not is_perspective:
            continue

        move_num = len(moves['move_num']) + 1
        clock = node.clock()
        time_spent = int(prev_clock - clock) if clock and prev_clock else 0
        prev_clock = clock

        is_premove = time_spent < 0.1  # Identify premoves

        score, metrics = Sunfish.evaluate_fen(
            board.fen(), result=None), Sunfish.calculate_metrics(board.fen())
        if perspective_color == "black":
            score, metrics = -score, {k: -v for k, v in metrics.items()}

        cp_loss = max(0, prev_eval - score) if prev_eval is not None else 0
        prev_eval = score

        if verbose:
            print(f"Move {move_num:2d}: {move_san:6s} | Eval: {score:+5d} | "
                  f"Time: {time_spent:2d}s | Loss: {cp_loss:3d}cp | "
                  f"Premove: {is_premove}")

        moves['move_num'].append(move_num)
        moves['eval'].append(score)
        moves['time_spent'].append(time_spent)
        moves['centipawn_loss'].append(cp_loss)
        moves['last_piece_type_moved'].append(
            chess.piece_name(piece.piece_type) if piece else "")
        moves['is_premove'].append(is_premove)
        for key in METRIC_KEYS:
            moves[key].append(metrics[key])

    num_moves = len(moves['move_num'])

    game_meta.update({
        'num_moves':
        num_moves,
        'queen_dev_turn':
        queen_dev_turn,
        'castle_turn':
        castle_turn,
        'castle_type':
        castle_type,
        'premove_count':
        sum(moves['is_premove']),
        'premove_ratio':
        sum(moves['is_premove']) / num_moves if num_moves else 0,
        'premove_acpl':
        np.mean([
            moves['centipawn_loss'][i] for i in range(num_moves)
            if moves['is_premove'][i]
        ]) if num_moves else 0,
        'non_premove_acpl':
        np.mean([
            moves['centipawn_loss'][i] for i in range(num_moves)
            if not moves['is_premove'][i]
        ]) if num_moves else 0,
    })

    return {'game': game_meta, 'moves': moves}


def process_games_list(games, verbose=False):
    rows = []
    for idx, game in enumerate(games):
        for user in [
                game.headers.get("White", ""),
                game.headers.get("Black", "")
        ]:
            res = process_game(game, perspective_user=user, verbose=verbose)
            meta, moves = res['game'], res['moves']
            n = len(moves['move_num'])
            cpl_vals = [
                sum([
                    moves['centipawn_loss'][i + j]
                    for j in range(3) if i + j < n
                ]) / min(3, n - i) for i in range(n)
            ]
            meta['acpl'] = sum(cpl_vals) / n if n else 0
            rows.extend([{
                'game_id': idx,
                **{
                    k: v[i]
                    for k, v in moves.items()
                },
                **meta
            } for i in range(n)])
    return pd.DataFrame(rows)
