import random
import httpx
import time
import chess.pgn
import chess
import io


def _sleep(ms):
    time.sleep(ms / 1000)


_client = httpx.Client(headers={"User-Agent": "Mozilla/5.0"})


def _verify_user_exists(username, verbose=False):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    res = _client.get(url)
    return (res.status_code == 200)


def _fetch_user_archives(username, verbose=False):
    _sleep(35)
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    res = _client.get(url)
    if verbose:
        print(f"    GET {url}\t-> {res.status_code}")
    return res.json()["archives"]


def _fetch_archive_games(username, month, year, verbose=False):
    _sleep(5)
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    res = _client.get(url)
    if verbose:
        print(f"    GET {url}\t-> {res.status_code}")
    return res.json()["games"]


def fetch_all_users_games(usernames, n=None, verbose=False):
    if not isinstance(usernames, list) or len(usernames) == 0:
        return []
    all_games = []
    now = time.time()
    for username in usernames:
        if not _verify_user_exists(username, verbose):
            print(f"Error: Username not found: {username}")
            continue
        if verbose:
            print(f"Fetching games for: {username}...")
        user_game_count = len(all_games)
        archives = _fetch_user_archives(username, verbose)
        for archive_url in archives:
            year, month = archive_url.split('/')[-2:]
            archive_timestamp = time.mktime(
                time.strptime(f"{year}-{month}", "%Y-%m"))
            if archive_timestamp > now:
                continue
            games = _fetch_archive_games(username, month, year, verbose)
            all_games.extend(games)
            if n and len(all_games) >= n:
                break
        if verbose:
            games_for_this_user = len(all_games) - user_game_count
            print(f"\n{games_for_this_user} games fetched for {username}\n")
        if n and len(all_games) >= n:
            break
    if n:
        all_games = all_games[:n]

    # Convert PGNs to Game objects
    pgns = [g["pgn"].replace("\n", "\t") for g in all_games]
    return _parse_games_to_objects(pgns)


def _fetch_country_players(country_code, verbose=False):
    _sleep(20)
    url = f"https://api.chess.com/pub/country/{country_code}/players"
    res = _client.get(url)
    if verbose:
        print(f"    GET {url}\t-> {res.status_code}")
    if res.status_code == 200:
        return res.json()["players"]
    return []


def fetch_random_games(n, m=80, verbose=False):
    """Fetch n random chess.pgn.Game objects from various countries (m games per user)."""
    countries = [
        'US', 'IN', 'RU', 'GB', 'DE', 'FR', 'CA', 'AU', 'BR', 'ES', 'IT', 'NL',
        'MX', 'AR', 'PL', 'TR', 'UA', 'SE', 'NO', 'DK', 'FI', 'BE', 'AT', 'CH',
        'PT', 'GR', 'CZ', 'RO', 'HU', 'IL', 'ZA', 'EG', 'NG', 'KE', 'JP', 'KR',
        'CN', 'TH', 'VN', 'ID', 'PH', 'MY', 'SG', 'NZ', 'CL', 'CO', 'PE', 'VE'
    ]
    all_games = []

    while len(all_games) < n:
        country = random.choice(countries)
        players = _fetch_country_players(country, verbose)
        if len(players) < 2:
            continue
        users = random.sample(players, 3)
        games = fetch_all_users_games(users, m, verbose)
        all_games.extend(games)

    print(f'\n{len(all_games[:n])} random games fetched.\n')
    return all_games[:n]


def _parse_games_to_objects(pgn_list):
    """Converts list of PGN strings to chess.pgn.Game objects."""
    games = []
    for pgn in pgn_list:
        game_io = io.StringIO(pgn.replace("\t",
                                          "\n"))  # revert tab back to newline
        game = chess.pgn.read_game(game_io)
        if game:
            games.append(game)
    return games
