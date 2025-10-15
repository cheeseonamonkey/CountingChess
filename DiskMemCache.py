import gzip, pickle, hashlib, heapq, time
from collections import defaultdict, OrderedDict
from pathlib import Path


class DiskMemCache:
    """Persistent LFU cache (frequency-based) for Stockfish or similar analysis."""

    def __init__(self,
                 cache_file="position_cache.pkl.gz",
                 prune_threshold=6.0,
                 check_interval=499,
                 max_cache_size=50_000,
                 periodic_save=True,
                 key_cache_size=9_000):
        self.cache_file = Path(cache_file)
        self.cache, self.freq = {}, defaultdict(int)
        self.hits = self.misses = self.lookup_count = 0
        self.prune_threshold = float(prune_threshold)
        self.check_interval = max(1, int(check_interval))
        self.max_cache_size = int(max_cache_size)
        self.periodic_save = periodic_save
        self._key_cache = OrderedDict()
        self._key_cache_size = max(1000, key_cache_size)
        self._soft_cap_mult = 1.2
        self._freq_cap = 1_000_000_000
        self._last_prune_time = None

    # ---------- Core API ----------

    def get(self, fen, depth):
        k = self._key(fen, depth)
        v = self.cache.get(k)
        if v is not None:
            self.hits += 1
            self.freq[k] = min(self._freq_cap, self.freq.get(k, 0) + 1)
        else:
            self.misses += 1
        self.lookup_count += 1
        self._maybe_prune()
        return v

    def get_many(self, positions):
        hits, misses = {}, []
        fget, cache, freq, cap = self.freq.get, self.cache, self.freq, self._freq_cap
        for fen, depth in positions:
            k = self._key(fen, depth)
            v = cache.get(k)
            if v is not None:
                hits[(fen, depth)] = v
                freq[k] = min(cap, fget(k, 0) + 1)
                self.hits += 1
            else:
                misses.append((fen, depth))
                self.misses += 1
            self.lookup_count += 1
        self._maybe_prune()
        return hits, misses

    def put(self, fen, depth, value):
        k = self._key(fen, depth)
        self.cache[k] = value
        self.freq[k] = min(self._freq_cap, self.freq.get(k, 0) + 1)
        if len(self.cache) > self.max_cache_size * self._soft_cap_mult:
            self._prune_in_memory()

    def put_many(self, results):
        freq, cache, cap = self.freq, self.cache, self._freq_cap
        for fen, depth, value in results:
            k = self._key(fen, depth)
            cache[k] = value
            freq[k] = min(cap, freq.get(k, 0) + 1)
        if len(cache) > self.max_cache_size * self._soft_cap_mult:
            self._prune_in_memory()

    # ---------- Persistence ----------

    def load(self):
        if not self.cache_file.exists():
            print(f"  ! cache file {self.cache_file} does not exist")
            return
        try:
            with gzip.open(self.cache_file, "rb") as f:
                data = pickle.load(f)
        except Exception as e:
            print(f"  ! failed to load cache: {e}")
            self.cache, self.freq = {}, defaultdict(int)
            return
        if isinstance(data, dict) and 'cache' in data:
            self.cache = data.get('cache', {})
            self.freq = defaultdict(int, data.get('freq', {}))
        else:
            self.cache, self.freq = data, defaultdict(int)
        for k in self.cache:
            self.freq.setdefault(k, 1)
        print(f"  ✓ loaded {len(self.cache)} positions from {self.cache_file}")

    def save(self):
        if not self.cache:
            return
        n = len(self.cache)
        print(f"  - saving: before trim {n} positions (max {self.max_cache_size})")
        if n <= self.max_cache_size:
            top_keys = set(self.cache)
        else:
            items = ((self.freq.get(k, 1), k) for k in self.cache)
            top_keys = {
                k
                for _, k in heapq.nlargest(
                    self.max_cache_size, items, key=lambda x: x[0])
            }
        trimmed_cache = {k: self.cache[k] for k in top_keys}
        trimmed_freq = {k: self.freq.get(k, 1) for k in top_keys}
        m = len(trimmed_cache)
        data = {'cache': trimmed_cache, 'freq': trimmed_freq}
        tmp = self.cache_file.with_suffix('.tmp')
        try:
            with gzip.open(tmp, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(self.cache_file)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        self.cache, self.freq = trimmed_cache, defaultdict(int, trimmed_freq)
        self._reset_stats()
        self._last_prune_time = time.time()
        print(f"  ✓ saved {m} positions to {self.cache_file} (trimmed from {n})")

    # ---------- Internals ----------

    def _key(self, fen, depth):
        ck = (fen, int(depth))
        kc = self._key_cache
        if ck in kc:
            kc.move_to_end(ck)
            return kc[ck]
        m = hashlib.md5()
        m.update(fen.encode('utf-8'))
        m.update(b':')
        m.update(str(depth).encode('ascii'))
        key = m.hexdigest()
        kc[ck] = key
        if len(kc) > self._key_cache_size:
            kc.popitem(last=False)
        return key

    def _hit_rate(self):
        t = self.hits + self.misses
        return 100 * self.hits / t if t else 0

    def _maybe_prune(self):
        csize = len(self.cache)
        if csize > self.max_cache_size * self._soft_cap_mult:
            self._prune_in_memory()
            if self.periodic_save:
                self.save()
            return
        if self.lookup_count % self.check_interval != 0:
            return
        if self._hit_rate() < self.prune_threshold or self.periodic_save:
            self.save()

    def _prune_in_memory(self):
        n = len(self.cache)
        if n <= self.max_cache_size:
            return
        print(f"  - pruning in-memory: before {n} -> max {self.max_cache_size}")
        items = ((self.freq.get(k, 1), k) for k in self.cache)
        keep = {
            k
            for _, k in heapq.nlargest(
                self.max_cache_size, items, key=lambda x: x[0])
        }
        for k in list(self.cache.keys()):
            if k not in keep:
                self.cache.pop(k, None)
                self.freq.pop(k, None)
        m = len(self.cache)
        print(f"  ✓ pruned in-memory to {m} positions")
        self._last_prune_time = time.time()

    def force_prune(self):
        return self._prune_in_memory()

    def _reset_stats(self):
        self.hits = self.misses = self.lookup_count = 0

    def stats(self):
        return dict(cache_size=len(self.cache),
                    freq_map_size=len(self.freq),
                    hits=self.hits,
                    misses=self.misses,
                    hit_rate=self._hit_rate(),
                    last_prune=self._last_prune_time)