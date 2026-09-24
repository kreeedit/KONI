import sys, inspect, textwrap, time, random
sys.path.insert(0, "/home/tamask/github/KONI")
from collections import Counter
from app import flame_pure as fp
NS = {"levenshtein_ratio": lambda a, b: 0.0, "Counter": Counter, "_shingles": fp._shingles}
exec(textwrap.dedent(inspect.getsource(fp.cluster_pairs)), NS)
cp = NS["cluster_pairs"]
random.seed(5)
W = ["".join(random.choice("αβγδεζηθικλμνξοπρστυφχψω") for _ in range(5)) for _ in range(300)]
for U in (500, 1000, 2000, 4000):
    sigs = [" ".join(random.choice(W) for _ in range(5)) for _ in range(U)]
    t = time.time(); r = cp(sigs, max_lev=10**9); dt = time.time() - t
    print(f"U={U}: gate+stub-DP time={dt:.1f}s  lev_compares={r['stats']['lev_compares']} "
          f"truncated={r['stats']['truncated']}", flush=True)
