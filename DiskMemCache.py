from collections import defaultdict
from pathlib import Path
import gzip
import pickle
import hashlib
import heapq


class DiskMemCache:
    """
    Persistent cache for Stockfish analysis results, with smarter pruning
    based on combined frequency + recency (LFU + LRU).
    """

    def __init__(self,
                 cache_file="position_cache.pkl.gz",
                 prune_threshold=10.0,
                 check_interval=1999,
                 max_cache_size=100_000):
        """
        :param cache_file: Path to gzip-pickle file
        :param prune_threshold: Hit rate below which pruning is triggered
        :param check_interval: Number of lookups before checking for pruning
        :param max_cache_size: Maximum number of positions to keep on save
        """
        self.cache_file = Path(cache_file)
        self.cache = {}
        self.freq = defaultdict(int)
        self.last_access = {}  # For LRU component
        self.hits = 0
        self.misses = 0
        self.lookup_count = 0
        self.check_interval = check_interval
        self.prune_threshold = prune_threshold
        self.max_cache_size = max_cache_size

    # ---------------- Core API ----------------

    def get(self, fen, depth):
        k = self._key(fen, depth)
        value = self.cache.get(k)
        if value is not None:
            self.hits += 1
            self.freq[k] += 1
            self.last_access[k] = self.lookup_count
        else:
            self.misses += 1
        self.lookup_count += 1
        self._maybe_prune()
        return value

    def put(self, fen, depth, value):
        k = self._key(fen, depth)
        self.cache[k] = value
        self.freq[k] += 1
        self.last_access[k] = self.lookup_count

    # ---------------- Persistence ----------------

    def load(self):
        if not self.cache_file.exists():
            return
        size_mb = self.cache_file.stat().st_size / 1024 / 1024
        print(f"Loading cache from {self.cache_file} ({size_mb:.1f} MB)...")
        with gzip.open(self.cache_file, "rb") as f:
            self.cache = pickle.load(f)
        # Initialize last_access for loaded items
        for k in self.cache.keys():
            self.last_access[k] = 0
            self.freq[k] = self.freq.get(k, 1)
        print(f"  Loaded {len(self.cache):,} positions\n")

    def save(self):
        if not self.cache:
            print("Nothing to save.")
            return

        # Heap-based pruning: top N positions by score
        heap = []
        for k, v in self.cache.items():
            age = self.lookup_count - self.last_access.get(k, 0)
            score = self.freq.get(k, 1) / (1 + age)
            if len(heap) < self.max_cache_size:
                heapq.heappush(heap, (score, k))
            else:
                heapq.heappushpop(heap, (score, k))

        top_keys = {k for _, k in heap}
        trimmed_cache = {k: self.cache[k] for k in top_keys}

        kept = len(trimmed_cache)
        total = len(self.cache)
        print(
            f"\nPruning cache: keeping top {kept:,} of {total:,} positions...")
        with gzip.open(self.cache_file, "wb") as f:
            pickle.dump(trimmed_cache, f)

        size_mb = self.cache_file.stat().st_size / 1024 / 1024
        hit_rate = self._hit_rate()
        print(f"  Saved {kept:,} positions ({size_mb:.1f} MB)")
        print(f"  Cache stats: {self.hits:,} hits, {self.misses:,} misses "
              f"({hit_rate:.1f}% hit rate)")

        self.cache = trimmed_cache
        # Reset stats for next round
        self._reset_stats()

    # ---------------- Internals ----------------

    def _key(self, fen, depth):
        return hashlib.md5(f"{fen}:{depth}".encode()).hexdigest()

    def _hit_rate(self):
        total = self.hits + self.misses
        return (100 * self.hits / total) if total else 0

    def _maybe_prune(self):
        if self.lookup_count % self.check_interval != 0:
            return
        if self._hit_rate() < self.prune_threshold:
            print(
                f"\nHit rate low ({self._hit_rate():.1f}%), pruning & saving..."
            )
            self.save()

    def _reset_stats(self):
        self.hits = self.misses = self.lookup_count = 0
