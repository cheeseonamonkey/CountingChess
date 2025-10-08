import random
import httpx
import chess.pgn
import io
import json
import gzip
from pathlib import Path

_client = httpx.Client(headers={"User-Agent": "Mozilla/5.0"})
_cache_dir = Path(".cache/chess_api")
_cache_dir.mkdir(parents=True, exist_ok=True)

def _cache_get(key):
    f = _cache_dir / f"{key}.gz"
    return json.loads(gzip.decompress(f.read_bytes())) if f.exists() else None

def _cache_set(key, data):
    (_cache_dir / f"{key}.gz").write_bytes(gzip.compress(json.dumps(data).encode()))


def _verify_user_exists(username, verbose=False):
    return _client.get(
        f"https://api.chess.com/pub/player/{username}/games/archives"
    ).status_code == 200


def _fetch_user_archives(username, verbose=False):
    cache_file = _cache_dir / f"{username}_archives.json"
    if cache_file.exists():
        if verbose: print(f"  ✓ cached archives: {username}")
        return json.loads(cache_file.read_text())
    if verbose: print(f"  → fetching archives: {username}")
    archives = _client.get(
        f"https://api.chess.com/pub/player/{username}/games/archives").json(
        )["archives"]
    cache_file.write_text(json.dumps(archives))
    if verbose: print(f"  ✓ saved {len(archives)} archives to cache")
    return archives


def _fetch_archive_games(username, month, year, verbose=False):
    if verbose: print(f"    → downloading {year}/{month}")
    games = _client.get(
        f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    ).json()["games"]
    if verbose: print(f"    ✓ got {len(games)} games")
    return games


def fetch_all_users_games(usernames, n=None, verbose=False):
    if not isinstance(usernames, list) or len(usernames) == 0:
        return []

    all_games = []
    for username in usernames:
        if not _verify_user_exists(username, verbose):
            print(f"✗ user not found: {username}")
            continue
        if verbose: print(f"→ {username}")
        user_game_count = len(all_games)

        archives = _fetch_user_archives(username, verbose)
        for archive_url in archives:
            year, month = archive_url.split('/')[-2:]
            games = _fetch_archive_games(username, month, year, verbose)
            all_games.extend(games)
            if n and len(all_games) >= n: 
                break

        if verbose:
            print(f"  ✓ {len(all_games) - user_game_count} total from {username}\n")
        if n and len(all_games) >= n:
            break

    if n: 
        all_games = all_games[:n]

    if verbose: 
        print(f"→ parsing {len(all_games)} games to objects...")

    # Filter out games without 'pgn' and parse safely
    parsed = _parse_games_to_objects(
        [g["pgn"].replace("\n", "\t") for g in all_games if "pgn" in g]
    )

    if verbose: 
        print(f"✓ parsed {len(parsed)} games successfully\n")
    return parsed


def _fetch_country_players(country_code, verbose=False):
    if verbose: print(f"  → fetching players from {country_code}")
    res = _client.get(
        f"https://api.chess.com/pub/country/{country_code}/players")
    players = res.json()["players"] if res.status_code == 200 else []
    if verbose: print(f"  ✓ found {len(players)} players")
    return players


def fetch_random_games(n, m=50, o=3, verbose=False):
    """Fetch n random games, max m per user, from o users per country."""
    countries = [
        'US', 'IN', 'RU', 'GB', 'DE', 'FR', 'CA', 'AU', 'BR', 'ES', 'IT', 'NL',
        'MX', 'AR', 'PL', 'TR', 'UA', 'SE', 'NO', 'DK', 'FI', 'BE', 'AT', 'CH',
        'PT', 'GR', 'CZ', 'RO', 'HU', 'IL', 'ZA', 'EG', 'NG', 'KE', 'JP', 'KR',
        'CN', 'TH', 'VN', 'ID', 'PH', 'MY', 'SG', 'NZ', 'CL', 'CO', 'PE', 'VE',
        'IE', 'PK', 'BD', 'SA', 'AE', 'TW', 'HK', 'MA', 'DZ', 'TN', 'GH', 'ET',
        'UY', 'EC', 'CR', 'PA', 'DO', 'BG', 'HR', 'SK', 'SI', 'LT', 'LV', 'EE',
        'RS', 'BA', 'MK', 'AL', 'IS', 'LU', 'CY', 'MT', 'QA', 'KW', 'OM', 'BH',
        'JO', 'LB', 'IQ', 'LY', 'SD', 'TZ', 'UG', 'AO', 'SN', 'CI', 'CM', 'MZ',
        'BY', 'KZ', 'UZ', 'GE', 'AM', 'AZ', 'MD', 'NP', 'LK', 'MM', 'KH', 'LA',
        'BN', 'MN', 'AF', 'YE', 'SY', 'PS', 'ZW'
    ]

    all_games, attempts = [], 0
    if verbose:
        print(
            f"→ fetching {n} random games (max {m}/user, {o} users/country)\n")
    while len(all_games) < n:
        country = random.choice(countries)
        if verbose: print(f"→ sampling country: {country}")
        players = _fetch_country_players(country, verbose)
        if len(players) < o:
            if verbose: print(f"  ✗ only {len(players)} players, skipping\n")
            continue
        selected = random.sample(players, o)
        if verbose: print(f"  → selected {o} random players")
        games = fetch_all_users_games(selected, m, verbose)
        all_games.extend(games)
        attempts += 1
        if verbose: print(f"✓ total games collected: {len(all_games)}/{n}\n")
    print(f'✓ fetched {len(all_games[:n])} games from {attempts} countries\n')
    return all_games[:n]


def _parse_games_to_objects(pgn_list):
    return [
        game for pgn in pgn_list
        if (game := chess.pgn.read_game(io.StringIO(pgn.replace("\t", "\n"))))
    ]


def _get_user_country(username, verbose=False):
    res = _client.get(f"https://api.chess.com/pub/player/{username}")
    if res.status_code == 200:
        country_url = res.json().get("country", "")
        return country_url.split('/')[-1] if country_url else None
    return None
