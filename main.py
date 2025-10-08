import Fetchers
import GameProcessor
import numpy as np
from tabulate import tabulate
from collections import Counter


def calc_stats(df):
    # --- Basic game-level stats ---
    game_acpl = df.groupby(['game_id', 'perspective_user'])['acpl'].first()
    game_data = df.groupby('game_id').first()
    total_games = len(game_data)

    win_rate = (game_data['game_outcome']
                == 'win').sum() / total_games if total_games else 0
    resigned_rate = game_data['resigned_or_abandoned'].sum(
    ) / total_games if total_games else 0

    # --- Piece-level stats ---
    piece_stats = df.groupby('last_piece_type_moved')['centipawn_loss'].agg(
        ['mean', 'count'])

    # --- Correlations ---
    valid = df[df['time_spent'] > 0].dropna(
        subset=['time_spent', 'centipawn_loss'])
    time_cpl_corr = valid['time_spent'].corr(
        valid['centipawn_loss']) if len(valid) > 1 else 0

    valid_sharp = df.dropna(subset=['sharpness', 'centipawn_loss'])
    sharp_cpl_corr = valid_sharp['sharpness'].corr(
        valid_sharp['centipawn_loss']) if len(valid_sharp) > 1 else 0

    # --- Castle ACPL stats ---
    castle_cpl = {}
    for c in ['O-O', 'O-O-O']:
        cg = df[df['castle_type'] == c]
        if not cg.empty:
            pc = cg[cg['move_num'] > cg['castle_turn']]
            castle_cpl[c] = pc['centipawn_loss'].mean() if not pc.empty else 0

    # --- Castle & Queen development timing vs win ---
    castle_timing_wr, queen_timing_wr = {}, {}
    for threshold in [5, 10, 15]:
        ce = game_data[(game_data['castle_turn'] > 0)
                       & (game_data['castle_turn'] <= threshold)]
        cl = game_data[game_data['castle_turn'] > threshold]
        castle_timing_wr[f'<={threshold}'] = (
            ce['game_outcome'] == 'win').sum() / len(ce) if len(ce) else 0
        castle_timing_wr[f'>{threshold}'] = (
            cl['game_outcome'] == 'win').sum() / len(cl) if len(cl) else 0

        qe = game_data[(game_data['queen_dev_turn'] > 0)
                       & (game_data['queen_dev_turn'] <= threshold)]
        ql = game_data[game_data['queen_dev_turn'] > threshold]
        queen_timing_wr[f'<={threshold}'] = (
            qe['game_outcome'] == 'win').sum() / len(qe) if len(qe) else 0
        queen_timing_wr[f'>{threshold}'] = (
            ql['game_outcome'] == 'win').sum() / len(ql) if len(ql) else 0

    # --- Premove stats ---
    premove = df[df['is_premove']]
    non_premove = df[~df['is_premove']]

    premove_acpl = premove['centipawn_loss'].mean() if len(premove) else 0
    non_premove_acpl = non_premove['centipawn_loss'].mean() if len(
        non_premove) else 0
    premove_ratio = df['is_premove'].mean() if len(df) else 0

    premove_cap = premove[premove['is_capture']]
    premove_noncap = premove[~premove['is_capture']]
    non_premove_cap = non_premove[non_premove['is_capture']]
    non_premove_noncap = non_premove[~non_premove['is_capture']]

    # --- Metrics vs win correlations ---
    metric_cols = [
        'openness', 'development', 'mobility', 'sharpness', 'center_control',
        'king_safety', 'pawn_structure', 'space', 'time_spent', 'acpl'
    ]
    metric_vs_win = {}
    for m in metric_cols:
        v = df.dropna(subset=[m, 'game_outcome'])
        if len(v) > 1:
            game_means = v.groupby('game_id')[m].mean()
            game_wins = v.groupby('game_id')['game_outcome'].first().apply(
                lambda x: int(x == 'win'))
            metric_vs_win[m] = game_means.corr(game_wins)
        else:
            metric_vs_win[m] = 0

    # --- New metrics ---
    avg_time_per_move = df['time_spent'].mean() if len(df) else 0
    capture_ratio = df['is_capture'].mean() if len(df) else 0
    moves_per_piece = dict(Counter(
        df['last_piece_type_moved'])) if len(df) else {}
    moves_per_piece_ratio = {
        k: v / len(df)
        for k, v in moves_per_piece.items()
    } if len(df) else {}
    moves_per_game = df.groupby('game_id')['move_num'].count().mean() if len(
        df) else 0

    return {
        'num_games':
        total_games,
        'avg_acpl':
        game_acpl.mean(),
        'median_acpl':
        game_acpl.median(),
        'piece_avg':
        piece_stats['mean'].to_dict(),
        'piece_counts':
        piece_stats['count'].to_dict(),
        'time_cpl_corr':
        time_cpl_corr,
        'sharp_cpl_corr':
        sharp_cpl_corr,
        'castle_cpl':
        castle_cpl,
        'win_rate':
        win_rate,
        'resigned_rate':
        resigned_rate,
        'castle_timing_wr':
        castle_timing_wr,
        'queen_timing_wr':
        queen_timing_wr,
        'metric_vs_win':
        metric_vs_win,
        'premove_acpl':
        premove_acpl,
        'non_premove_acpl':
        non_premove_acpl,
        'premove_ratio':
        premove_ratio,
        'premove_cap_acpl':
        premove_cap['centipawn_loss'].mean() if len(premove_cap) else 0,
        'premove_noncap_acpl':
        premove_noncap['centipawn_loss'].mean() if len(premove_noncap) else 0,
        'non_premove_cap_acpl':
        non_premove_cap['centipawn_loss'].mean()
        if len(non_premove_cap) else 0,
        'non_premove_noncap_acpl':
        non_premove_noncap['centipawn_loss'].mean()
        if len(non_premove_noncap) else 0,
        'premove_cap_ratio':
        len(premove_cap) / len(df) if len(df) else 0,
        'premove_noncap_ratio':
        len(premove_noncap) / len(df) if len(df) else 0,
        # --- new metrics ---
        'avg_time_per_move':
        avg_time_per_move,
        'capture_ratio':
        capture_ratio,
        'moves_per_piece_ratio':
        moves_per_piece_ratio,
        'moves_per_game':
        moves_per_game,
    }


