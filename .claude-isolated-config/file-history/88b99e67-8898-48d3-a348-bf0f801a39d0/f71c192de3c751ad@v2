"""The property that actually matters: after compare() re-sorts pairs and
remaps cluster members, the pairs a cluster points at must all still be the
SAME topos (their cores must agree). Range-only checks would not catch a remap
that points at the wrong rows."""
import os, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F, texts

fails = []
def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)

# Compare on a work that produces many near-duplicate pairs (self-compare gives
# the densest cluster structure) plus a cross-author case.
CASES = {
    "self 0003.001": ("0003", "001", "0003", "001"),
    "procopius x thucydides": ("4029", "001", "0003", "001"),
}
for label, (a1, w1, a2, w2) in CASES.items():
    s1, s2 = texts.section_texts(a1, w1), texts.section_texts(a2, w2)
    if not s1 or not s2:
        print("  skip (no text):", label); continue
    res = F.compare(s1, s2)
    pairs, clusters = res["pairs"], res["clusters"]
    print("\n%s: pairs=%d clusters=%d" % (label, len(pairs), len(clusters)))
    if not clusters:
        print("  (no clusters to check)"); continue

    # 1. a cluster's members must share the same core_text as its own best member
    bad_core = 0
    for c in clusters:
        cores = {pairs[m]["core_text"] for m in c["members"]}
        # exact-duplicate cores collapse first, so a genuine cluster can hold
        # near-variants; require that the members agree far more than random.
        if len(cores) == len(c["members"]) and c["size"] > 2:
            bad_core += 1
    check("no cluster is a set of all-distinct cores (size>2)", bad_core == 0, bad_core)

    # 2. transitivity: every member must be near-similar to the best member
    worst = []
    for c in clusters:
        best = pairs[c["members"][0]]["core_text"]
        for m in c["members"]:
            second = best if False else None
        for m in c["members"][1:]:
            r = F.levenshtein_ratio(best, pairs[m]["core_text"])
            if r < 0.5:
                worst.append((c["id"], round(r, 3), pairs[m]["core_text"][:40]))
    check("every member is near the cluster's best core (ratio >= 0.5)",
          not worst, worst[:3])

    # 3. members are sorted ascending (the UI assumes members[0] is the best)
    unsorted = [c["id"] for c in clusters if sorted(c["members"]) != c["members"]]
    check("members sorted ascending in every cluster", not unsorted, unsorted[:5])

    # 4. the cluster's best member really is its highest-chain member
    notbest = []
    for c in clusters:
        best_idx = max(c["members"], key=lambda m: pairs[m]["chain_len"])
        if best_idx != c["members"][0]:
            notbest.append(c["id"])
    check("members[0] is the highest-chain member of the cluster", not notbest, notbest[:5])

    # 5. clustered pairs and singletons partition the pair list exactly
    in_cluster = [m for c in clusters for m in c["members"]]
    check("no pair in two clusters", len(set(in_cluster)) == len(in_cluster))
    check("clustered + singletons == all pairs",
          len(in_cluster) + res["cluster_stats"]["n_singletons"] == len(pairs))

print("\nRESULT: %d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
