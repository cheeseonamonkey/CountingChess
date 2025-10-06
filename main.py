import Fetchers
import chess.pgn
import Sunfish
import Plotting
import pandas as pd

randomGames = Fetchers.fetch_random_games(15, 60, True)
games_vectors = []

for game_index, game in enumerate(randomGames):
    print(f"\n===== Game {game_index + 1} =====\n")
    vectors = {
        'eval': [],
        'openness': [],
        'development': [],
        'mobility': [],
        'sharpness': [],
        'center_control': [],
        'king_safety': [],
        'pawn_structure': [],
        'space': []
    }

    board = game.board()
    for i, move in enumerate(game.mainline_moves(), start=1):
        print(f"Move {i}: {board.san(move)}")
        board.push(move)
        fen = board.fen()

        score = Sunfish.evaluate_fen(fen)
        metrics = Sunfish.calculate_metrics(fen)

        vectors['eval'].append(score)
        for key in [
                'openness', 'development', 'mobility', 'sharpness',
                'center_control', 'king_safety', 'pawn_structure', 'space'
        ]:
            vectors[key].append(metrics[key])

        print(f"Sunfish evaluation: {score}")
        print(f'Metrics: {metrics}')

    df = pd.DataFrame(vectors)
    games_vectors.append(df)


