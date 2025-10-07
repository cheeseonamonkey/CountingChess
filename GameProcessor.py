from datetime import datetime
import chess
import Sunfish

WINNER_MAP = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}
METRIC_KEYS = ['openness', 'development', 'mobility', 'sharpness', 'center_control',
               'king_safety', 'pawn_structure', 'space']

def parse_datetime(utc_date, utc_time=""):
    """Parse game datetime from UTC date/time strings."""
    if not utc_date or utc_date == "????.??.??":
        return None
    try:
        return datetime.fromisoformat(f"{utc_date.replace('.', '-')} {utc_time}".strip())
    except:
        return None

def process_game(game, perspective_user=None, verbose=True):
    """Process a single game from a user's perspective. Returns dict with game and move data."""
    result = game.headers.get("Result", "*")
    winner = WINNER_MAP.get(result, "unknown")
    white = game.headers.get("White", "")

    perspective_color = "white" if perspective_user == white else "black" if perspective_user else None
    outcome = "win" if winner == perspective_color else "draw" if winner == "draw" else "loss"

    dt = parse_datetime(game.headers.get("UTCDate", game.headers.get("Date", "")),
                       game.headers.get("UTCTime", ""))

    game_meta = {
        'winner': winner, 'perspective_user': perspective_user,
        'perspective_color': perspective_color, 'game_outcome': outcome,
        'opening': game.headers.get("Opening", ""), 'eco': game.headers.get("ECO", ""),
        'time_control': game.headers.get("TimeControl", ""),
        'white_elo': game.headers.get("WhiteElo", ""), 'black_elo': game.headers.get("BlackElo", ""),
        'date': game.headers.get("Date", ""), 'day_of_week': dt.strftime('%A') if dt else "",
        'hour': dt.hour if dt else -1,
    }

    if verbose:
        print(f"\n{'='*60}\nGame: {white} vs {game.headers.get('Black', '')}")
        print(f"Result: {result} → {winner.upper()} wins\nOpening: {game_meta['opening']}")
        if dt:
            print(f"When: {dt.strftime('%Y-%m-%d %H:%M')} ({game_meta['day_of_week']})")
        if perspective_user:
            print(f"Perspective: {perspective_user} ({perspective_color}) → {outcome.upper()}")
        print(f"{'='*60}")

    moves = {k: [] for k in ['move_num', 'eval', *METRIC_KEYS, 'time_spent', 
                              'centipawn_loss', 'last_piece_type_moved']}
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

        score, metrics = Sunfish.evaluate_fen(board.fen()), Sunfish.calculate_metrics(board.fen())
        if perspective_color == "black":
            score, metrics = -score, {k: -v for k, v in metrics.items()}

        cp_loss = max(0, prev_eval - score) if prev_eval is not None else 0
        prev_eval = score

        if verbose:
            print(f"Move {move_num:2d}: {move_san:6s} | Eval: {score:+5d} | "
                  f"Time: {time_spent:2d}s | Loss: {cp_loss:3d}cp")

        moves['move_num'].append(move_num)
        moves['eval'].append(score)
        moves['time_spent'].append(time_spent)
        moves['centipawn_loss'].append(cp_loss)
        moves['last_piece_type_moved'].append(chess.piece_name(piece.piece_type) if piece else "")
        for key in METRIC_KEYS:
            moves[key].append(metrics[key])

    num_moves = len(moves['move_num'])
    if verbose and num_moves > 0:
        print(f"\nSummary: {num_moves} moves | Avg CP Loss: {sum(moves['centipawn_loss'])/num_moves:.1f} | "
              f"Total Time: {sum(moves['time_spent'])}s")

    game_meta.update({'num_moves': num_moves, 'queen_dev_turn': queen_dev_turn,
                      'castle_turn': castle_turn, 'castle_type': castle_type})

    return {'game': game_meta, 'moves': moves}