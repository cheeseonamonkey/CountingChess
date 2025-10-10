import pandas as pd
import numpy as np
import warnings
import Fetchers
import GameProcessor as gp

CORR_METRICS = [
    'openness', 'development', 'mobility', 'sharpness', 'center_control',
    'king_safety', 'pawn_structure', 'space', 'time_spent', 'centipawn_loss'
]
def summarize(df):
    if df.empty:
        return {}

    gb = df.groupby('game_id')
    first = gb.first()

    meta = {
        # --- Overall results ---
        'num_games': df['game_id'].nunique(),
        'win_rate': first['game_outcome'].eq('win').mean(),
        'resign_rate': first.get('resigned_or_abandoned', pd.Series([0])).mean(),
        'avg_elo': df['perspective_elo'].mean(),
        'avg_opponent_elo': df['opponent_elo'].mean(),

        # --- ACPL & time metrics ---
        'avg_acpl': gb['centipawn_loss'].mean().mean(),
        'median_acpl': gb['centipawn_loss'].mean().median(),
        'avg_time': df['time_spent'].mean(),
        'longest_think': df.groupby(['game_id', 'perspective_user'])['time_spent'].max().mean(),

        # --- Evaluation & dynamics ---
        'eval_volatility': df.groupby(['game_id', 'perspective_user'])['eval'].std().mean(),
        'material_swing': df.groupby(['game_id', 'perspective_user'])['material'].agg(lambda s: s.max() - s.min()).mean(),
    }

    # --- Phases / openings ---
    meta.update({f'phase_{k}': v for k, v in df['phase'].value_counts(normalize=True).items()})
    meta.update({f'open_{k}': v for k, v in df.groupby('opening').game_id.nunique().nlargest(5).items()})

    # --- Comeback / Conversion ---
    ahead, behind = df[df['eval'] > 50], df[df['eval'] < -50]
    meta['conv_ahead'] = ahead.groupby('game_id').first()['game_outcome'].eq('win').mean() if not ahead.empty else 0
    meta['comeback'] = behind.groupby('game_id').first()['game_outcome'].eq('win').mean() if not behind.empty else 0

    # --- ACPL per piece moved ---
    if 'last_piece' in df.columns:
        piece_acpl = df.groupby('last_piece')['centipawn_loss'].mean()
        meta.update({f'acpl_{k}': v for k, v in piece_acpl.items()})

    # --- Correlations ---
    try:
        available = [m for m in CORR_METRICS if m in df.columns]
        if available:
            corr = df[available].corr()['centipawn_loss'].drop('centipawn_loss', errors='ignore')
            meta.update({f'corr_{k}': v for k, v in corr.items()})
    except Exception:
        pass

    return meta

def compare(my_df, rand_df):
    my_elo = my_df['perspective_elo'].mean()
    elo_range = 100
    top20_threshold = rand_df['perspective_elo'].quantile(0.8)
    bot20_threshold = rand_df['perspective_elo'].quantile(0.2)

    a = summarize(my_df)
    b = summarize(rand_df)
    c = summarize(rand_df[(rand_df['perspective_elo'] >= my_elo - elo_range) & 
                          (rand_df['perspective_elo'] <= my_elo + elo_range)])
    d = summarize(rand_df[rand_df['perspective_elo'] >= top20_threshold])
    e = summarize(rand_df[rand_df['perspective_elo'] <= bot20_threshold])

    groups = [
        ('Game Stats', ['num_games', 'win_rate', 'resign_rate']),
        ('ACPL / Time', ['avg_acpl', 'median_acpl', 'avg_time', 'longest_think']),
        ('Eval & Dynamics', ['eval_volatility', 'material_swing', 'conv_ahead', 'comeback']),
        ('Phase / Openings', [k for k in a if k.startswith('phase_') or k.startswith('open_')]),
        ('Piece ACPL', [k for k in a if k.startswith('acpl_')]),
        ('Piece Ratios', [k for k in a if k.startswith('ratio_')]),
        ('Correlations', [k for k in a if k.endswith('_corr')]),
    ]

    for group_name, keys in groups:
        subset = {k: (a.get(k, ''), b.get(k, ''), c.get(k, ''), d.get(k, ''), e.get(k, '')) 
                  for k in keys if k in a or k in b}
        if not subset:
            continue
        df = pd.DataFrame(subset, index=['You', 'Random', 'My ELO', 'Top 20%', 'Bottom 20%']).T
        print(f"\n=== {group_name} ===")
        print(df.to_string(float_format='%.3f'))

if __name__ == "__main__":
    print("fetching...")
    mine = gp.process_games_list(Fetchers.fetch_all_users_games(["ffffattyyyy", "fffattyyy"], None))
    rand = gp.process_games_list(Fetchers.fetch_random_games(7999, m=35, o=18))
    print("analyzing...")
    compare(mine, rand)




print("\n-"*45)


