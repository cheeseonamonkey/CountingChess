


from collections import defaultdict
from pathlib import Path
import gzip
import pickle
import hashlib
import heapq


class DiskMemCache:
    """
    Persistent cache for Stockfish analysis results, with smart pruning
    based on frequency (LFU). Values are immutable and never expire.
    """

    def __init__(self,
                 cache_file="position_cache.pkl.gz",
                 prune_threshold=8,
                 check_interval=6999,
                 max_cache_size=275_000,
                 periodic_save=True):
        """
        :param cache_file: Path to gzip-pickle file
        :param prune_threshold: Hit rate below which pruning is triggered
        :param check_interval: Number of lookups before checking for pruning
        :param max_cache_size: Maximum number of positions to keep on save
        :param periodic_save: Save at check_interval even if hit rate is good
        """
        self.cache_file = Path(cache_file)
        self.cache = {}
        self.freq = defaultdict(int)
        self.hits = 0
        self.misses = 0
        self.lookup_count = 0
        self.check_interval = check_interval
        self.prune_threshold = prune_threshold
        self.max_cache_size = max_cache_size
        self.periodic_save = periodic_save

    # ---------------- Core API ----------------

    def get(self, fen, depth):
        k = self._key(fen, depth)
        value = self.cache.get(k)
        if value is not None:
            self.hits += 1
            self.freq[k] += 1
        else:
            self.misses += 1
        self.lookup_count += 1
        self._maybe_prune()
        return value

    def get_many(self, positions):
        """
        Batch lookup for multiple positions.

        :param positions: List of (fen, depth) tuples
        :return: Tuple of (hits_dict, miss_list) where:
                 - hits_dict maps (fen, depth) -> cached_value
                 - miss_list contains (fen, depth) tuples sorted by frequency
        """
        hits = {}
        misses = []

        for fen, depth in positions:
            k = self._key(fen, depth)
            value = self.cache.get(k)

            if value is not None:
                hits[(fen, depth)] = value
                self.hits += 1
                self.freq[k] += 1
            else:
                misses.append((fen, depth, k))
                self.misses += 1

            self.lookup_count += 1

        # Sort misses by frequency (descending) - check most frequent positions first
        misses_sorted = sorted(misses, key=lambda x: self.freq[x[2]], reverse=True)
        miss_list = [(fen, depth) for fen, depth, _ in misses_sorted]

        self._maybe_prune()
        return hits, miss_list

    def put(self, fen, depth, value):
        k = self._key(fen, depth)
        self.cache[k] = value
        self.freq[k] += 1

    def put_many(self, results):
        """
        Batch insert for multiple positions.

        :param results: List of (fen, depth, value) tuples
        """
        for fen, depth, value in results:
            k = self._key(fen, depth)
            self.cache[k] = value
            self.freq[k] += 1

    # ---------------- Persistence ----------------

    def load(self):
        if not self.cache_file.exists():
            return
        size_mb = self.cache_file.stat().st_size / 1024 / 1024
        print(f"Loading cache from {self.cache_file} ({size_mb:.1f} MB)...")
        with gzip.open(self.cache_file, "rb") as f:
            data = pickle.load(f)

        # Handle both old format (cache only) and new format (cache + freq)
        if isinstance(data, dict) and 'cache' in data:
            self.cache = data['cache']
            self.freq = data.get('freq', defaultdict(int))
        else:
            self.cache = data
            self.freq = defaultdict(int)

        # Initialize frequency for items without it
        for k in self.cache.keys():
            if k not in self.freq:
                self.freq[k] = 1

        print(f"  Loaded {len(self.cache):,} positions\n")

    def save(self):
        if not self.cache:
            print("Nothing to save.")
            return

        # Pure LFU: Keep top N positions by frequency
        if len(self.cache) > self.max_cache_size:
            # Use heap to efficiently get top N items
            heap = []
            for k in self.cache.keys():
                freq = self.freq.get(k, 1)
                if len(heap) < self.max_cache_size:
                    heapq.heappush(heap, (freq, k))
                else:
                    heapq.heappushpop(heap, (freq, k))

            top_keys = {k for _, k in heap}
            trimmed_cache = {k: self.cache[k] for k in top_keys}
            trimmed_freq = {k: self.freq[k] for k in top_keys}
        else:
            trimmed_cache = self.cache
            trimmed_freq = dict(self.freq)

        kept = len(trimmed_cache)
        total = len(self.cache)

        if kept < total:
            print(f"\nPruning cache: keeping top {kept:,} of {total:,} positions...")

        # Save both cache and frequency data
        data = {
            'cache': trimmed_cache,
            'freq': trimmed_freq
        }

        with gzip.open(self.cache_file, "wb") as f:
            pickle.dump(data, f)

        size_mb = self.cache_file.stat().st_size / 1024 / 1024
        hit_rate = self._hit_rate()
        print(f"  Saved {kept:,} positions ({size_mb:.1f} MB)")
        print(f"  Cache stats: {self.hits:,} hits, {self.misses:,} misses "
              f"({hit_rate:.1f}% hit rate)")

        self.cache = trimmed_cache
        self.freq = defaultdict(int, trimmed_freq)
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
        elif self.periodic_save:
            self.save()

    def _reset_stats(self):
        self.hits = self.misses = self.lookup_count = 0







