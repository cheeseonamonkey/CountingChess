#!/usr/bin/env python3
"""Minimal chess position evaluator from FEN notation"""

from functools import lru_cache

# Piece values and piece-square tables
piece = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 60000}
pst = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0, 78, 83, 86, 73, 102, 82, 85, 90, 7, 29, 21,
          44, 40, 31, 44, 7, -17, 16, -2, 15, 14, 0, 15, -13, -26, 3, 10, 9, 6,
          1, 0, -23, -22, 9, 5, -11, -10, -2, 3, -19, -31, 8, -7, -37, -36,
          -14, 3, -31, 0, 0, 0, 0, 0, 0, 0, 0),
    'N': (-66, -53, -75, -75, -10, -55, -58, -70, -3, -6, 100, -36, 4, 62, -4,
          -14, 10, 67, 1, 74, 73, 27, 62, -2, 24, 24, 45, 37, 33, 41, 25, 17,
          -1, 5, 31, 21, 22, 35, 2, 0, -18, 10, 13, 22, 18, 15, 11, -14, -23,
          -15, 2, 0, 2, 0, -23, -20, -74, -23, -26, -24, -19, -35, -22, -69),
    'B': (-59, -78, -82, -76, -23, -107, -37, -50, -11, 20, 35, -42, -39, 31,
          2, -22, -9, 39, -32, 41, 52, -10, 28, -14, 25, 17, 20, 34, 26, 25,
          15, 10, 13, 10, 17, 23, 17, 16, 0, 7, 14, 25, 24, 15, 8, 25, 20, 15,
          19, 20, 11, 6, 7, 6, 20, 16, -7, 2, -15, -12, -14, -15, -10, -10),
    'R':
    (35, 29, 33, 4, 37, 33, 56, 50, 55, 29, 56, 67, 55, 62, 34, 60, 19, 35, 28,
     33, 45, 27, 25, 15, 0, 5, 16, 13, 18, -4, -9, -6, -28, -35, -16, -21, -13,
     -29, -46, -30, -42, -28, -42, -25, -25, -35, -26, -46, -53, -38, -31, -26,
     -29, -43, -44, -53, -30, -24, -18, 5, -2, -18, -31, -32),
    'Q':
    (6, 1, -8, -104, 69, 24, 88, 26, 14, 32, 60, -10, 20, 76, 57, 24, -2, 43,
     32, 60, 72, 63, 43, 2, 1, -16, 22, 17, 25, 20, -13, -6, -14, -15, -2, -5,
     -1, -10, -20, -22, -30, -6, -13, -11, -16, -11, -16, -27, -36, -18, 0,
     -19, -15, -15, -21, -38, -39, -30, -31, -13, -31, -36, -34, -42),
    'K':
    (4, 54, 47, -99, -99, 60, 83, -62, -32, 10, 55, 56, 56, 55, 10, 3, -62, 12,
     -57, 44, -67, 28, 37, -31, -55, 50, 11, -4, -19, 13, 0, -49, -55, -43,
     -52, -28, -51, -47, -8, -50, -47, -42, -43, -79, -64, -32, -29, -32, -4,
     3, -14, -50, -57, -18, 13, 4, 17, 30, -3, -14, 6, -1, 40, 18),
}

# Pad tables and merge piece values
for k, t in pst.items():
    padded = []
    for i in range(8):
        padded.extend([0] + [x + piece[k] for x in t[i * 8:(i + 1) * 8]] + [0])
    pst[k] = (0, ) * 20 + tuple(padded) + (0, ) * 20


@lru_cache(maxsize=512)
def fen_to_board(fen):
    """Convert FEN to 120-char board representation"""
    rows = [
        ' ' + ''.join('.' * int(c) if c.isdigit() else c for c in rank)
        for rank in fen.split()[0].split('/')
    ]
    return "         \n         \n" + '\n'.join(
        rows) + "\n         \n         \n"


@lru_cache(maxsize=8224 * 4)
def evaluate_fen(fen, result=None):
    """
    Evaluate position from FEN, returns score from white's perspective.
    Optional:
      - result: '1-0', '0-1', '1/2-1/2' to slightly bias evaluation
    """
    b = fen_to_board(fen)

    # Base evaluation from piece-square tables
    eval_base = sum(pst[p][i] if p.isupper() else -pst[p.upper()][119 - i]
                    for i, p in enumerate(b) if p.isalpha())

    # Apply result bias only for decisive games
    if result in ('1-0', '0-1'):
        # Material ratio as a stage factor
        mat_w = sum(piece.get(p.upper(), 0) for p in b if p.isupper())
        mat_b = sum(piece.get(p.upper(), 0) for p in b if p.islower())
        stage_factor = min((mat_w + mat_b) / 2000, 1)
        bias = 0.075 * stage_factor
        if result == '1-0':
            eval_base *= 1 + bias
        elif result == '0-1':
            eval_base *= 1 - bias

    return eval_base


