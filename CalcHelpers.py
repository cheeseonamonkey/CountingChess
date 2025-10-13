# CalcHelpers.py
from collections import defaultdict, Counter
import chess, chess.pgn
from io import StringIO

user = None


def _pdiff(r):
    """Extract player centipawn losses."""
    return [
        max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
        for ev, _, _, c, *_ in r for i in range(1, len(ev))
        if not c or i % 2 == c
    ]


METRICS = {
    'acpl':
    lambda r: (d := _pdiff(r)) and sum(d) / len(d),
    'sharpness':
    lambda r:
    (d := [abs(ev[i] - ev[i - 1]) for ev, *_ in r
           for i in range(1, len(ev))]) and sum(d) / len(d),
    'closedness':
    lambda r:
    (p := [pc for _, _, pws, *_ in r for pc in pws]) and sum(p) / len(p),
    'resign_rate':
    lambda r: ((lost := [x for x in r if x[7] == False]) and len(lost) > 0 and
               sum(1 for x in lost if x[8]) / len(lost) * 100) or 0,
    'best_move_rate':
    lambda r: (bm := [b for *_, bms, _, _ in r
                      for b in bms]) and sum(bm) / len(bm) * 100
}


def pmetrics(r):
    """Piece ACPL and frequency."""
    acpl, cnt = defaultdict(list), defaultdict(int)
    for ev, pcs, _, c, *_ in r:
        for i in range(1, len(ev)):
            if c is None or i % 2 == c:
                acpl[pcs[i - 1]].append(
                    max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1]))
                cnt[pcs[i - 1]] += 1
    tot = sum(cnt.values()) or 1
    return ({
        p: sum(d) / len(d)
        for p, d in acpl.items() if d
    }, {
        p: c / tot * 100
        for p, c in cnt.items()
    })


def cmetrics(r):
    """Castling side/timing win rates."""
    side, turn = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for *_, ct, cs, won, _, _, _, _ in r:
        if cs and won is not None:
            side[cs][won] += 1
            grp = "<=4" if ct <= 4 else "5-6" if ct <= 6 else "7-8" if ct <= 8 else "9-10" if ct <= 10 else "11-12" if ct <= 12 else "13-15" if ct <= 15 else ">15"
            turn[grp][won] += 1
    return ({
        k: v[1] / sum(v) * 100 if sum(v) else 0
        for k, v in side.items()
    }, {
        k: v[1] / sum(v) * 100 if sum(v) else 0
        for k, v in turn.items()
    })


def tmetrics(r):
    """Time-of-day ACPL and win rates."""
    acpl, wins = defaultdict(list), defaultdict(lambda: [0, 0])
    for ev, _, _, c, _, _, _, won, _, _, h, _ in r:
        if h is None: continue
        if diffs := [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if c is None or i % 2 == c
        ]:
            acpl[h].extend(diffs)
        if won is not None: wins[h][won] += 1
    return ({
        h: sum(d) / len(d)
        for h, d in acpl.items()
    }, {
        h: v[1] / sum(v) * 100 if sum(v) else 0
        for h, v in wins.items()
    })


def gmetrics(r):
    """Game-number-per-day ACPL and win rates."""
    acpl, wins = defaultdict(list), defaultdict(lambda: [0, 0])
    for ev, _, _, c, _, _, _, won, _, _, _, gn in r:
        if gn is None: continue
        if diffs := [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if c is None or i % 2 == c
        ]:
            acpl[gn].extend(diffs)
        if won is not None: wins[gn][won] += 1
    return ({
        g: sum(d) / len(d)
        for g, d in acpl.items()
    }, {
        g: v[1] / sum(v) * 100 if sum(v) else 0
        for g, v in wins.items()
    })


