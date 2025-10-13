import chess, chess.engine
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from DiskMemCache import DiskMemCache
from ProgressLogging import progress

_pcache = DiskMemCache()


def evaluate_single_game(pgn, stockfish_path, depth_limit, users=None, 
                         track_time=False, game_num=None):
    try:
        game = chess.pgn.read_game(StringIO(pgn)) if isinstance(pgn, str) else pgn
        if not game: return None

        white, black = game.headers.get("White", "").lower(), game.headers.get("Black", "").lower()
        user_list = [u.lower() for u in (users or [])]
        color = chess.WHITE if white in user_list else chess.BLACK if black in user_list else None

        result = game.headers.get("Result", "*")
        won = None
        if result in ["1-0", "0-1"]:
            won = (result == "1-0") == (color == chess.WHITE) if color else (result == "1-0")

        hour = None
        if track_time and (d := game.headers.get("UTCDate")) and (t := game.headers.get("UTCTime")):
            try:
                hour = datetime.strptime(f"{d} {t}", "%Y.%m.%d %H:%M:%S").replace(
                    tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/Denver")).hour
            except:
                pass

        board, evals, piece_types, pawn_counts, best_moves = game.board(), [], [], [], []
        castle_turn, castle_side = None, None

        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            for move_index, move in enumerate(game.mainline_moves(), 1):
                fen = board.fen()
                info = _pcache.get(fen, depth_limit.depth)
                if not info:
                    info = engine.analyse(board, depth_limit)
                    _pcache.put(fen, depth_limit.depth, info)

                evals.append(max(-800, min(800, info["score"].white().score(mate_score=1e4) or 0)))
                piece_types.append(board.piece_type_at(move.from_square))
                pawn_counts.append(sum(len(board.pieces(chess.PAWN, s)) for s in [chess.WHITE, chess.BLACK]))

                if not castle_turn and board.is_castling(move) and board.turn == (color or board.turn):
                    castle_turn, castle_side = move_index, "K" if move.to_square > move.from_square else "Q"

                if (not color or move_index % 2 != color) and (pv := info.get("pv", [None])[0]):
                    best_moves.append(move == pv)

                board.push(move)

        is_resignation = result in ["1-0", "0-1"] and not board.is_checkmate()

        return (evals, piece_types, pawn_counts, color,
                int(game.headers.get("WhiteElo", 0) or game.headers.get("BlackElo", 0)),
                castle_turn, castle_side, won, is_resignation, best_moves, hour, game_num)
    except:
        return None


def assign_game_numbers(pgns):
    grouped = defaultdict(list)
    for idx, pgn in enumerate(pgns):
        try:
            g = chess.pgn.read_game(StringIO(pgn)) if isinstance(pgn, str) else pgn
            if not g or not (d := g.headers.get("UTCDate")) or not (t := g.headers.get("UTCTime")):
                continue
            local = datetime.strptime(f"{d} {t}", "%Y.%m.%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/Denver"))
            grouped[local.date()].append((local, idx))
        except:
            continue
    return {i: n for day, games in grouped.items() for n, (_, i) in enumerate(sorted(games), 1)}


def analyze_games(pgns, stockfish_path, depth, users=None, track_time=False):
    total, game_nums = len(pgns), assign_game_numbers(pgns) if users else {}
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(evaluate_single_game, pgn, stockfish_path,
                          chess.engine.Limit(depth=depth), users, track_time, game_nums.get(i)): i
            for i, pgn in enumerate(pgns)
        }
        results = [None] * total
        for completed, future in enumerate(as_completed(futures), 1):
            results[futures[future]] = future.result()
            progress(completed, total)
    return results


def load_cache():
    _pcache.load()


def save_cache():
    _pcache.save()