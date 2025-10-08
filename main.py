import Fetchers
from GameProcessor import process_game
import pandas as pd
from tabulate import tabulate


def process_games_list(games):
    rows = []
    for idx, game in enumerate(games):
        for user in [
                game.headers.get("White", ""),
                game.headers.get("Black", "")
        ]:
            result = process_game(game, perspective_user=user, verbose=True)
            meta, moves = result['game'], result['moves']
            n = len(moves['turn_num'])

            # Calculate ACPL with 3-turn rolling average
            cpl_vals = [
                sum([
                    moves['centipawn_loss'][i + j]
                    for j in range(3) if i + j < n
                ]) / min(3, n - i) for i in range(n)
            ]
            meta['acpl'] = sum(cpl_vals) / n if n else 0

            # Create rows for each turn
            rows.extend([{
                'game_id': idx,
                **{
                    k: v[i]
                    for k, v in moves.items()
                },
                **meta
            } for i in range(n)])

    return pd.DataFrame(rows)


def calc_stats(df):
    game_acpl = df.groupby(['game_id', 'perspective_user'])['acpl'].first()
    game_data = df.groupby('game_id').first()

    piece_stats = df.groupby('last_piece_type_moved')['centipawn_loss'].agg(
        ['mean', 'count'])

    valid = df[df['time_spent'] > 0].dropna(
        subset=['time_spent', 'centipawn_loss'])
    time_cpl_corr = valid[['time_spent', 'centipawn_loss'
                           ]].corr().iloc[0, 1] if len(valid) > 1 else 0

    castle_cpl = {
        c: (pc :=
            cg[cg['turn_num'] > cg['castle_turn']])['centipawn_loss'].mean()
        if not (pc := cg[cg['turn_num'] > cg['castle_turn']]).empty else 0
        for c in ['O-O', 'O-O-O']
        if not (cg := df[df['castle_type'] == c]).empty
    }

    valid_sharp = df.dropna(subset=['sharpness', 'centipawn_loss'])
    sharp_cpl_corr = valid_sharp[[
        'sharpness', 'centipawn_loss'
    ]].corr().iloc[0, 1] if len(valid_sharp) > 1 else 0

    # Win rate calculations
    total_games = len(game_data)
    win_rate = (game_data['game_outcome']
                == 'win').sum() / total_games if total_games > 0 else 0

    # Castle timing win rates
    castle_timing_wr = {}
    for threshold in [5, 10, 15]:
        castled_early = game_data[(game_data['castle_turn'] > 0)
                                  & (game_data['castle_turn'] <= threshold)]
        if len(castled_early) > 0:
            castle_timing_wr[f'<={threshold}'] = (
                castled_early['game_outcome']
                == 'win').sum() / len(castled_early)
        castled_late = game_data[game_data['castle_turn'] > threshold]
        if len(castled_late) > 0:
            castle_timing_wr[f'>{threshold}'] = (
                castled_late['game_outcome']
                == 'win').sum() / len(castled_late)

    # Queen development timing win rates
    queen_timing_wr = {}
    for threshold in [5, 10, 15]:
        queen_early = game_data[(game_data['queen_dev_turn'] > 0)
                                & (game_data['queen_dev_turn'] <= threshold)]
        if len(queen_early) > 0:
            queen_timing_wr[f'<={threshold}'] = (
                queen_early['game_outcome'] == 'win').sum() / len(queen_early)
        queen_late = game_data[game_data['queen_dev_turn'] > threshold]
        if len(queen_late) > 0:
            queen_timing_wr[f'>{threshold}'] = (
                queen_late['game_outcome'] == 'win').sum() / len(queen_late)

    return {
        'num_games': len(game_acpl),
        'avg_acpl': game_acpl.mean(),
        'median_acpl': game_acpl.median(),
        'piece_avg': piece_stats['mean'].to_dict(),
        'piece_counts': piece_stats['count'].to_dict(),
        'time_cpl_corr': time_cpl_corr,
        'castle_cpl': castle_cpl,
        'sharp_cpl_corr': sharp_cpl_corr,
        'win_rate': win_rate,
        'castle_timing_wr': castle_timing_wr,
        'queen_timing_wr': queen_timing_wr
    }


