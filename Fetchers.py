import requests
from time import sleep
from datetime import datetime


def _verify_user_exists(username):
    try:
        res = requests.get(
            f"https://api.chess.com/pub/player/{username}/games/archives")
        if res.status_code == 200:
            return True
        else:
            print(f"    Username not found: {username} (status code: {res.status_code})")
            return False
    except Exception as e:
        print(f"    Error checking username {username}: {e}")
        return False


def _fetch_user_archives(username):
    sleep(0.03)
    res = requests.get(
        f"https://api.chess.com/pub/player/{username}/games/archives")
    if res.status_code == 200:
        try:
            return res.json()['archives']
        except:
            print(f"    Error parsing archives for {username}")
            return []
    else:
        print(f"    Failed to fetch archives for {username} (status code: {res.status_code})")
        return []


def _fetch_archive_games(username, month, year):
    sleep(0.006)
    res = requests.get(
        f"https://api.chess.com/pub/player/{username}/games/{year}/{month}")
    if res.status_code == 200:
        try:
            return res.json()['games']
        except:
            print(f"    Error parsing games for {username}/{year}/{month}")
            return []
    else:
        print(f"    Failed to fetch games for {username}/{year}/{month} (status code: {res.status_code})")
        return []


def fetch_all_users_games(usernames):
    if not usernames or not isinstance(usernames, list):
        return []

    all_games = []
    now = datetime.now()

    for username in usernames:
        if not _verify_user_exists(username):
            continue

        print(f"  Fetching games for: {username}...")
        user_game_count = len(all_games)

        archives = _fetch_user_archives(username)
        for archive_url in archives:
            year, month = archive_url.split('/')[-2:]

            # Skip future months
            archive_date = datetime(int(year), int(month), 1)
            if archive_date > now:
                continue

            games = _fetch_archive_games(username, month, year)
            all_games.extend(games)

        games_for_this_user = len(all_games) - user_game_count
        print(
            f"    {games_for_this_user} games found for {username} (total: {len(all_games)})"
        )

    # Extract PGNs
    return [g['pgn'].replace('\n', '    ') for g in all_games]
