import requests
from time import sleep
from datetime import datetime


def verify_user_exists(username):
    try:
        requests.get(
            f"https://api.chess.com/pub/player/{username}/games/archives")
        return True
    except:
        print(f"    Username not found: {username}")
        return False


def fetch_user_archives(username):
    sleep(0.03)
    res = requests.get(
        f"https://api.chess.com/pub/player/{username}/games/archives")
    return res.json()['archives']


def fetch_archive_games(username, month, year):
    sleep(0.006)
    res = requests.get(
        f"https://api.chess.com/pub/player/{username}/games/{year}/{month}")
    return res.json()['games']


def fetch_all_users_games(usernames):
    if not usernames or not isinstance(usernames, list):
        return []

    all_games = []
    now = datetime.now()

    for username in usernames:
        if not verify_user_exists(username):
            continue

        print(f"  Fetching games for: {username}...")
        user_game_count = len(all_games)

        archives = fetch_user_archives(username)
        for archive_url in archives:
            year, month = archive_url.split('/')[-2:]

            # Skip future months
            archive_date = datetime(int(year), int(month), 1)
            if archive_date > now:
                continue

            games = fetch_archive_games(username, month, year)
            all_games.extend(games)

        games_for_this_user = len(all_games) - user_game_count
        print(
            f"    {games_for_this_user} games found for {username} (total: {len(all_games)})"
        )

    # Extract PGNs
    return [g['pgn'].replace('\n', '    ') for g in all_games]
