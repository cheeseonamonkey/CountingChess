import chess
import Fetchers, CalcHelpers, Stockfish
from CalcHelpers import print_stats
from tqdm import tqdm
from itertools import chain


def main():
    print("Hello!\n")
    sf_path = "./stockfish/stockfish-ubuntu-x86-64-avx2"
    depth, user = 10, "ffffattyyyy"
    CalcHelpers.user = user

    print("Loading cache...")
    Stockfish.load_cache()

    print("Fetching games...")
    user_games = Fetchers.fetch_all_users_games([user], None)
    random_games = Fetchers.fetch_random_games(2750, 10, 99)
    print(f"  {len(user_games)} user, {len(random_games)} random\n")

    all_games = list(user_games) + list(random_games)
    print("Analyzing all games (single pass)...")
    all_results = Stockfish.analyze_games(all_games, sf_path, depth, [user],
                                          True)

    ulen = len(user_games)
    user_results, random_results = all_results[:ulen], all_results[ulen:]

    print("Computing stats...\n")

    def filter_valid(games, results):
        valid = [(g, r) for g, r in zip(games, results) if r is not None]
        return zip(*valid) if valid else ([], [])

    user_games, user_results = filter_valid(user_games, user_results)
    random_games, random_results = filter_valid(random_games, random_results)
    print(
        f"  {len(user_results)} valid user, {len(random_results)} valid random\n"
    )

    # Sort and split random games by ELO with progress
    sorted_pairs = sorted(zip(random_games, random_results),
                          key=lambda x: (x[1][4] or 0) if x[1] else 0)
    n = len(sorted_pairs)

    splits = [0, int(n * 0.15), int(n * 0.17), int(n * 0.87), int(n * 0.90), n]
    groups = []
    for i in tqdm(range(len(splits) - 1), desc="Splitting ELO groups"):
        start, end = splits[i], splits[i + 1]
        games, results = zip(*sorted_pairs[start:end]) if start < end else ([],
                                                                            [])
        groups.append((list(games), list(results)))

    bott_games, bott_results = groups[0]
    mid_games, mid_results = groups[1]
    top_games, top_results = groups[2]

    print_stats(["Me", "Bott", "Mid", "Top"],
                [user_results, bott_results, mid_results, top_results],
                [user_games, bott_games, mid_games, top_games],
                [user_results, bott_results, mid_results, top_results])

    Stockfish.save_cache()


if __name__ == "__main__":
    main()
    print("\n" + "-" * 40)
