"""Minimal chess position evaluator from FEN notation with enhanced metrics"""

from functools import lru_cache
import chess

# Piece values (centipawns)
PIECE_VALUES = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 55000}

# Piece-square tables (expanded for better evaluation)
PST = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0, 78, 83, 86, 73, 102, 82, 85, 90, 7, 29, 21, 44, 40, 31, 44, 7, -17, 16, -2, 15, 14, 0, 15, -13, -26, 3, 10, 9, 6, 1, 0, -23, -22, 9, 5, -11, -10, -2, 3, -19, -31, 8, -7, -37, -36, -14, 3, -31, 0, 0, 0, 0, 0, 0, 0, 0),
    'N': (-66, -53, -75, -75, -10, -55, -58, -70, -3, -6, 100, -36, 4, 62, -4, -14, 10, 67, 1, 74, 73, 27, 62, -2, 24, 24, 45, 37, 33, 41, 25, 17, -1, 5, 31, 21, 22, 35, 2, 0, -18, 10, 13, 22, 18, 15, 11, -14, -23, -15, 2, 0, 2, 0, -23, -20, -74, -23, -26, -24, -19, -35, -22, -69),
    'B': (-59, -78, -82, -76, -23, -107, -37, -50, -11, 20, 35, -42, -39, 31, 2, -22, -9, 39, -32, 41, 52, -10, 28, -14, 25, 17, 20, 34, 26, 25, 15, 10, 13, 10, 17, 23, 17, 16, 0, 7, 14, 25, 24, 15, 8, 25, 20, 15, 19, 20, 11, 6, 7, 6, 20, 16, -7, 2, -15, -12, -14, -15, -10, -10),
    'R': (35, 29, 33, 4, 37, 33, 56, 50, 55, 29, 56, 67, 55, 62, 34, 60, 19, 35, 28, 33, 45, 27, 25, 15, 0, 5, 16, 13, 18, -4, -9, -6, -28, -35, -16, -21, -13, -29, -46, -30, -42, -28, -42, -25, -25, -35, -26, -46, -53, -38, -31, -26, -29, -43, -44, -53, -30, -24, -18, 5, -2, -18, -31, -32),
    'Q': (6, 1, -8, -104, 69, 24, 88, 26, 14, 32, 60, -10, 20, 76, 57, 24, -2, 43, 32, 60, 72, 63, 43, 2, 1, -16, 22, 17, 25, 20, -13, -6, -14, -15, -2, -5, -1, -10, -20, -22, -30, -6, -13, -11, -16, -11, -16, -27, -36, -18, 0, -19, -15, -15, -21, -38, -39, -30, -31, -13, -31, -36, -34, -42),
    'K': (4, 54, 47, -99, -99, 60, 83, -62, -32, 10, 55, 56, 56, 55, 10, 3, -62, 12, -57, 44, -67, 28, 37, -31, -55, 50, 11, -4, -19, 13, 0, -49, -55, -43, -52, -28, -51, -47, -8, -50, -47, -42, -43, -79, -64, -32, -29, -32, -4, 3, -14, -50, -57, -18, 13, 4, 17, 30, -3, -14, 6, -1, 40, 18),
}

# Pad tables for board indexing
for k, t in PST.items():
    padded = []
    for i in range(8):
        padded.extend([0] + [x + PIECE_VALUES[k] for x in t[i * 8:(i + 1) * 8]] + [0])
    PST[k] = (0,) * 20 + tuple(padded) + (0,) * 20

# Movement directions for pieces
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

@lru_cache(maxsize=5120)
def fen_to_board(fen):
    """Convert FEN to a string representation of the board."""
    rows = [' ' + ''.join('.' * int(c) if c.isdigit() else c for c in r) for r in fen.split()[0].split('/')]
    return "         \n         \n" + '\n'.join(rows) + "\n         \n         \n"

@lru_cache(maxsize=4444)
def evaluate_fen(fen, result=None, turn_4=None):
    """Evaluate a FEN position, adjusting for game result and turn bias."""
    b = fen_to_board(fen)
    eval_base = sum(PST[p][i] if p.isupper() else -PST[p.upper()][119 - i] for i, p in enumerate(b) if p.isalpha())

    # Adjust evaluation based on game result
    if result in ('1-0', '0-1'):
        mat_w = sum(PIECE_VALUES.get(p.upper(), 0) for p in b if p.isupper())
        mat_b = sum(PIECE_VALUES.get(p.upper(), 0) for p in b if p.islower())
        stage = min((mat_w + mat_b) / 2000, 1)
        bias = 0.05 * stage
        eval_base *= (1 + bias) if result == '1-0' else (1 - bias)

    # Apply turn bias
    if turn_4:
        eval_base += turn_4 * 0.06
    return eval_base