def display_comparison(mine, rand):
    print(
        "\nOVERALL\n",
        tabulate([['Games', mine['num_games'], rand['num_games'], ''],
                  [
                      'Avg ACPL', f"{mine['avg_acpl']:.1f}",
                      f"{rand['avg_acpl']:.1f}",
                      f"{mine['avg_acpl']-rand['avg_acpl']:+.1f}"
                  ],
                  [
                      'Median ACPL', f"{mine['median_acpl']:.1f}",
                      f"{rand['median_acpl']:.1f}",
                      f"{mine['median_acpl']-rand['median_acpl']:+.1f}"
                  ],
                  [
                      'Win Rate', f"{mine['win_rate']:.1%}",
                      f"{rand['win_rate']:.1%}",
                      f"{mine['win_rate']-rand['win_rate']:+.1%}"
                  ]],
                 headers=['Metric', 'You', 'Random', 'Diff'],
                 tablefmt='simple'))

    # CPL BY PIECE
    all_pieces = sorted(
        set(mine.get('piece_avg', {})) | set(rand.get('piece_avg', {})))
    print("\nCPL BY PIECE")
    if all_pieces:
        print(
            tabulate([[
                p, f"{mine['piece_avg'].get(p, 0):.1f}",
                f"{rand['piece_avg'].get(p, 0):.1f}",
                f"{mine['piece_avg'].get(p, 0) - rand['piece_avg'].get(p, 0):+.1f}",
                mine['piece_counts'].get(p, 0)
            ] for p in all_pieces],
                     headers=['Piece', 'You', 'Random', 'Diff', 'Count'],
                     tablefmt='simple'))
    else:
        print("No piece data available.")

    print(
        "\nTIME vs CPL CORRELATION\n",
        tabulate([['You', f"{mine.get('time_cpl_corr', 0):.3f}"],
                  ['Random', f"{rand.get('time_cpl_corr', 0):.3f}"]],
                 headers=['', 'Correlation'],
                 tablefmt='simple'))

    print("\nCPL AFTER CASTLING")
    all_castles = sorted(
        set(mine.get('castle_cpl', {})) | set(rand.get('castle_cpl', {})))
    if all_castles:
        print(
            tabulate([[
                c, f"{mine['castle_cpl'].get(c, 0):.1f}",
                f"{rand['castle_cpl'].get(c, 0):.1f}"
            ] for c in all_castles],
                     headers=['Castle', 'You', 'Random'],
                     tablefmt='simple'))
    else:
        print("No castle data available.")

    print(
        "\nSHARPNESS vs CPL CORRELATION\n",
        tabulate([['You', f"{mine.get('sharp_cpl_corr', 0):.3f}"],
                  ['Random', f"{rand.get('sharp_cpl_corr', 0):.3f}"]],
                 headers=['', 'Correlation'],
                 tablefmt='simple'))

    # Castle timing win rates
    all_castle_times = sorted(
        set(mine.get('castle_timing_wr', {}))
        | set(rand.get('castle_timing_wr', {})))
    print("\nWIN RATE BY CASTLE TIMING")
    if all_castle_times:
        print(
            tabulate([[
                t, f"{mine['castle_timing_wr'].get(t, 0):.1%}",
                f"{rand['castle_timing_wr'].get(t, 0):.1%}",
                f"{mine['castle_timing_wr'].get(t, 0) - rand['castle_timing_wr'].get(t, 0):+.1%}"
            ] for t in all_castle_times],
                     headers=['Turn', 'You', 'Random', 'Diff'],
                     tablefmt='simple'))
    else:
        print("No castle timing data available.")

    # Queen development timing win rates
    all_queen_times = sorted(
        set(mine.get('queen_timing_wr', {}))
        | set(rand.get('queen_timing_wr', {})))
    print("\nWIN RATE BY QUEEN DEV TIMING")
    if all_queen_times:
        print(
            tabulate([[
                t, f"{mine['queen_timing_wr'].get(t, 0):.1%}",
                f"{rand['queen_timing_wr'].get(t, 0):.1%}",
                f"{mine['queen_timing_wr'].get(t, 0) - rand['queen_timing_wr'].get(t, 0):+.1%}"
            ] for t in all_queen_times],
                     headers=['Turn', 'You', 'Random', 'Diff'],
                     tablefmt='simple'))
    else:
        print("No queen timing data available.")

    return mine, rand


print("Processing your games...")
my_df = process_games_list(
    Fetchers.fetch_all_users_games(["ffffattyyyy"], None, False))
print("Processing random games...")
rand_df = process_games_list(
    Fetchers.fetch_random_games(2050, m=555, verbose=False))
print("Calculating stats...")
my_stats, rand_stats = display_comparison(calc_stats(my_df),
                                          calc_stats(rand_df))