# Pre-compute direction sets and center squares
_DIRS = {
    'N': (-21, -19, -12, -8, 8, 12, 19, 21),
    'B': (-11, -9, 9, 11),
    'R': (-10, -1, 1, 10),
    'Q': (-11, -10, -9, -1, 1, 9, 10, 11),
    'K': (-11, -10, -9, -1, 1, 9, 10, 11)
}
_CTR = frozenset({44, 45, 54, 55})
_SLIDES = frozenset('BRQ')
_W_UPPER = frozenset('PRNBQK')
_B_LOWER = frozenset('prnbqk')


@lru_cache(maxsize=8224 * 4)
def calculate_metrics(fen):
    """Calculate positional metrics from FEN"""
    b = fen_to_board(fen)

    # Openness - fewer pawns + open files
    pawns = b.count('P') + b.count('p')
    files = sum(
        all(b[20 + f + 10 * r] not in 'Pp' for r in range(8))
        for f in range(1, 9))

    # Development - minor pieces off starting squares
    dev = sum(b[i] not in 'NB' for i in (92, 93, 96, 97)) - \
          sum(b[i] not in 'nb' for i in (22, 23, 26, 27))

    # Mobility - single pass calculation
    wm = bm = 0
    wk = bk = None
    mat_w = mat_b = 0
    adv = 0

    for i, p in enumerate(b):
        if p == ' ' or p == '\n': continue

        pu = p.upper()

        # Track kings
        if p == 'K': wk = i
        elif p == 'k': bk = i

        # Material
        if p.isupper():
            mat_w += piece.get(pu, 0)
            if i < 60 and p != '.': adv += 3
        elif p.islower():
            mat_b += piece.get(pu, 0)
            if i > 60: adv += 3

        # Mobility
        if p == 'P':
            wm += (b[i + 10] == '.') + (b[i + 9] in _B_LOWER) + (b[i + 11]
                                                                 in _B_LOWER)
        elif p == 'p':
            bm += (b[i - 10] == '.') + (b[i - 9] in _W_UPPER) + (b[i - 11]
                                                                 in _W_UPPER)
        elif pu in _DIRS:
            for d in _DIRS[pu]:
                pos = i + d
                if p.isupper():
                    if b[pos] not in _W_UPPER and b[pos] not in ' \n':
                        wm += 1
                        if pu in _SLIDES:
                            pos += d
                            while b[pos] == '.':
                                wm += 1
                                pos += d
                else:
                    if b[pos] not in _B_LOWER and b[pos] not in ' \n':
                        bm += 1
                        if pu in _SLIDES:
                            pos += d
                            while b[pos] == '.':
                                bm += 1
                                pos += d

    # Sharpness
    sharp = (abs(wk - 95) + abs(bk - 25)) * 10 + abs(mat_w - mat_b) // 20 + adv

    # Center control - optimized single pass
    wc = bc = 0
    for sq in _CTR:
        if b[sq].isupper(): wc += 2
        elif b[sq].islower(): bc += 2

    for i, p in enumerate(b):
        if p == 'P':
            wc += ((i + 9) in _CTR) + ((i + 11) in _CTR)
        elif p == 'p':
            bc += ((i - 9) in _CTR) + ((i - 11) in _CTR)
        elif p.upper() in _DIRS:
            for d in _DIRS[p.upper()]:
                if (i + d) in _CTR:
                    wc += p.isupper()
                    bc += p.islower()

    # King safety
    ws = sum(b[wk + d] == 'P' for d in (-11, -10, -9, 9, 10, 11))
    bs = sum(b[bk + d] == 'p' for d in (-11, -10, -9, 9, 10, 11))
    ks = (ws - bs) * 10 + \
         (sum(b[bk + d].isupper() for d in range(-22, 23) if 0 <= bk + d < len(b)) -
          sum(b[wk + d].islower() for d in range(-22, 23) if 0 <= wk + d < len(b))) * 5

    # Pawn structure
    wp_st = bp_st = 0
    for f in range(1, 9):
        wp_col = sum(b[20 + f + 10 * r] == 'P' for r in range(8))
        bp_col = sum(b[20 + f + 10 * r] == 'p' for r in range(8))

        if wp_col > 1: wp_st -= 15
        if bp_col > 1: bp_st -= 15

        if wp_col:
            has_adj = (f > 1 and any(b[19 + f + 10 * r] == 'P' for r in range(8))) or \
                      (f < 8 and any(b[21 + f + 10 * r] == 'P' for r in range(8)))
            if not has_adj: wp_st -= 10
        if bp_col:
            has_adj = (f > 1 and any(b[19 + f + 10 * r] == 'p' for r in range(8))) or \
                      (f < 8 and any(b[21 + f + 10 * r] == 'p' for r in range(8)))
            if not has_adj: bp_st -= 10

    # Space
    ws = sum(
        any(b[i + d] == 'P' for d in (-9, -11)) for i in range(20, 60)
        if b[i] == '.')
    bs = sum(
        any(b[i + d] == 'p' for d in (9, 11)) for i in range(60, 100)
        if b[i] == '.')

    return {
        'openness': (16 - pawns) * 4 + files * 8,
        'development': dev,
        'mobility': wm - bm,
        'sharpness': sharp,
        'center_control': wc - bc,
        'king_safety': ks,
        'pawn_structure': wp_st - bp_st,
        'space': ws - bs
    }