def eco_stats(pgns, res, users=None):
    """ECO opening stats by color."""
    ew, eb = defaultdict(lambda: {
        'a': [],
        'w': 0,
        'l': 0
    }), defaultdict(lambda: {
        'a': [],
        'w': 0,
        'l': 0
    })
    for pgn, rs in zip(pgns, res):
        if not rs: continue
        try:
            g = chess.pgn.read_game(StringIO(pgn)) if isinstance(pgn,
                                                                 str) else pgn
            if not g or not (eco := g.headers.get("ECO")): continue
            w, b = g.headers.get("White",
                                 "").lower(), g.headers.get("Black",
                                                            "").lower()
            ul = [u.lower() for u in (users or [])]
            c = chess.WHITE if w in ul else chess.BLACK if b in ul else None
            ev, *rest = rs
            diffs = [
                max(0, ev[i - 1] - ev[i] if i % 2 else ev[i] - ev[i - 1])
                for i in range(1, len(ev)) if not c or i % 2 == c
            ]
            a = sum(diffs) / len(diffs) if diffs else 0
            ed = ew if c == chess.WHITE else eb if c == chess.BLACK else None
            if ed:
                ed[eco]['a'].append(a)
                if rest[5] is not None: ed[eco]['w' if rest[5] else 'l'] += 1
        except:
            pass
    return ({
        e: {
            'a': sum(d['a']) / len(d['a']),
            'w':
            d['w'] / (d['w'] + d['l']) * 100 if d['w'] + d['l'] > 0 else 0,
            'n': d['w'] + d['l']
        }
        for e, d in ew.items() if d['a']
    }, {
        e: {
            'a': sum(d['a']) / len(d['a']),
            'w':
            d['w'] / (d['w'] + d['l']) * 100 if d['w'] + d['l'] > 0 else 0,
            'n': d['w'] + d['l']
        }
        for e, d in eb.items() if d['a']
    })


def print_stats(lbls, dsets, pgn_sets=None, res_sets=None):
    """Print comprehensive stats table."""
    pn = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
    stats = [{k: f(d) for k, f in METRICS.items()} for d in dsets]
    ps, cs, ts, gs = [pmetrics(d)
                      for d in dsets], [cmetrics(d) for d in dsets
                                        ], [tmetrics(d) for d in dsets
                                            ], [gmetrics(d) for d in dsets]
    w = 10 + 9 * len(lbls)
    print(f"\n{'Metric':<10} " + ' '.join(f"{l:>8}"
                                          for l in lbls) + f"\n{'='*w}")
    for m, l in [('acpl', 'ACPL'), ('sharpness', 'Sharp'),
                 ('closedness', 'Closed')]:
        print(f"{l:<10} " + ' '.join(f"{s[m]:>8.1f}" for s in stats))
    print(f"{'-'*w}")
    for p in range(1, 7):
        print(f"{pn[p]+' ACPL':<10} " + ' '.join(f"{x[0].get(p,0):>8.1f}"
                                                 for x in ps))
    print(f"{'-'*w}")
    for p in range(1, 7):
        print(f"{pn[p]+' %':<10} " + ' '.join(f"{x[1].get(p,0):>8.1f}"
                                              for x in ps))
    print(f"{'-'*w}")
    print(f"{'Resign%':<10} " + ' '.join(f"{s['resign_rate']:>8.1f}"
                                         for s in stats))
    print(f"{'Best%':<10} " + ' '.join(f"{s['best_move_rate']:>8.1f}"
                                       for s in stats))
    print(f"{'-'*w}")
    for side in ["K", "Q"]:
        print(f"{side+'-WR':<10} " + ' '.join(f"{x[0].get(side,0):>8.1f}"
                                              for x in cs))
    for t in ["<=4", "5-6", "7-8", "9-10", "11-12", "13-15", ">15"]:
        print(f"C {t:<5} " + ' '.join(f"{x[1].get(t,0):>8.1f}" for x in cs))
    print(f"{'-'*w}")
    if pgn_sets and res_sets:
        for i, (l, p, r) in enumerate(zip(lbls, pgn_sets, res_sets)):
            ew, eb = eco_stats(p, r, [user] if i == 0 else None)
            if ew or eb:
                print(f"\n{l} ECO:")
                if ew:
                    print("  W:")
                    for eco, d in sorted(ew.items(),
                                         key=lambda x: -x[1]['n'])[:10]:
                        print(
                            f"    {eco} n:{d['n']:>2} A:{d['a']:>5.1f} W:{d['w']:>5.1f}%"
                        )
                if eb:
                    print("  B:")
                    for eco, d in sorted(eb.items(),
                                         key=lambda x: -x[1]['n'])[:10]:
                        print(
                            f"    {eco} n:{d['n']:>2} A:{d['a']:>5.1f} W:{d['w']:>5.1f}%"
                        )
    for i, l in enumerate(lbls):
        if gs[i][0] or gs[i][1]:
            print(f"\n{l} Game# per Day:")
            for g in sorted(set(gs[i][0].keys()) | set(gs[i][1].keys())):
                print(
                    f"  {g:>2} A:{gs[i][0].get(g,0):>5.1f} W:{gs[i][1].get(g,0):>5.1f}%"
                )
    if lbls:
        print(f"\n{lbls[0]} Time of Day:")
        for h in range(24):
            a = ts[0][0].get(h, 0)
            w = ts[0][1].get(h, 0)
            print(f"  {h:02d}h A:{a:>5.1f} W:{w:>5.1f}%")
