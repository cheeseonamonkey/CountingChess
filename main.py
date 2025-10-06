import pandas as pd
import chess
import Fetchers
import Sunfish

# Fetch games once
myGames = Fetchers.fetch_all_users_games(
    [
        'ffffattyyyy',
        # 'fffattyy', 'ffatty120', 'ffatty140', 'ffatty190', 'ffatty', 'ffattyy'
    ],
    None,
    True)
randomGames = Fetchers.fetch_random_games(50, 120, True)

WINNER_MAP = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}
METRIC_KEYS = [
    'openness', 'development', 'mobility', 'sharpness', 'center_control',
    'king_safety', 'pawn_structure', 'space'
]


def process_game(game, perspective_user=None, verbose=True):
    """Process a single game from a user's perspective. Returns DataFrame."""
    result = game.headers.get("Result", "*")
    winner = WINNER_MAP.get(result, "unknown")
    white_player = game.headers.get("White", "")
    black_player = game.headers.get("Black", "")
    # Determine perspective color
    if perspective_user:
        is_white = white_player == perspective_user
        perspective_color = "white" if is_white else "black"
    else:
        perspective_color = None
    if verbose:
        print(f"\nResult: {result} (Winner: {winner})")
        if perspective_user:
            print(f"Perspective: {perspective_user} ({perspective_color})")
    vectors = {
        k: []
        for k in [
            'eval', *METRIC_KEYS, 'time_spent', 'centipawn_loss', 'winner',
            'perspective_user', 'perspective_color'
        ]
    }
    board = game.board()
    node = game
    prev_clock = prev_eval = None
    for i, move in enumerate(game.mainline_moves(), start=1):
        if verbose:
            print(f"Move {i}: {board.san(move)}")
        was_white_turn = board.turn
        is_perspective_turn = (perspective_color == "white" and was_white_turn) or \
                             (perspective_color == "black" and not was_white_turn)

        # Only record moves from the perspective player
        if not is_perspective_turn:
            board.push(move)
            node = node.next()
            continue

        board.push(move)
        node = node.next()
        # Time spent calculation
        clock = node.clock()
        time_spent = int(prev_clock - clock) if clock and prev_clock else 0
        prev_clock = clock
        # Evaluation and metrics
        fen = board.fen()
        score = Sunfish.evaluate_fen(fen)
        metrics = Sunfish.calculate_metrics(fen)

        # Flip metrics for black's perspective
        if perspective_color == "black":
            score = -score
            for key in METRIC_KEYS:
                metrics[key] = -metrics[key]

        # Centipawn loss (now from perspective)
        cp_loss = 0
        if prev_eval is not None:
            cp_loss = max(0, prev_eval - score)
        prev_eval = score
        # Append values
        vectors['eval'].append(score)
        vectors['time_spent'].append(time_spent)
        vectors['centipawn_loss'].append(cp_loss)
        vectors['winner'].append(winner)
        vectors['perspective_user'].append(perspective_user)
        vectors['perspective_color'].append(perspective_color)
        for key in METRIC_KEYS:
            vectors[key].append(metrics[key])
        if verbose:
            print(f"  Eval: {score}, Time: {time_spent}s, CP Loss: {cp_loss}")
    return pd.DataFrame(vectors)


# Process my games (one perspective per game)
MY_USERNAMES = {
    'ffffattyyyy', 'fffattyy', 'ffatty120', 'ffatty140', 'ffatty190', 'ffatty',
    'ffattyy'
}
games_vectors = []
for idx, game in enumerate(myGames, start=1):
    print(f"\n===== My Game {idx} =====")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    user = white if white in MY_USERNAMES else black
    games_vectors.append(
        process_game(game, perspective_user=user, verbose=True))

# Process random games (both perspectives)
for idx, game in enumerate(randomGames, start=1):
    print(f"\n===== Random Game {idx} =====")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    games_vectors.append(
        process_game(game, perspective_user=white, verbose=True))
    games_vectors.append(
        process_game(game, perspective_user=black, verbose=True))

# Combine all games
all_games_df = pd.concat(games_vectors,
                         keys=range(len(games_vectors)),
                         names=['game_id', 'move_id'])

print(all_games_df.loc[9:])
