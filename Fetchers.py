import random, httpx, chess.pgn, io, json, gzip, hashlib
from pathlib import Path
from collections import deque

_client = httpx.Client(
    headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })
_cache_dir = Path(".cache/chess_api")
_cache_dir.mkdir(parents=True, exist_ok=True)


def _cache(key, data=None):
    f = _cache_dir / f"{key}.gz"
    if data is None:
        return json.loads(gzip.decompress(
            f.read_bytes())) if f.exists() else None
    f.write_bytes(gzip.compress(json.dumps(data).encode()))


def _get_user_country(username):
    key = f"user_country_{username}"
    if cached := _cache(key): return cached
    res = _client.get(f"https://api.chess.com/pub/player/{username}")
    country = res.json().get(
        "country", "").split('/')[-1] if res.status_code == 200 else None
    _cache(key, country)
    return country


def _fetch_user_archives(username, verbose=False):
    key = f"{username}_archives"
    if cached := _cache(key):
        if verbose: print(f"✓ cached archives: {username}")
        return cached
    if verbose: print(f"→ fetching archives: {username}")
    res = _client.get(
        f"https://api.chess.com/pub/player/{username}/games/archives")
    if res.status_code != 200: return []
    archives = res.json()["archives"]
    _cache(key, archives)
    if verbose: print(f"✓ saved {len(archives)} archives")
    return archives


def _fetch_archive_games(username, month, year, verbose=False):
    if verbose: print(f"→ downloading {year}/{month}")
    res = _client.get(
        f"https://api.chess.com/pub/player/{username}/games/{year}/{month}")
    games = res.json()["games"] if res.status_code == 200 else []
    if verbose: print(f"✓ got {len(games)} games")
    return games


def fetch_all_users_games(usernames, n=None, verbose=False):
    if not isinstance(usernames, list): return []
    h = hashlib.md5('_'.join(sorted(usernames)).encode()).hexdigest()
    cache_key = f"users_{h}_{n}"
    if cached := _cache(cache_key):
        if verbose: print(f"✓ loaded {len(cached)} cached games")
        return _parse_games(cached)
    all_games = []
    for username in usernames:
        if not _get_user_country(username):
            if verbose: print(f"✗ user not found: {username}")
            continue
        if verbose: print(f"→ {username}")
        archives = _fetch_user_archives(username, verbose)
        user_games = 0
        for archive in archives:
            year, month = archive.split('/')[-2:]
            added = _fetch_archive_games(username, month, year, verbose)
            all_games.extend(added)
            user_games += len(added)
            if n and len(all_games) >= n: break
        if verbose: print(f"✓ {user_games} games from {username}")
        if n and len(all_games) >= n: break
    pgns = [g["pgn"].replace("\n", "\t") for g in all_games if "pgn" in g]
    result = _parse_games(pgns)[:n]
    _cache(cache_key, [g.accept(chess.pgn.StringExporter()) for g in result])
    if verbose: print(f"✓ parsed {len(result)} games")
    return result


def _fetch_country_players(country_code, verbose=False):
    key = f"country_{country_code}_players"
    if cached := _cache(key):
        if verbose:
            print(f"✓ cached {len(cached)} players from {country_code}")
        return cached
    if verbose: print(f"→ fetching players from {country_code}")
    res = _client.get(
        f"https://api.chess.com/pub/country/{country_code}/players")
    players = res.json()["players"] if res.status_code == 200 else []
    _cache(key, players)
    if verbose: print(f"✓ found {len(players)} players")
    return players


def spider_users(seed_user, n, m=50, o=3, verbose=False):
    """
    BFS spider from seed_user to collect n unique users via opponents in games.
    """
    h = hashlib.md5(f"{seed_user}_{n}_{m}_{o}".encode()).hexdigest()
    cache_key = f"spider_users_{h}"
    if cached := _cache(cache_key):
        if verbose: print(f"✓ loaded {len(cached)} cached users")
        return cached
    if not _get_user_country(seed_user):
        if verbose: print(f"✗ seed user not found: {seed_user}")
        return []
    users = {seed_user}
    queue = deque([seed_user])
    while len(users) < n and queue:
        current = queue.popleft()
        if verbose: print(f"→ crawling {current} ({len(users)}/{n})")
        games = fetch_all_users_games([current], m, verbose)
        opponents = {
            opp
            for game in games
            for opp in (game.headers.get("White"), game.headers.get("Black"))
            if opp and opp != current
        }
        candidates = opponents - users
        if not candidates: continue
        new_opps = random.sample(list(candidates), min(o, len(candidates)))
        users.update(new_opps)
        queue.extend(new_opps)
        shuffled = list(queue)
        random.shuffle(shuffled)
        queue.clear()
        queue.extend(shuffled)
        if verbose: print(f"  added {len(new_opps)} new users")
    result = list(users)[:n]
    _cache(cache_key, result)
    if verbose: print(f"✓ collected {len(result)} users")
    return result


def fetch_random_games(n, m=50, o=3, verbose=False):
    cache_key = f"random_games_{n}_{m}_{o}"
    if cached := _cache(cache_key):
        if verbose: print(f"✓ loaded {len(cached)} cached games")
        cached_games = _parse_games(cached)
        if len(cached_games) >= n: return cached_games
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
    while len(all_games) < n:
        country = random.choice(countries)
        if verbose: print(f"\r→ sampling {country} ({attempts+1})", end='')
        players = _fetch_country_players(country, verbose)
        if len(players) < o:
            if verbose: print(f" ✗ only {len(players)} players, skipping")
            continue
        selected = random.sample(players, o)
        games = fetch_all_users_games(selected, m, verbose)
        all_games.extend(games)
        attempts += 1
        if verbose:
            print(
                f"\rGathering games: {len(all_games):4d}/{n:4d} (attempts: {attempts})",
                end='')
    if verbose: print()
    random.shuffle(all_games)
    filtered = [g for g in all_games[:n] if _valid_elo(g)]
    if not cached or len(filtered) > len(_parse_games(cached)):
        _cache(cache_key,
               [g.accept(chess.pgn.StringExporter()) for g in filtered])
        if verbose: print(f"✓ cached {len(filtered)} games")
    if verbose:
        print(
            f"✓ fetched {len(filtered)} valid games from {attempts} countries")
    return filtered


def spider_games(seed_user, n_games, m=20, o=10, verbose=False):
    """
    Args:
        seed_user: Starting username
        n_games: Target number of games to fetch
        m: Games per user in spider
        o: Opponents sampled per iteration
        verbose: Print progress
    """
    # Estimate users needed (rough heuristic: m games per user)
    estimated_users = max(5, (n_games // m) + 2)
    users = spider_users(seed_user, estimated_users, m, o, verbose)
    return fetch_all_users_games(users, n_games, verbose)


def _valid_elo(game):
    try:
        return int(game.headers.get("WhiteElo", 0)) >= 10 and int(
            game.headers.get("BlackElo", 0)) >= 10
    except (ValueError, TypeError):
        return False


def _parse_games(pgn_list):
    return [
        game for pgn in pgn_list
        if (game := chess.pgn.read_game(io.StringIO(pgn.replace("\t", "\n")))
            ) is not None
    ]
