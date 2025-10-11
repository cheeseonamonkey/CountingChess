#!/usr/bin/env python3
from collections import namedtuple
from itertools import count

PV = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 50000}
PR = {
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
     3, -14, -50, -57, -18, 13, 4, 17, 30, -3, -14, 6, -1, 40, 18)
}
PS = {
    p: (0, ) * 20 + sum(
        (((0, ) + tuple(x + PV[p] for x in PR[p][i * 8:i * 8 + 8]) + (0, ))
         for i in range(8)), ()) + (0, ) * 20
    for p in PR
}

N, E, S, W = -10, 1, 10, -1
A1, H1, A8, H8 = 91, 98, 21, 28
DR = {
    "P": (N, N + N, N + W, N + E),
    "N": (N + N + E, E + N + E, E + S + E, S + S + E, S + S + W, W + S + W,
          W + N + W, N + N + W),
    "B": (N + E, S + E, S + W, N + W),
    "R": (N, E, S, W),
    "Q": (N, E, S, W, N + E, S + E, S + W, N + W),
    "K": (N, E, S, W, N + E, S + E, S + W, N + W)
}
ML, MU = PV["K"] - 10 * PV["Q"], PV["K"] + 10 * PV["Q"]

Mv = namedtuple("Mv", "i j p")
En = namedtuple("En", "l u")


class Pos(namedtuple("Pos", "b s wc bc ep kp")):

    def gm(self):
        for i, p in enumerate(self.b):
            if not p.isupper(): continue
            for d in DR[p]:
                for j in count(i + d, d):
                    q = self.b[j]
                    if q.isspace() or q.isupper(): break
                    if p == "P":
                        if d in (N, N + N) and q != ".": break
                        if d == N + N and (i < A1 + N or self.b[i + N] != "."):
                            break
                        if d in (N + W, N + E) and q == "." and j not in (
                                self.ep, self.kp, self.kp - 1, self.kp + 1):
                            break
                        if A8 <= j <= H8:
                            for pr in "NBRQ":
                                yield Mv(i, j, pr)
                            break
                    yield Mv(i, j, "")
                    if p in "PNK" or q.islower(): break
                    if i == A1 and self.b[j + E] == "K" and self.wc[0]:
                        yield Mv(j + E, j + W, "")
                    if i == H1 and self.b[j + W] == "K" and self.wc[1]:
                        yield Mv(j + W, j + E, "")

    def rot(self, nm=False):
        return Pos(self.b[::-1].swapcase(), -self.s, self.bc, self.wc,
                   119 - self.ep if self.ep and not nm else 0,
                   119 - self.kp if self.kp and not nm else 0)

    def mv(self, m):
        i, j, pr = m
        p, q = self.b[i], self.b[j]
        put = lambda b, i, p: b[:i] + p + b[i + 1:]
        b, wc, bc, ep, kp, s = self.b, self.wc, self.bc, 0, 0, self.s + self.v(
            m)
        b = put(put(b, j, b[i]), i, ".")
        if i == A1: wc = (False, wc[1])
        if i == H1: wc = (wc[0], False)
        if j == A8: bc = (bc[0], False)
        if j == H8: bc = (False, bc[1])
        if p == "K":
            wc = (False, False)
            if abs(j - i) == 2:
                kp = (i + j) // 2
                b = put(put(b, A1 if j < i else H1, "."), kp, "R")
        if p == "P":
            if A8 <= j <= H8: b = put(b, j, pr)
            if j - i == 2 * N: ep = i + N
            if j == self.ep: b = put(b, j + S, ".")
        return Pos(b, s, wc, bc, ep, kp).rot()

    def v(self, m):
        i, j, pr = m
        p, q = self.b[i], self.b[j]
        s = PS[p][j] - PS[p][i]
        if q.islower(): s += PS[q.upper()][119 - j]
        if abs(j - self.kp) < 2: s += PS["K"][119 - j]
        if p == "K" and abs(i - j) == 2:
            s += PS["R"][(i + j) // 2] - PS["R"][A1 if j < i else H1]
        if p == "P":
            if A8 <= j <= H8: s += PS[pr][j] - PS["P"][j]
            if j == self.ep: s += PS["P"][119 - (j + S)]
        return s


class _S:

    def __init__(self):
        self.ts, self.tm = {}, {}

    def bd(self, pos, g, d, cn=True):
        d = max(d, 0)
        if pos.s <= -ML: return -MU
        e = self.ts.get((pos, d, cn), En(-MU, MU))
        if e.l >= g: return e.l
        if e.u < g: return e.u

        def mvs():
            if d == 0:
                yield None, pos.s
                return
            k = self.tm.get(pos)
            vl = 40 - d * 140
            if k and pos.v(k) >= vl:
                yield k, -self.bd(pos.mv(k), 1 - g, d - 1)
            for v, m in sorted(((pos.v(m), m) for m in pos.gm()),
                               reverse=True):
                if v < vl: break
                if d <= 1 and pos.s + v < g:
                    yield m, pos.s + v if v < ML else MU
                    break
                yield m, -self.bd(pos.mv(m), 1 - g, d - 1)

        bs = -MU
        for m, sc in mvs():
            bs = max(bs, sc)
            if bs >= g:
                if m is not None: self.tm[pos] = m
                break
        if bs >= g: self.ts[pos, d, cn] = En(bs, e.u)
        if bs < g: self.ts[pos, d, cn] = En(e.l, bs)
        return bs

    def sr(self, pos, d):
        self.ts.clear()
        l, u, g = -ML, ML, 0
        for _ in range(d):
            while l < u - 15:
                sc = self.bd(pos, g, d, cn=False)
                l, u = (sc, u) if sc >= g else (l, sc)
                g = (l + u + 1) // 2
        return g, self.tm.get(pos)


def _fp(fen):
    p = fen.split()
    bf, tm, cs, ep = p[0], p[1], p[2], p[3]
    b = "         \n         \n"
    for r in bf.split('/'):
        b += " " + "".join("." * int(c) if c.isdigit() else c
                           for c in r) + "\n"
    b += "         \n         \n"
    if tm == 'b': b = b[::-1].swapcase()
    wc = ('Q' in cs, 'K' in cs) if tm == 'w' else ('q' in cs, 'k' in cs)
    bc = ('q' in cs, 'k' in cs) if tm == 'w' else ('Q' in cs, 'K' in cs)
    e = 0
    if ep != '-':
        f, r = ord(ep[0]) - ord('a'), int(ep[1]) - 1
        e = A1 + f - 10 * r
        e = 119 - e if tm == 'b' else e
    s = sum(PS[p][i] for i, p in enumerate(b) if p.isupper()) - sum(
        PS[p.upper()][119 - i] for i, p in enumerate(b) if p.islower())
    return Pos(b, s, wc, bc, e, 0)


def evaluate_fen(fen, depth=2):
    pos = _fp(fen)
    sr = _S()
    sc, m = sr.sr(pos, depth)
    if m is None: return sc, None
    i, j, pr = m.i, m.j, m.p
    if fen.split()[1] == 'b': i, j = 119 - i, 119 - j

    def r(ix):
        rk, fl = divmod(ix - A1, 10)
        return chr(fl + ord('a')) + str(-rk + 1)

    return sc, r(i) + r(j) + pr.lower()
