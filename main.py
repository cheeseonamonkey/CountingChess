import Fetchers
import GameProcessor
import numpy as np
from tabulate import tabulate


def calc_stats(df):
    game_acpl = df.groupby(['game_id', 'perspective_user'])['acpl'].first()
    game_data = df.groupby('game_id').first()
    piece_stats = df.groupby('last_piece_type_moved')['centipawn_loss'].agg(
        ['mean', 'count'])

    valid = df[df['time_spent'] > 0].dropna(
        subset=['time_spent', 'centipawn_loss'])
    time_cpl_corr = valid[['time_spent', 'centipawn_loss'
                           ]].corr().iloc[0, 1] if len(valid) > 1 else 0

    castle_cpl = {}
    for c in ['O-O', 'O-O-O']:
        cg = df[df['castle_type'] == c]
        if not cg.empty:
            pc = cg[cg['move_num'] > cg['castle_turn']]
            castle_cpl[c] = pc['centipawn_loss'].mean() if not pc.empty else 0

    valid_sharp = df.dropna(subset=['sharpness', 'centipawn_loss'])
    sharp_cpl_corr = valid_sharp[[
        'sharpness', 'centipawn_loss'
    ]].corr().iloc[0, 1] if len(valid_sharp) > 1 else 0

    total_games = len(game_data)
    win_rate = (game_data['game_outcome']
                == 'win').sum() / total_games if total_games > 0 else 0
    resigned_rate = game_data['resigned_or_abandoned'].sum(
    ) / total_games if total_games > 0 else 0

    castle_timing_wr, queen_timing_wr = {}, {}
    for threshold in [5, 10, 15]:
        ce = game_data[(game_data['castle_turn'] > 0)
                       & (game_data['castle_turn'] <= threshold)]
        cl = game_data[game_data['castle_turn'] > threshold]
        if len(ce):
            castle_timing_wr[f'<={threshold}'] = (ce['game_outcome']
                                                  == 'win').sum() / len(ce)
        if len(cl):
            castle_timing_wr[f'>{threshold}'] = (cl['game_outcome']
                                                 == 'win').sum() / len(cl)

        qe = game_data[(game_data['queen_dev_turn'] > 0)
                       & (game_data['queen_dev_turn'] <= threshold)]
        ql = game_data[game_data['queen_dev_turn'] > threshold]
        if len(qe):
            queen_timing_wr[f'<={threshold}'] = (qe['game_outcome']
                                                 == 'win').sum() / len(qe)
        if len(ql):
            queen_timing_wr[f'>{threshold}'] = (ql['game_outcome']
                                                == 'win').sum() / len(ql)

    premove_acpl = df[
        df['is_premove']]['centipawn_loss'].mean() if 'is_premove' in df else 0
    non_premove_acpl = df[~df['is_premove']]['centipawn_loss'].mean(
    ) if 'is_premove' in df else 0
    premove_ratio = df['is_premove'].mean() if 'is_premove' in df else 0

    metric_cols = [
        'openness', 'development', 'mobility', 'sharpness', 'center_control',
        'king_safety', 'pawn_structure', 'space', 'time_spent', 'acpl'
    ]
    metric_vs_win = {}
    for m in metric_cols:
        v = df.dropna(subset=[m, 'game_outcome'])
        if len(v) > 1:
            metric_vs_win[m] = v.groupby('game_id')[m].mean().corr(
                v.groupby('game_id')['game_outcome'].first().apply(
                    lambda x: int(x == 'win')))
        else:
            metric_vs_win[m] = 0

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
        'resigned_rate': resigned_rate,
        'castle_timing_wr': castle_timing_wr,
        'queen_timing_wr': queen_timing_wr,
        'metric_vs_win': metric_vs_win,
        'premove_acpl': premove_acpl,
        'non_premove_acpl': non_premove_acpl,
        'premove_ratio': premove_ratio,
        'n_games': total_games
    }


def display_comparison(mine, rand):
    from math import sqrt

    def diff(x, y):
        return x - y

    def confidence_interval(p1, n1, p2, n2, z=1.96):
        se = sqrt((p1 * (1 - p1) / n1 if n1 > 0 else 0) +
                  (p2 * (1 - p2) / n2 if n2 > 0 else 0))
        return se * z

    print(
        "\nOVERALL\n",
        tabulate([
            ['Games', mine['num_games'], rand['num_games'], ''],
            [
                'Avg ACPL', f"{mine['avg_acpl']:.1f}",
                f"{rand['avg_acpl']:.1f}",
                f"{diff(mine['avg_acpl'], rand['avg_acpl']):+.1f}"
            ],
            [
                'Median ACPL', f"{mine['median_acpl']:.1f}",
                f"{rand['median_acpl']:.1f}",
                f"{diff(mine['median_acpl'], rand['median_acpl']):+.1f}"
            ],
            [
                'Win Rate', f"{mine['win_rate']:.1%}",
                f"{rand['win_rate']:.1%}",
                f"{diff(mine['win_rate'], rand['win_rate']):+.1%} "
                f"± {confidence_interval(mine['win_rate'], mine['n_games'], rand['win_rate'], rand['n_games']):.1%} (95% CI)"
            ],
            [
                'Resigned/Abandoned', f"{mine['resigned_rate']:.1%}",
                f"{rand['resigned_rate']:.1%}",
                f"{diff(mine['resigned_rate'], rand['resigned_rate']):+.1%} "
                f"± {confidence_interval(mine['resigned_rate'], mine['n_games'], rand['resigned_rate'], rand['n_games']):.1%} (95% CI)"
            ], ['Premove Ratio', f"{mine['premove_ratio']:.1%}", '', ''],
            ['ACPL Premove', f"{mine['premove_acpl']:.1f}", '', ''],
            ['ACPL Non-Premove', f"{mine['non_premove_acpl']:.1f}", '', '']
        ],
                 headers=['Metric', 'You', 'Random', 'Diff±95% CI'],
                 tablefmt='simple'))

    return mine, rand


# --- Main ---
print("Processing your games...")
my_df = GameProcessor.process_games_list(
    Fetchers.fetch_all_users_games(["ffffattyyyy"], None, verbose=False))
print("Processing random games...")
rand_df = GameProcessor.process_games_list(
    Fetchers.fetch_random_games(222, m=420, o=4, verbose=False))
print("Calculating stats...")
my_stats, rand_stats = display_comparison(calc_stats(my_df),
                                          calc_stats(rand_df))
