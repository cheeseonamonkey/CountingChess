import chess
import Fetchers, CalcHelpers, Stockfish
from CalcHelpers import print_stats


def main():
    sf_path, depth, user = "./stockfish/stockfish-ubuntu-x86-64-avx2", 10, "ffffattyyyy"
    CalcHelpers.user = user
    Stockfish.load_cache()

    print("Fetching games...")
    user_games = Fetchers.fetch_all_users_games([user], None)[:55] 
    random_games = Fetchers.fetch_random_games(20, 10, 33)

    print(f"  {len(user_games)} user, {len(random_games)} random\n")

    print("Analyzing user games...")
    user_results = Stockfish.analyze_games(user_games, sf_path, depth, [user], True)
    print("Analyzing random games...")
    random_results = Stockfish.analyze_games(random_games, sf_path, depth)
    print("Computing stats...\n")

    # Sort and split random games by ELO
    sorted_pairs = sorted(zip(random_games, random_results),
                         key=lambda x: (x[1][4] or 0) if x[1] else 0)
    n = len(sorted_pairs)

    # Fixed splitting logic: LOW: 0-15%, MID: 17-87%, TOP: 90-100%
    # This creates small gaps to emphasize differences
    bott_games, bott_results = zip(*sorted_pairs[:int(n * 0.15)]) if n else ([], [])
    mid_games, mid_results = zip(*sorted_pairs[int(n * 0.17):int(n * 0.87)]) if n else ([], [])
    top_games, top_results = zip(*sorted_pairs[int(n * 0.90):]) if n else ([], [])

    print_stats(["Me", "Bott", "Mid", "Top"],
                [user_results, list(bott_results), list(mid_results), list(top_results)],
                [user_games, list(bott_games), list(mid_games), list(top_games)],
                [user_results, list(bott_results), list(mid_results), list(top_results)])

    Stockfish.save_cache()


if __name__ == "__main__":
    main()
    print("\n-" * 40)