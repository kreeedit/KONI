"""Focused tests for flame_pure.cluster_pairs and the compare() index remap."""
import os, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

fails = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


def members_are_sane(res, n):
    seen = []
    for c in res["clusters"]:
        seen += c["members"]
        if len(c["members"]) != c["size"]:
            return False, f"size mismatch in cluster {c['id']}"
        if sorted(c["members"]) != c["members"]:
            return False, f"members not sorted in cluster {c['id']}"
        if len(set(c["members"])) != len(c["members"]):
            return False, f"duplicate member in cluster {c['id']}"
    if len(set(seen)) != len(seen):
        return False, "a pair is in two clusters"
    if any(not (0 <= m < n) for m in seen):
        return False, "member index out of range"
    return True, ""


print("cluster_pairs — basics")
r = F.cluster_pairs([])
check("empty input yields nothing", r["clusters"] == [] and r["pair_cluster"] == [])
check("empty input stats zeroed", r["stats"]["n_pairs"] == 0 and r["stats"]["n_clusters"] == 0)

r = F.cluster_pairs(["a b c", "d e f", "g h i"])
check("all distinct -> no clusters", r["clusters"] == [])
check("all distinct -> all singletons", r["stats"]["n_singletons"] == 3)
check("pair_cluster all -1", r["pair_cluster"] == [-1, -1, -1])

print("\ncluster_pairs — exact duplication")
sigs = ["alpha beta gamma"] * 4 + ["delta epsilon"] * 2
r = F.cluster_pairs(sigs)
check("two clusters found", len(r["clusters"]) == 2, [c["size"] for c in r["clusters"]])
check("sizes 4 then 2", [c["size"] for c in r["clusters"]] == [4, 2])
check("members sane", members_are_sane(r, len(sigs))[0], members_are_sane(r, len(sigs))[1])
check("no lev work needed", r["stats"]["lev_compares"] == 0)
check("cores collapsed 6 -> 2", r["stats"]["n_cores"] == 2)

print("\ncluster_pairs — min_size")
r = F.cluster_pairs(sigs, min_size=3)
check("min_size=3 keeps only the 4-group", [c["size"] for c in r["clusters"]] == [4])
r = F.cluster_pairs(sigs, min_size=5)
check("min_size=5 keeps nothing", r["clusters"] == [])

print("\ncluster_pairs — threshold semantics")
near = ["τοῖς δὲ Ἀθηναίοις ναῦς ἑκατόν", "τοῖς δὲ Ἀθηναίοις ναῦς ἑκατόν."]
r = F.cluster_pairs(near, threshold=1.0)
check("threshold=1.0 does not merge a 1-char difference", r["clusters"] == [])
r = F.cluster_pairs(near, threshold=0.85)
check("threshold=0.85 merges it", len(r["clusters"]) == 1 and r["clusters"][0]["size"] == 2)

print("\ncluster_pairs — transitivity (union-find, not greedy pairs)")
# a~b and b~c, but a is not directly similar to c.
a = "one two three four five six seven eight nine ten"
b = "one two three four five six seven eight nine ten!"
c = "one two three four five six seven eight nine ten!!"
r = F.cluster_pairs([a, b, c], threshold=0.85)
check("A~B~C collapses to one cluster of 3", len(r["clusters"]) == 1 and r["clusters"][0]["size"] == 3)

print("\ncluster_pairs — the max_lev cap is reported, not hidden")
many = [f"word{i} " * 10 for i in range(60)] + ["word0 word0 word0 word0 word0 word0 word0 word0 word0 wordX"]
r = F.cluster_pairs(many, threshold=0.5, max_lev=1)
check("truncated flag set when cap hit", r["stats"]["truncated"] is True)
r = F.cluster_pairs(many, threshold=0.5, max_lev=200000)
check("not truncated with a generous cap", r["stats"]["truncated"] is False)

print("\ncluster_pairs — cluster ids and ordering")
sigs = ["x"] * 2 + ["y"] * 9 + ["z"] * 5
r = F.cluster_pairs(sigs)
check("ids are 0..k-1", [c["id"] for c in r["clusters"]] == [0, 1, 2])
check("sorted by size desc", [c["size"] for c in r["clusters"]] == [9, 5, 2])
check("no singletons left", r["stats"]["n_singletons"] == 0)
check("pair_cluster set for members only",
      sorted(set(r["pair_cluster"])) == [0, 1, 2] and r["pair_cluster"][:2] == [2, 2])

print("\ncompare() — cluster members index the RETURNED pair order")
s1 = [{"label": "1.1", "text": " ".join(["ἀνὴρ", "ἀγαθὸς", "ἦν", "ἐν", "πολέμῳ"] * 4)}]
s2 = [{"label": "2.1", "text": " ".join(["ἀνὴρ", "ἀγαθὸς", "ἦν", "ἐν", "πολέμῳ"] * 4)}]
res = F.compare(s1, s2)
pairs, clusters = res["pairs"], res["clusters"]
check("compare() exposes clusters", isinstance(clusters, list))
check("compare() exposes cluster_stats", "n_pairs" in (res["cluster_stats"] or {}))
ok = True
for c in clusters:
    for m in c["members"]:
        if not (0 <= m < len(pairs)):
            ok = False
check("remapped members are in range of the sorted pairs array", ok)
check("pairs are chain_len sorted", all(pairs[i]["chain_len"] >= pairs[i + 1]["chain_len"]
                                        for i in range(len(pairs) - 1)))
check("every pair carries core_text", all("core_text" in p for p in pairs))

print("\ncompare_iter() — cluster event ordering")
evs = [e["t"] for e in F.compare_iter(s1, s2, progress_every=10**9)]
check("exactly one clusters event", evs.count("clusters") == 1)
check("exactly one done event", evs.count("done") == 1)
check("clusters precedes done", evs.index("clusters") < evs.index("done"))
check("phase event precedes clusters", evs.index("phase") < evs.index("clusters"))

print("\nRESULT: %d failure(s)" % len(fails))
if fails:
    for f in fails:
        print("  -", f)
    sys.exit(1)
