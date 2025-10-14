import chess
import Fetchers, CalcHelpers, Stockfish
from CalcHelpers import print_stats


def main():
    sf_path = "./stockfish/stockfish-ubuntu-x86-64-avx2"
    depth = 10
    user = "ffffattyyyy"
    CalcHelpers.user = user

    print("\nLoading cache...")
    Stockfish.load_cache()

    print("Fetching games...")
    user_games = Fetchers.fetch_all_users_games([user], None)
    random_games = Fetchers.fetch_random_games(1600, 10, 99)
    print(f"  {len(user_games)} user, {len(random_games)} random\n")

    # Analyze every game once
    all_games = list(user_games) + list(random_games)
    print("Analyzing all games (single pass)...")
    all_results = Stockfish.analyze_games(all_games, sf_path, depth, [user],
                                          True)

    # Split results
    ulen = len(user_games)
    user_results, random_results = all_results[:ulen], all_results[ulen:]

    print("Computing stats...\n")

    # Filter valid results
    def filter_valid(games, results):
        valid = [(g, r) for g, r in zip(games, results) if r is not None]
        return zip(*valid) if valid else ([], [])

    user_games, user_results = filter_valid(user_games, user_results)
    random_games, random_results = filter_valid(random_games, random_results)

    print(
        f"  {len(user_results)} valid user, {len(random_results)} valid random\n"
    )

    # Sort and split random games by ELO
    sorted_pairs = sorted(zip(random_games, random_results),
                          key=lambda x: (x[1][4] or 0) if x[1] else 0)
    n = len(sorted_pairs)
    bott_games, bott_results = zip(*sorted_pairs[:int(n *
                                                      0.15)]) if n else ([],
                                                                         [])
    mid_games, mid_results = zip(
        *sorted_pairs[int(n * 0.17):int(n * 0.87)]) if n else ([], [])
    top_games, top_results = zip(*sorted_pairs[int(n * 0.90):]) if n else ([],
                                                                           [])

    print_stats(["Me", "Bott", "Mid", "Top"], [
        user_results,
        list(bott_results),
        list(mid_results),
        list(top_results)
    ], [user_games,
        list(bott_games),
        list(mid_games),
        list(top_games)], [
            user_results,
            list(bott_results),
            list(mid_results),
            list(top_results)
        ])

    Stockfish.save_cache()


if __name__ == "__main__":
    main()
    print("\n-" * 40)
