import os
from collections import defaultdict
from pathlib import Path
import gzip
import pickle
import hashlib
import heapq


class DiskMemCache:
    """
    Persistent cache for Stockfish analysis results, with LFU-based pruning.
    """

    def __init__(self,
                 cache_file="position_cache.pkl.gz",
                 prune_threshold=5.5,
                 check_interval=1999,
                 max_cache_size=250_000,
                 periodic_save=True):
        self.cache_file = Path(cache_file)
        self.cache = {}
        self.freq = defaultdict(int)
        self.hits = self.misses = self.lookup_count = 0
        self.check_interval = check_interval
        self.prune_threshold = prune_threshold
        self.max_cache_size = max_cache_size
        self.periodic_save = periodic_save

    # ---------------- Core API ----------------

    def get(self, fen, depth):
        k = self._key(fen, depth)
        v = self.cache.get(k)
        if v is not None:
            self.hits += 1
            self.freq[k] += 1
        else:
            self.misses += 1
        self.lookup_count += 1
        self._maybe_prune()
        return v

    def get_many(self, positions):
        hits = {}
        misses = []

        append_miss = misses.append
        cache_get = self.cache.get
        freq_get = self.freq.get

        for fen, depth in positions:
            k = self._key(fen, depth)
            v = cache_get(k)
            if v is not None:
                hits[(fen, depth)] = v
                self.hits += 1
                self.freq[k] += 1
            else:
                append_miss((fen, depth, k))
                self.misses += 1
            self.lookup_count += 1

        # Use heapq.nlargest instead of full sort
        miss_list = [(fen, depth) for fen, depth, k in heapq.nlargest(
            len(misses), misses, key=lambda x: freq_get(x[2], 0))]

        self._maybe_prune()
        return hits, miss_list

    def put(self, fen, depth, value):
        k = self._key(fen, depth)
        self.cache[k] = value
        self.freq[k] += 1

    def put_many(self, results):
        cache_set = self.cache.__setitem__
        freq = self.freq
        for fen, depth, value in results:
            k = self._key(fen, depth)
            cache_set(k, value)
            freq[k] += 1

    # ---------------- Persistence ----------------

    def load(self):
        if not self.cache_file.exists():
            return
        try:
            print(f"Decompressing cache from {self.cache_file}...")
            with gzip.open(self.cache_file, "rb") as f:
                data = pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            self.cache = {}
            self.freq = defaultdict(int)
            return

        if isinstance(data, dict) and 'cache' in data:
            self.cache = data['cache']
            self.freq = defaultdict(int, data.get('freq', {}))
        else:
            self.cache = data
            self.freq = defaultdict(int)

        for k in self.cache.keys():
            self.freq.setdefault(k, 1)
        print(f"Loaded {len(self.cache)} positions from cache.")

    def save(self):
        if not self.cache:
            return

        if len(self.cache) > self.max_cache_size:
            heap = []
            heap_append = heapq.heappush
            heap_pop = heapq.heappushpop
            freq_get = self.freq.get
            for k in self.cache.keys():
                f = freq_get(k, 1)
                if len(heap) < self.max_cache_size:
                    heap_append(heap, (f, k))
                else:
                    heap_pop(heap, (f, k))
            top_keys = {k for _, k in heap}
            trimmed_cache = {k: self.cache[k] for k in top_keys}
            trimmed_freq = {k: self.freq[k] for k in top_keys}
        else:
            trimmed_cache = self.cache
            trimmed_freq = dict(self.freq)

        data = {'cache': trimmed_cache, 'freq': trimmed_freq}
        tmp_path = self.cache_file.with_suffix(".tmp")
        try:
            with gzip.open(tmp_path, "wb") as f:
                pickle.dump(data, f)
            os.replace(tmp_path, self.cache_file)
        finally:
            tmp_path.unlink(missing_ok=True)

        self.cache = trimmed_cache
        self.freq = defaultdict(int, trimmed_freq)
        self._reset_stats()

    # ---------------- Internals ----------------

    def _key(self, fen, depth):
        return hashlib.md5(f"{fen}:{depth}".encode()).hexdigest()

    def _hit_rate(self):
        t = self.hits + self.misses
        return (100 * self.hits / t) if t else 0

    def _maybe_prune(self):
        if self.lookup_count % self.check_interval != 0:
            return
        hr = self._hit_rate()
        if hr < self.prune_threshold or self.periodic_save:
            self.save()

    def _reset_stats(self):
        self.hits = self.misses = self.lookup_count = 0