@lru_cache(maxsize=8224 * 4)
def calculate_metrics(fen):
    """Calculate advanced positional metrics for a given FEN."""
    b = fen_to_board(fen)
    pawns = b.count('P') + b.count('p')
    files = sum(all(b[20 + f + 10 * r] not in 'Pp' for r in range(8)) for f in range(1, 9))
    dev = sum(b[i] != 'NBR' for i in (92, 93, 96, 97)) - sum(b[i] != 'nbr' for i in (22, 23, 26, 27))
    wm = bm = adv = 0
    wk = bk = None
    mat_w = mat_b = 0
    piece_activity = {'P': 0, 'N': 0, 'B': 0, 'R': 0, 'Q': 0, 'K': 0}

    for i, p in enumerate(b):
        if p in (' ', '\n'):
            continue
        pu = p.upper()
        if p == 'K':
            wk = i
        elif p == 'k':
            bk = i
        if p.isupper():
            mat_w += PIECE_VALUES.get(pu, 0)
            adv += (3 if i < 60 and p != '.' else 0)
        elif p.islower():
            mat_b += PIECE_VALUES.get(pu, 0)
            adv += (3 if i > 60 else 0)
        if p == 'P':
            wm += (b[i + 10] == '.') + (b[i + 9] in _B_LOWER) + (b[i + 11] in _B_LOWER)
        elif p == 'p':
            bm += (b[i - 10] == '.') + (b[i - 9] in _W_UPPER) + (b[i - 11] in _W_UPPER)
        elif pu in _DIRS:
            for d in _DIRS[pu]:
                pos = i + d
                if p.isupper():
                    if b[pos] not in _W_UPPER and b[pos] not in ' \n':
                        wm += 1
                        piece_activity[pu] += 1
                    if pu in _SLIDES:
                        while b[pos] == '.':
                            wm += 1
                            piece_activity[pu] += 0.5
                            pos += d
                else:
                    if b[pos] not in _B_LOWER and b[pos] not in ' \n':
                        bm += 1
                        piece_activity[pu] += 1
                    if pu in _SLIDES:
                        while b[pos] == '.':
                            bm += 1
                            piece_activity[pu] += 0.5
                            pos += d

    # Additional metrics
    sharp = (abs(wk - 95) + abs(bk - 25)) * 10 + abs(mat_w - mat_b) // 20 + adv
    wc = bc = sum(2 if b[s].isupper() else -2 if b[s].islower() else 0 for s in _CTR)
    ws = bs = 0
    for f in range(1, 9):
        wp_col = sum(b[20 + f + 10 * r] == 'P' for r in range(8))
        bp_col = sum(b[20 + f + 10 * r] == 'p' for r in range(8))
        if wp_col > 1:
            ws -= 15
        if bp_col > 1:
            bs -= 15

    # King safety: check for pawn shield
    king_safety_w = king_safety_b = 0
    if wk:
        for offset in (-11, -10, -9):
            if b[wk + offset] == 'P':
                king_safety_w += 20
    if bk:
        for offset in (9, 10, 11):
            if b[bk + offset] == 'p':
                king_safety_b += 20

    # Space control
    space_w = sum(1 for i in range(60, 100) if b[i].isupper())
    space_b = sum(1 for i in range(20, 60) if b[i].islower())

    # Piece coordination: bonus for knights and bishops working together
    piece_coord = 0
    if b.count('N') >= 2:
        piece_coord += 10
    if b.count('B') >= 2:
        piece_coord += 10

    return {
        'openness': (16 - pawns) * 4 + files * 8,
        'development': dev,
        'mobility': wm - bm,
        'sharpness': sharp,
        'center_control': wc - bc,
        'king_safety': king_safety_w - king_safety_b,
        'pawn_structure': ws - bs,
        'space': space_w - space_b,
        'piece_coordination': piece_coord,
        'piece_activity': piece_activity
    }