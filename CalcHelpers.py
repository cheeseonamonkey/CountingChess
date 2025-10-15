import os
from collections import defaultdict
import chess.pgn
from io import StringIO


# --- Internal helpers ---
def _pdiff(results):
    return [
        max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
        for ev, _, _, c, *_ in results for i in range(1, len(ev))
        if c is None or i % 2 == c
    ]


def _metric(results, fn):
    diffs = fn(results)
    return sum(diffs) / len(diffs) if diffs else 0


# --- Metrics ---
METRICS = {
    'acpl':
    lambda r: _metric(r, _pdiff),
    'sharpness':
    lambda r: _metric(
        r, lambda x:
        [abs(ev[i] - ev[i - 1]) for ev, *_ in x for i in range(1, len(ev))]),
    'closedness':
    lambda r: _metric(r, lambda x: [pc for _, _, pws, *_ in x for pc in pws]),
    'resign_rate':
    lambda r: (100 * sum(1 for x in lost if x[8]) / len(lost)
               if (lost := [x for x in r if x[7] is False]) else 0),
    'best_move_rate':
    lambda r: 100 * _metric(r, lambda x:
                            [b for *_, bms, _, _ in x for b in bms]),
}


# --- Per-piece metrics ---
def pmetrics(results):
    acpl = defaultdict(float)
    cnt = defaultdict(int)
    for ev, pcs, _, c, *_ in results:
        for i in range(1, len(ev)):
            if c is None or i % 2 == c:
                diff = max(0,
                           ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                acpl[pcs[i - 1]] += diff
                cnt[pcs[i - 1]] += 1
    total_moves = sum(cnt.values()) or 1
    acpl_avg = {p: acpl[p] / cnt[p] for p in acpl if cnt[p]}
    piece_pct = {p: 100 * cnt[p] / total_moves for p in cnt}
    return acpl_avg, piece_pct


# --- Castle & turn metrics ---
def cmetrics(results):
    side = defaultdict(lambda: [0, 0])
    turn = defaultdict(lambda: [0, 0])
    for *_, ct, cs, won, _, _, _, _ in results:
        if cs and won is not None:
            side[cs][won] += 1
            grp = ("<=4" if ct <= 4 else "5-6" if ct <= 6 else "7-8"
                   if ct <= 8 else "9-10" if ct <= 10 else "11-12" if ct <=
                   12 else "13-15" if ct <= 15 else ">15")
            turn[grp][won] += 1
    return (
        {
            k: 100 * v[1] / sum(v) if sum(v) else 0
            for k, v in side.items()
        },
        {
            k: 100 * v[1] / sum(v) if sum(v) else 0
            for k, v in turn.items()
        },
    )


# --- Time & game metrics ---
def tmetrics(results):
    acpl = defaultdict(list)
    wins = defaultdict(lambda: [0, 0])
    for ev, _, _, c, _, _, _, won, _, _, h, _ in results:
        if h is not None:
            diffs = [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if c is None or i % 2 == c
            ]
            if diffs:
                acpl[h].extend(diffs)
            if won is not None:
                wins[h][won] += 1
    return (
        {
            h: sum(d) / len(d)
            for h, d in acpl.items() if d
        },
        {
            h: 100 * v[1] / sum(v) if sum(v) else 0
            for h, v in wins.items()
        },
    )


def gmetrics(results):
    acpl = defaultdict(list)
    wins = defaultdict(lambda: [0, 0])
    for ev, _, _, c, _, _, _, won, _, _, _, gn in results:
        if gn is not None:
            diffs = [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if c is None or i % 2 == c
            ]
            if diffs:
                acpl[gn].extend(diffs)
            if won is not None:
                wins[gn][won] += 1
    return (
        {
            g: sum(d) / len(d)
            for g, d in acpl.items() if d
        },
        {
            g: 100 * v[1] / sum(v) if sum(v) else 0
            for g, v in wins.items()
        },
    )


# --- ECO stats ---
def eco_stats(pgns, res, users=None):
    """
    Compute ECO statistics for given users (or all if None).
    """
    ew = defaultdict(lambda: {'a': [], 'w': 0, 'l': 0})
    eb = defaultdict(lambda: {'a': [], 'w': 0, 'l': 0})
    ul = [u.lower() for u in (users or [])]

    for pgn, rs in zip(pgns, res):
        if not rs:
            continue
        try:
            g = chess.pgn.read_game(StringIO(pgn)) if isinstance(pgn,
                                                                 str) else pgn
            if not g or not (eco := g.headers.get("ECO")):
                continue
            w, b = g.headers.get("White",
                                 "").lower(), g.headers.get("Black",
                                                            "").lower()
            c = chess.WHITE if w in ul else chess.BLACK if b in ul else None
            ev, *rest = rs
            diffs = [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if c is None or i % 2 == c
            ]
            a = sum(diffs) / len(diffs) if diffs else 0
            ed = ew if c == chess.WHITE else eb if c == chess.BLACK else None
            if ed:
                ed[eco]['a'].append(a)
                if rest[5] is not None:
                    ed[eco]['w' if rest[5] else 'l'] += 1
        except Exception:
            pass

    def summar(d):
        return {
            e: {
                'a': sum(v['a']) / len(v['a']) if v['a'] else 0,
                'w':
                100 * v['w'] / (v['w'] + v['l']) if v['w'] + v['l'] else 0,
                'n': v['w'] + v['l']
            }
            for e, v in d.items() if v['a']
        }

    return summar(ew), summar(eb)


# --- Print stats ---
def print_stats(lbls, dsets, pgn_sets=None, res_sets=None, user=None):
    """
    Print and return chess statistics for datasets.
    """
    pn = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
    stats = [{k: f(d) for k, f in METRICS.items()} for d in dsets]
    ps = [pmetrics(d) for d in dsets]
    cs = [cmetrics(d) for d in dsets]
    ts = [tmetrics(d) for d in dsets]
    gs = [gmetrics(d) for d in dsets]

    counts = [len(d) for d in dsets]
    w = 9 + 8 * len(lbls)

    print(f"\n{'Metric':<9} " + ' '.join(f"{l:>7}"
                                         for l in lbls) + f"\n{'='*w}")
    print(f"{'n (count)':<9} " + ' '.join(f"{n:>7}" for n in counts))
    for m, l in [('acpl', 'ACPL'), ('sharpness', 'Sharp'),
                 ('closedness', 'Closed')]:
        print(f"{l:<9} " + ' '.join(f"{s[m]:>7.1f}" for s in stats))
    print(f"{'-'*w}")

    for p in range(1, 7):
        print(f"{pn[p]+' ACPL':<9} " + ' '.join(f"{x[0].get(p,0):>7.1f}"
                                                for x in ps))
    print(f"{'-'*w}")
    for p in range(1, 7):
        print(f"{pn[p]+' %':<9} " + ' '.join(f"{x[1].get(p,0):>7.1f}"
                                             for x in ps))
    print(f"{'-'*w}")

    print(f"{'Resign%':<9} " + ' '.join(f"{s['resign_rate']:>7.1f}"
                                        for s in stats))
    print(f"{'Best%':<9} " + ' '.join(f"{s['best_move_rate']:>7.1f}"
                                      for s in stats))
    print(f"{'-'*w}")

    for side in ["OO", "OOO"]:
        print(f"{side+'-WR':<8} " + ' '.join(f"{x[0].get(side,0):>7.1f}"
                                             for x in cs))
    for t in ["<=4", "5-6", "7-8", "9-10", "11-12", "13-15", ">15"]:
        print(f"C {t:<6} " + ' '.join(f"{x[1].get(t,0):>7.1f}" for x in cs))
    print(f"{'-'*w}")

    # ECO stats
    if pgn_sets and res_sets:
        for i, (l, p, r) in enumerate(zip(lbls, pgn_sets, res_sets)):
            users_param = [user] if user and i == 0 else None
            ew, eb = eco_stats(p, r, users=users_param)
            if ew or eb:
                print(f"\n{l} ECO:")
                for color, data in [("W", ew), ("B", eb)]:
                    if data:
                        print(f"  {color}:")
                        for eco, d in sorted(data.items(),
                                             key=lambda x: -x[1]['n'])[:10]:
                            print(
                                f"    {eco} n:{d['n']:>2} A:{d['a']:>5.1f} W:{d['w']:>5.1f}%"
                            )

    if dsets:
        user_games = dsets[0]
        if gs[0][0] or gs[0][1]:
            print(f"\n{lbls[0]} Game# per Day:")
            keys = sorted(set(gs[0][0]) | set(gs[0][1]))
            for g in keys:
                n = sum(1 for ev, *_, _, _, _, _, _, _, _, _, gn in user_games
                        if gn == g)
                print(
                    f"  {g:>2} \tA:{gs[0][0].get(g,0):>5.1f} \tW:{gs[0][1].get(g,0):>5.1f}% \tn={n:>3}"
                )

        print(f"\n{lbls[0]} Time of Day:")
        for h in range(24):
            n = sum(1 for ev, *_, _, _, _, _, _, _, _, hr, _ in user_games
                    if hr == h)
            print(
                f"  {h:02d}h \tA:{ts[0][0].get(h,0):>5.1f} \tW:{ts[0][1].get(h,0):>5.1f}% \tn={n:>3}"
            )

    return {
        "counts": counts,
        "metrics": stats,
        "piece_metrics": ps,
        "castle_metrics": cs,
        "time_metrics": ts,
        "game_metrics": gs
    }


# --- SPEEDUP HELPERS (non-invasive, call explicitly) ---
# usage: fast_eval_fens(fens, "/path/to/stockfish", depth=12, threads=2, procs=4)
def fast_eval_fens(fens,
                   engine_path,
                   depth=12,
                   threads=1,
                   procs=4,
                   hash_mb=64,
                   cache=True):
    """
    Parallel, process-local persistent engine workers + optional FEN caching.
    Doesn't import extra libs at module import time (keeps your hooks).
    """
    if not fens:
        return []
    from multiprocessing import Pool
    import atexit, functools, hashlib, json, time

    # small in-process LRU cache (per master process) to avoid duplicates before mapping
    seen = {}
    unique = []
    idxs = []
    for i, f in enumerate(fens):
        k = f if not cache else hashlib.md5(f.encode()).hexdigest()
        if k in seen:
            idxs.append(seen[k])
        else:
            seen[k] = len(unique)
            unique.append(f)
            idxs.append(seen[k])

    # worker initializer sets globals in each process (engine opened once per worker)
    def _init_worker(ep, th, hm, dp):
        global _ENGINE, _DEPTH
        import chess, chess.engine
        _DEPTH = dp
        _ENGINE = chess.engine.SimpleEngine.popen_uci(ep)
        try:
            _ENGINE.configure({"Threads": th, "Hash": hm})
        except Exception:
            pass
        import atexit
        atexit.register(lambda: _ENGINE.quit())

    def _worker(fen):
        # minimal imports inside worker to avoid global import side-effects
        import chess
        try:
            board = chess.Board(fen)
            info = _ENGINE.analyse(board, chess.engine.Limit(depth=_DEPTH))
            sc = info.get("score")
            if sc is None:
                return 0
            # unify mate/cp
            try:
                val = sc.white().score(mate_score=100000)
                return 0 if val is None else val
            except Exception:
                return 0
        except Exception:
            return 0

    # map unique fens to scores
    with Pool(processes=procs,
              initializer=_init_worker,
              initargs=(engine_path, threads, hash_mb, depth)) as P:
        out = P.map(_worker, unique)

    # reconstruct original order
    return [out[i] for i in idxs]


# tiny convenience: extract FENs from PGN positions (first-node FENs or per-move FENs)
def pgn_extract_fens(pgn_text_or_game, per_move=True):
    """
    Return list of FENs (per-move if per_move else start FEN of game).
    Non-invasive: uses chess.pgn only when called.
    """
    import chess.pgn
    g = chess.pgn.read_game(StringIO(pgn_text_or_game)) if isinstance(
        pgn_text_or_game, str) else pgn_text_or_game
    if not g:
        return []
    if not per_move:
        return [g.board().fen()]
    b = g.board()
    fens = []
    for mv in g.mainline_moves():
        b.push(mv)
        fens.append(b.fen())
    return fens


# NOTES (keep short):
# - call fast_eval_fens with a deduped list of FENs (use pgn_extract_fens to get them).
# - prefer lower depth (10-14) + more threads per engine + multiple processes.
# - set procs ~= CPU cores/threads/2, keep Threads in engine >1 for multi-core Stockfish builds.
# - use hash_mb to give engine more cache.
# - caching (cache=True) dedups identical FENs before expensive eval.
# - this file leaves your original imports & hooks untouched; call helpers explicitly.