def display_full_comparison(mine, rand):

    def diff(x, y):
        return x - y

    print("\n--- OVERALL ---")
    overall = [
        [
            'Games', mine['num_games'], rand['num_games'],
            diff(mine['num_games'], rand['num_games'])
        ],
        [
            'Avg ACPL', f"{mine['avg_acpl']:.1f}", f"{rand['avg_acpl']:.1f}",
            f"{diff(mine['avg_acpl'], rand['avg_acpl']):+.1f}"
        ],
        [
            'Median ACPL', f"{mine['median_acpl']:.1f}",
            f"{rand['median_acpl']:.1f}",
            f"{diff(mine['median_acpl'], rand['median_acpl']):+.1f}"
        ],
        [
            'Win Rate', f"{mine['win_rate']:.1%}", f"{rand['win_rate']:.1%}",
            f"{diff(mine['win_rate'], rand['win_rate']):+.1%}"
        ],
        [
            'Resign/Abandon', f"{mine['resigned_rate']:.1%}",
            f"{rand['resigned_rate']:.1%}",
            f"{diff(mine['resigned_rate'], rand['resigned_rate']):+.1%}"
        ],
        [
            'Avg Time/Move', f"{mine['avg_time_per_move']:.2f}s",
            f"{rand['avg_time_per_move']:.2f}s",
            f"{diff(mine['avg_time_per_move'], rand['avg_time_per_move']):+.2f}s"
        ],
        [
            'Capture Ratio', f"{mine['capture_ratio']:.1%}",
            f"{rand['capture_ratio']:.1%}",
            f"{diff(mine['capture_ratio'], rand['capture_ratio']):+.1%}"
        ],
        [
            'Moves/Game', f"{mine['moves_per_game']:.1f}",
            f"{rand['moves_per_game']:.1f}",
            f"{diff(mine['moves_per_game'], rand['moves_per_game']):+.1f}"
        ]
    ]  # <-- remove the trailing comma
    print(
        tabulate(overall,
                 headers=['Metric', 'You', 'Random', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Piece Stats ---")
    pieces = sorted(
        set(mine['piece_avg'].keys()) | set(rand['piece_avg'].keys()))
    piece_table = [[
        p,
        f"{mine['piece_avg'].get(p, 0):.2f} ({mine['piece_counts'].get(p, 0) / 1000:.1}k)",
        f"{rand['piece_avg'].get(p, 0):.2f} ({rand['piece_counts'].get(p, 0)/1000:.1}k)",
        f"{diff(mine['piece_avg'].get(p, 0), rand['piece_avg'].get(p, 0)):+.2f}"
    ] for p in pieces]
    print(
        tabulate(piece_table,
                 headers=['Piece', 'You', 'Random', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Moves per Piece Ratio ---")
    all_pieces = sorted(
        set(mine['moves_per_piece_ratio'].keys())
        | set(rand['moves_per_piece_ratio'].keys()))
    moves_ratio_table = [[
        p, f"{mine['moves_per_piece_ratio'].get(p, 0):.2%}",
        f"{rand['moves_per_piece_ratio'].get(p, 0):.2%}",
        f"{diff(mine['moves_per_piece_ratio'].get(p, 0), rand['moves_per_piece_ratio'].get(p, 0)):+.2%}"
    ] for p in all_pieces]
    print(
        tabulate(moves_ratio_table,
                 headers=['Piece', 'You', 'Random', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Castle Stats ---")
    castles = sorted(
        set(mine['castle_cpl'].keys()) | set(rand['castle_cpl'].keys()))
    castle_table = [[
        c, f"{mine['castle_cpl'].get(c, 0):.2f}",
        f"{rand['castle_cpl'].get(c, 0):.2f}",
        f"{diff(mine['castle_cpl'].get(c, 0), rand['castle_cpl'].get(c, 0)):+.2f}"
    ] for c in castles]
    print(
        tabulate(castle_table,
                 headers=['Castle', 'You ACPL', 'Random ACPL', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Timing vs Win Rate ---")
    timing = []
    for t in sorted(
            set(mine['castle_timing_wr'].keys())
            | set(rand['castle_timing_wr'].keys())):
        timing.append([
            f"Castle {t}", f"{mine['castle_timing_wr'].get(t, 0):.1%}",
            f"{rand['castle_timing_wr'].get(t, 0):.1%}",
            f"{diff(mine['castle_timing_wr'].get(t, 0), rand['castle_timing_wr'].get(t, 0)):+.1%}"
        ])
    for t in sorted(
            set(mine['queen_timing_wr'].keys())
            | set(rand['queen_timing_wr'].keys())):
        timing.append([
            f"Queen {t}", f"{mine['queen_timing_wr'].get(t, 0):.1%}",
            f"{rand['queen_timing_wr'].get(t, 0):.1%}",
            f"{diff(mine['queen_timing_wr'].get(t, 0), rand['queen_timing_wr'].get(t, 0)):+.1%}"
        ])
    print(
        tabulate(timing,
                 headers=['Event', 'You WR', 'Random WR', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Metric vs Win Correlations ---")
    metrics = sorted(
        set(mine['metric_vs_win'].keys()) | set(rand['metric_vs_win'].keys()))
    metric_table = [[
        m, f"{mine['metric_vs_win'].get(m, 0):.2f}",
        f"{rand['metric_vs_win'].get(m, 0):.2f}",
        f"{diff(mine['metric_vs_win'].get(m, 0), rand['metric_vs_win'].get(m, 0)):+.2f}"
    ] for m in metrics]
    print(
        tabulate(metric_table,
                 headers=['Metric', 'You vs Win', 'Random vs Win', 'Diff'],
                 tablefmt='simple'))

    print("\n--- Other Stats ---")
    print(
        f"Time vs CPL Corr: You {mine['time_cpl_corr']:.2f}, Random {rand['time_cpl_corr']:.2f}, Diff {diff(mine['time_cpl_corr'], rand['time_cpl_corr']):+.2f}"
    )
    print(
        f"Sharpness vs CPL Corr: You {mine['sharp_cpl_corr']:.2f}, Random {rand['sharp_cpl_corr']:.2f}, Diff {diff(mine['sharp_cpl_corr'], rand['sharp_cpl_corr']):+.2f}"
    )

    return mine, rand


# --- Main ---
print("Processing your games...")
my_df = GameProcessor.process_games_list(
    Fetchers.fetch_all_users_games(["ffatty190", "ffatty120", "ffffattyyyy"], None, verbose=False))

print("Processing random games...")
rand_df = GameProcessor.process_games_list(
    Fetchers.fetch_random_games(13999, m=64, o=16, verbose=False))

print("Calculating stats...")
my_stats = calc_stats(my_df)
rand_stats = calc_stats(rand_df)

# Display all comparisons in tables
my_stats, rand_stats = display_full_comparison(my_stats, rand_stats)

# --- Optional: Other stats in table format ---
other_table = [
    [
        'Time vs CPL Corr', 
        f"{my_stats['time_cpl_corr']:.3f}",
        f"{rand_stats['time_cpl_corr']:.3f}",
        f"{my_stats['time_cpl_corr'] - rand_stats['time_cpl_corr']:+.3f}"
    ],
    [
        'Sharpness vs CPL Corr', 
        f"{my_stats['sharp_cpl_corr']:.3f}",
        f"{rand_stats['sharp_cpl_corr']:.3f}",
        f"{my_stats['sharp_cpl_corr'] - rand_stats['sharp_cpl_corr']:+.3f}"
    ],
    [
        'Premove Ratio', 
        f"{my_stats['premove_ratio']:.2%}",
        f"{rand_stats['premove_ratio']:.2%}",
        f"{my_stats['premove_ratio'] - rand_stats['premove_ratio']:+.2%}"
    ],
    [
        'Premove Cap Ratio', 
        f"{my_stats['premove_cap_ratio']:.2%}",
        f"{rand_stats['premove_cap_ratio']:.2%}",
        f"{my_stats['premove_cap_ratio'] - rand_stats['premove_cap_ratio']:+.2%}"
    ],
    [
        'Premove NonCap Ratio', 
        f"{my_stats['premove_noncap_ratio']:.2%}",
        f"{rand_stats['premove_noncap_ratio']:.2%}",
        f"{my_stats['premove_noncap_ratio'] - rand_stats['premove_noncap_ratio']:+.2%}"
    ],
    [
        'Premove ACPL', 
        f"{my_stats['premove_acpl']:.1f}",
        f"{rand_stats['premove_acpl']:.1f}",
        f"{my_stats['premove_acpl'] - rand_stats['premove_acpl']:+.1f}"
    ],
    [
        'Non-Premove ACPL', 
        f"{my_stats['non_premove_acpl']:.1f}",
        f"{rand_stats['non_premove_acpl']:.1f}",
        f"{my_stats['non_premove_acpl'] - rand_stats['non_premove_acpl']:+.1f}"
    ],
]
print("\n--- Other Metrics ---")
print(
    tabulate(other_table,
             headers=['Metric', 'You', 'Random', 'Diff'],
             tablefmt='simple'))

print("\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nn\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")