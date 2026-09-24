"""Unit tests for app/variants.py — the pooling rules and their stoplists.

These assert the MEASURED behaviour recorded in the module docstring, not an
idealised version of it. Where the module is deliberately blind (eta/alpha,
rho-rho/rho-sigma), the test asserts the blindness so a later "fix" cannot
quietly change the numbers the docstring quotes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, "/home/tamask/github/KONI")

from app import variants as V
from app.flame_pure import normalize

fails = []


def check(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")


def n(s):
    return normalize(s)


# --- names() -------------------------------------------------------------
check("names default", V.names(""), V.DEFAULT)
check("names None", V.names(None), V.DEFAULT)
check("names all", V.names("all"), V.DEFAULT)
check("names none", V.names("none"), ())
check("names dash", V.names("-"), ())
check("names list", V.names("xyn,tt"), ("xyn", "tt"))
check("names unknown dropped", V.names("xyn,nope"), ("xyn",))
check("names unknown-only -> empty", V.names("nope"), ())
check("names whitespace", V.names(" xyn , tt "), ("xyn", "tt"))

# --- xyn: prefix, stoplist ----------------------------------------------
r_xyn = V.BY_NAME["xyn"]
check("xyn ξυμμαχια marked", r_xyn.applies_to(n("ξυμμαχία")), True)
check("xyn ξυμμαχων marked", r_xyn.applies_to(n("ξυμμάχων")), True)
check("xyn συμμαχια not marked", r_xyn.applies_to(n("συμμαχία")), False)
# ξυλ- (wood) and ξυρ- (razor) start with the same two letters but are not ξύν.
check("xyn ξυλον stopped", r_xyn.applies_to(n("ξύλον")), False)
check("xyn ξυρον stopped", r_xyn.applies_to(n("ξυρόν")), False)

# --- gign: substring ------------------------------------------------------
r_gign = V.BY_NAME["gign"]
check("gign εγιγνετο marked", r_gign.applies_to(n("ἐγίγνετο")), True)
check("gign εγινετο not marked", r_gign.applies_to(n("ἐγίνετο")), False)
check("gign γιγνομαι marked", r_gign.applies_to(n("γίγνομαι")), True)

# --- tt: substring, Attic stoplist ---------------------------------------
r_tt = V.BY_NAME["tt"]
check("tt πραττω marked", r_tt.applies_to(n("πράττω")), True)
check("tt πρασσω not marked", r_tt.applies_to(n("πράσσω")), False)
check("tt αττικη stopped", r_tt.applies_to(n("Ἀττική")), False)

# --- rr: lexeme pooling, metric off --------------------------------------
r_rr = V.BY_NAME["rr"]
check("rr θαρσος marked", r_rr.applies_to(n("θάρσος")), True)
# θαρρ- is the Koine side of the pair, θαρσ- the marked one.
check("rr θαρρος not marked", r_rr.applies_to(n("θάρρος")), False)
check("rr θαλασσα untouched", r_rr.applies_to(n("θάλασσα")), False)
check("rr not a metric rule", r_rr.metric, False)
check("rr excluded from METRIC_RULES", "rr" in V.METRIC_RULES, False)

# --- unify: one-directional folding --------------------------------------
check("unify xyn ξυμμαχια", V.unify(n("ξυμμαχία"), ("xyn",)), n("συμμαχία"))
check("unify gign εγιγνετο", V.unify(n("ἐγίγνετο"), ("gign",)), n("ἐγίνετο"))
check("unify tt πραττω", V.unify(n("πράττω"), ("tt",)), n("πράσσω"))
# Already-Koine forms must be fixed points: folding is classical -> Koine only.
for form in ("συμμαχία", "ἐγίνετο", "πράσσω"):
    check(f"unify fixed point {form}", V.unify(n(form), V.DEFAULT), n(form))
# Stoplisted forms are fixed points too.
check("unify ξυλον fixed", V.unify(n("ξύλον"), V.DEFAULT), n("ξύλον"))
# The junction case: ξύμμαχοι -> σύμμαχοι, not συύμμαχοι.
check("unify no double vowel", V.unify(n("ξύμμαχοι"), ("xyn",)), n("σύμμαχοι"))
# An empty rule set is the identity.
for form in ("ξυμμαχία", "ἐγίγνετο", "πράττω"):
    check(f"unify no rules {form}", V.unify(n(form), ()), n(form))

# Folding twice equals folding once — pooling must be idempotent or work_freq
# and variant_rates would disagree.
for form in ("ξυμμαχία", "ἐγίγνετο", "πράττω", "συμμαχία", "ξύλον"):
    once = V.unify(n(form), V.DEFAULT)
    check(f"unify idempotent {form}", V.unify(once, V.DEFAULT), once)

# --- marked_rules ---------------------------------------------------------
check("marked_rules xyn", V.marked_rules(n("ξυμμαχία"), V.DEFAULT), ["xyn"])
check("marked_rules none", V.marked_rules(n("θάλασσα"), V.DEFAULT), [])
check("marked_rules rr", V.marked_rules(n("θάρσος"), V.DEFAULT), ["rr"])
# gign fires on a compound, xyn does not — the rules are independent.
check("marked_rules compound", V.marked_rules(n("προσγιγνόμενα"), V.DEFAULT), ["gign"])

# --- describe() -----------------------------------------------------------
desc = V.describe()
check("describe count", len(desc), len(V.DEFAULT))
check("describe keys", sorted(desc[0]), sorted(["name", "summary", "marked", "key_side", "evidence", "caveat", "metric"]))
check("describe names", [d["name"] for d in desc], list(V.DEFAULT))
check("describe subset", [d["name"] for d in V.describe(("xyn",))], ["xyn"])

# --- Rule count / registry consistency -----------------------------------
check("BY_NAME covers RULES", sorted(V.BY_NAME), sorted(r.name for r in V.RULES))
check("DEFAULT all real", all(x in V.BY_NAME for x in V.DEFAULT), True)
check("METRIC_RULES subset", all(x in V.BY_NAME for x in V.METRIC_RULES), True)

if fails:
    print(f"FAIL {len(fails)}")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print(f"OK variants.py — {len(V.RULES)} rules, "
      f"{sum(1 for r in V.RULES if r.metric)} metric")
