# ProgressLogging.py
def progress(i, tot, label="games"):
    print(f"\r  {i}/{tot} {label}", end="", flush=True)
    if i == tot: print()
