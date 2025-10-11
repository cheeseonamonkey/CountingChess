import pandas as pd
import numpy as np
import warnings
import Fetchers
import GameProcessor as gp

warnings.filterwarnings("ignore")


def summarize(df):
    if df.empty:
        return {}
    gb = df.groupby('game_id')
    first = gb.first()
    num_games = df['game_id'].nunique()
    meta = {
        'num_games': num_games,
        'win_rate': first['game_outcome'].eq('win').mean(),
        'avg_elo': first['perspective_elo'].mean(),
        'avg_opponent_elo': first['opponent_elo'].mean(),
        'avg_acpl': gb['centipawn_loss'].mean().mean(),
        'median_acpl': gb['centipawn_loss'].mean().median(),
    }
    ahead = df[df['eval'] > 50]
    behind = df[df['eval'] < -50]
    meta['conv_ahead'] = ahead.groupby('game_id').first()['game_outcome'].eq(
        'win').mean() if not ahead.empty else 0
    meta['comeback'] = behind.groupby('game_id').first()['game_outcome'].eq(
        'win').mean() if not behind.empty else 0
    return meta


def compare(my_df, rand_df):
    print("\nComparing statistics...")
    a = summarize(my_df)
    b = summarize(rand_df)
    all_keys = set(a) | set(b)
    groups = [
        ('Game Stats',
         ['num_games', 'win_rate', 'avg_elo', 'avg_opponent_elo']),
        ('ACPL Metrics', ['avg_acpl', 'median_acpl']),
        ('Conversion Metrics', ['conv_ahead', 'comeback']),
    ]
    for group_name, keys in groups:
        subset = {}
        for k in keys:
            if k in all_keys:
                a_val = a.get(k, np.nan)
                b_val = b.get(k, np.nan)
                diff = a_val - b_val if (isinstance(a_val, (int, float))
                                         and isinstance(b_val,
                                                        (int, float))) else ''
                subset[k] = (a_val if a_val == a_val else '',
                             b_val if b_val == b_val else '', diff)
        if not subset:
            continue
        df = pd.DataFrame(subset, index=['You', 'Random', 'Diff']).T
        print(f"\n=== {group_name} ===")
        print(df.to_string(float_format='%.3f'))


if __name__ == "__main__":
    print("Starting analysis...")
    print("-" * 45)
    users = ["ffffattyyyy", "fffattyyy"]

    print(f"\n[1/4] Fetching games for users: {', '.join(users)}")
    my_games = Fetchers.fetch_all_users_games(users, None)
    print(
        f"      ✓ Fetched {len(my_games) if hasattr(my_games, '__len__') else '?'} games"
    )

    print(f"\n[2/4] Processing user games...")
    mine = gp.process_games_list(my_games, parallel=True, show_progress=True)
    print(
        f"      ✓ Processed {mine['game_id'].nunique() if not mine.empty else 0} unique games"
    )

    print(f"\n[3/4] Fetching random games (n=1, m=35, o=18)...")
    rand_games = Fetchers.fetch_random_games(1, m=35, o=18)
    print(
        f"      ✓ Fetched {len(rand_games) if hasattr(rand_games, '__len__') else '?'} games"
    )

    print(f"\n[4/4] Processing random games...")
    rand = gp.process_games_list(rand_games, parallel=True, show_progress=True)
    print(
        f"      ✓ Processed {rand['game_id'].nunique() if not rand.empty else 0} unique games"
    )

    print("\n" + "=" * 45)
    compare(mine, rand)
    print("\n" + "-" * 45)
    print("Analysis complete!")
