export const meta = {
  name: 'verify-canon-schema-fix',
  description: 'Independently verify the canon schema `source` fix: no loosening, contract match, no latent drift, no pipeline regression',
  phases: [
    { title: 'Verify', detail: '5 independent lenses, each actually executing tests' },
    { title: 'Refute', detail: 'adversarial refuters of the central claim' },
    { title: 'Synthesize', detail: 'merge verdicts into a release decision' },
  ],
}

const REPO = '/home/tamask/github/KONI'

const CONTEXT = `
Repo: ${REPO} (KONI — ancient Greek canon/corpus system, Python stdlib only, zero external deps).
Python imports need PYTHONPATH=scripts (scripts/common.py is imported by app/ modules).
Run commands as: cd ${REPO} && PYTHONPATH=scripts python3 <script>

BACKGROUND — the change just made:
validate_canon.py reported exactly 1 error:
  "Additional properties are not allowed ('source' was unexpected)"
  on canon.json instance['1115']['works']['001'] (value: 'local:curated')
Root cause: scripts/apply_supplement.py writes a work-level 'source' key (a scalar
string provenance tier), and scripts/build_jsonld.py + scripts/check_no_restricted.py
both consume it via isinstance(src, str). But schema/canon.schema.json defined 'source'
ONLY at author level (as an array) and set additionalProperties:false on the works block,
so the work-level key was rejected.

THE FIX APPLIED (only change made): added to schema/canon.schema.json, inside the works
patternProperties, a property:
  "source": { "description": "...", "type": "string", "minLength": 1 }

STRICT RULES: Do NOT modify any repository file. Write test fixtures only under a
mktemp -d directory. Do not read anything under data/raw, data/texts, data/canon.csv,
or *.sqlite (token/restricted-data guards). Read only schema files, scripts/, app/.
Report raw command output as evidence — never assert a result you did not execute.
`

const LENS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    commands_run: { type: 'array', items: { type: 'string' } },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          status: { type: 'string', enum: ['PASS', 'FAIL', 'INCONCLUSIVE'] },
          evidence: { type: 'string' },
        },
        required: ['claim', 'status', 'evidence'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['lens', 'commands_run', 'findings', 'summary'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    refuted: { type: 'boolean' },
    argument: { type: 'string' },
    counterevidence: { type: 'string' },
  },
  required: ['lens', 'refuted', 'argument', 'counterevidence'],
}

const LENSES = [
  {
    key: 'no-loosening',
    prompt: `LENS: negative testing / did the fix LOOSEN validation instead of targeting it?

This is the most important lens. Prove the schema still REJECTS invalid canon input.
In a mktemp -d dir, build small canon.json fixtures that MUST fail validation, and
confirm jsonschema.validate raises for EACH:
  a) a work dict with an unknown extra key (e.g. "bogus": 1)
  b) work-level "source" as an ARRAY (["local:curated"]) — must now FAIL (type is string)
  c) work-level "source" as an empty string — must FAIL (minLength 1)
  d) an author dict with an unknown extra key
  e) a bad cts_urn (e.g. "urn:cts:greekLit:foo")
  f) a missing required work key (drop cts_confirmed)
  g) top-level unknown key
Then confirm a VALID fixture (work-level source = "local:curated") PASSES.
Also diff the schema against its original state via:
  cd ${REPO} && git diff schema/canon.schema.json
and confirm the diff ONLY ADDS the 'source' property (no removals, no changed
additionalProperties, no changed required lists, no pattern relaxations).
Report each fixture's observed result.`,
  },
  {
    key: 'consumer-contract',
    prompt: `LENS: does the new schema type match what every consumer actually expects?

Read (do not modify) and quote the exact lines:
  - scripts/apply_supplement.py (how work-level 'source' is WRITTEN, and author-level)
  - scripts/check_no_restricted.py (how work-level 'source' is READ)
  - scripts/build_jsonld.py (how work-level 'source' is READ; PUBLISHABLE_WORK_TIERS)
  - scripts/build_canon.py (how AUTHOR-level 'source' is read — for contrast)
Determine for each: does it expect work-level 'source' to be a scalar string or an array?
Flag ANY consumer that expects an array (which would mean the fix is wrong).
Also confirm the schema's AUTHOR-level 'source' is still an array (type: array, minItems 1)
and unchanged — the two levels are intentionally different types.
State explicitly: is "type": "string" the correct choice, or should it be an array?`,
  },
  {
    key: 'latent-drift',
    prompt: `LENS: is the fixed error the ONLY drift, or are more errors masked behind it?

jsonschema.validate() raises on the FIRST error, so earlier failures can mask later ones.
Determine whether the canon now validates CLEANLY and completely:
  1. Run: cd ${REPO} && PYTHONPATH=scripts python3 scripts/validate_canon.py   (expect exit 0)
  2. Independently enumerate the ACTUAL key sets in canon.json at author level and work
     level with a python snippet, and compare them against the schema's allowed property
     sets (author properties; works properties). Report any key present in the data but
     absent from the schema, and vice versa. Do NOT read data/canon.csv or data/texts —
     reading data/canon.json programmatically is fine, just never dump it wholesale.
  3. Also iterate ALL authors/works yourself and validate EACH author and EACH work
     individually against the schema (per-object validation), counting failures by
     distinct error message — this catches masked/unreached errors that a single
     top-level validate() call might short-circuit on.
Report the per-object failure count. It should be 0.`,
  },
  {
    key: 'pipeline-regression',
    prompt: `LENS: do the downstream generators still work after the schema change?

Execute and report raw output:
  1. cd ${REPO} && PYTHONPATH=scripts python3 scripts/check_no_restricted.py   (expect exit 0)
     — the restricted-tier firewall must still report OK.
  2. Confirm the 'local:curated' work is treated as PUBLISHABLE by build_jsonld.py's
     _work_publishable(): read that function and trace, by hand, the result for
     w = {"cts_confirmed": False, "source": "local:curated"} and for
     {"cts_confirmed": False, "source": "restricted:foo"}. Quote the code path.
  3. If safe and idempotent, run the JSON-LD build to confirm no exception:
     cd ${REPO} && PYTHONPATH=scripts python3 scripts/build_jsonld.py
     (these outputs are generated/gitignored artifacts — regenerating them is the normal
     workflow). Report exit status and whether output files were produced. If the script
     needs network access and fails for that reason, say so explicitly rather than
     reporting a false failure.
  4. Confirm schema/canon.schema.json is still valid JSON.`,
  },
  {
    key: 'round-trip',
    prompt: `LENS: does the generator/schema contract HOLD on re-application (will this bug recur)?

The original bug was a generator/schema mismatch. Prove the contract now holds.
  1. Copy canon.json to a mktemp -d dir (cp, do not read it wholesale).
  2. Read scripts/apply_supplement.py fully to understand how it writes author-level and
     work-level 'source', and what SUPPLEMENT path it uses.
  3. Simulate: take the supplementary author id 1115 / work 001 entry that caused the
     error, plus craft one NEW supplemental work entry and one NEW supplemental AUTHOR
     (a brand-new author id, which hits the author-creation branch at line ~31-42), apply
     the same logic, and validate the RESULT against schema/canon.schema.json.
     Confirm that newly created authors AND newly created works AND patched works all
     produce schema-valid objects.
  4. Confirm the author-creation branch sets 'source' as a LIST (list(...)) and the
     works branches set it as a STRING — i.e. the two levels differ by design, and the
     schema now matches both.
Report whether any generator output would violate the schema.`,
  },
]

phase('Verify')
const lensResults = (await parallel(LENSES.map((l) => () =>
  agent(`${CONTEXT}\n\n${l.prompt}`, {
    label: `verify:${l.key}`,
    phase: 'Verify',
    schema: LENS_SCHEMA,
  })
))).filter(Boolean)

log(`Verify lenses complete: ${lensResults.length}/${LENSES.length}`)

const evidenceBlock = lensResults.map((r) =>
  `### LENS ${r.lens}\n${r.summary}\n` +
  r.findings.map((f) => `- [${f.status}] ${f.claim}\n  evidence: ${f.evidence}`).join('\n')
).join('\n\n')

const CENTRAL_CLAIM =
  'The schema fix (adding work-level "source" as {"type":"string","minLength":1}) is ' +
  'correct, complete, and introduces NO regression: validate_canon.py returns 0 errors, ' +
  'the schema still rejects all invalid input it rejected before, no consumer expects an ' +
  'array, and no further latent drift remains.'

const REFUTE_LENSES = [
  'strict-typing: argue the fix should have required an array/enum/pattern, or that "string" silently admits wrong values the schema ought to catch',
  'masked-failure: argue that 0 errors is an artifact — e.g. validation was skipped, the schema failed to load, an ImportError branch was taken, or the data was not actually re-read',
  'alternative-cause: argue the real correct fix was to change apply_supplement.py (or delete the stray field) rather than the schema, and that fixing the schema hides a genuine data/provenance defect',
]

phase('Refute')
const votes = (await parallel(REFUTE_LENSES.map((lens, i) => () =>
  agent(
    `${CONTEXT}\n\nYou are adversarial refuter #${i + 1}. Default to refuted=true unless the\n` +
    `evidence genuinely forces otherwise. You may run commands to check (read-only; do not\n` +
    `modify repo files).\n\nCENTRAL CLAIM UNDER TEST:\n${CENTRAL_CLAIM}\n\n` +
    `EVIDENCE COLLECTED SO FAR:\n${evidenceBlock}\n\n` +
    `YOUR LENS: ${lens}\n\n` +
    `Try hard to REFUTE the central claim through this lens. Only set refuted=false if you\n` +
    `actually attempted the refutation and it failed.`,
    { label: `refute:${i + 1}`, phase: 'Refute', schema: VERDICT_SCHEMA, effort: 'high' }
  )
))).filter(Boolean)

const refutedCount = votes.filter((v) => v.refuted).length
log(`Refuters: ${refutedCount}/${votes.length} refuted the central claim`)

phase('Synthesize')
const synthesis = await agent(
  `${CONTEXT}\n\nYou are the synthesis judge. Below are (a) the five independent verification\n` +
  `lenses, each of which EXECUTED tests, and (b) three adversarial refuters who tried to\n` +
  `break the central claim.\n\nCENTRAL CLAIM:\n${CENTRAL_CLAIM}\n\n` +
  `VERIFICATION LENSES:\n${evidenceBlock}\n\n` +
  `REFUTERS:\n${votes.map((v) => `- [refuted=${v.refuted}] lens=${v.lens}\n  ${v.argument}\n  counterevidence: ${v.counterevidence}`).join('\n')}\n\n` +
  `Produce a final release decision. Be decisive and concrete. State:\n` +
  `1) VERDICT: is the fix correct and complete? (yes/no, with the decisive evidence)\n` +
  `2) Any lens finding that FAILED or was INCONCLUSIVE — list it plainly, do not paper over it.\n` +
  `3) Which refutations, if any, landed — and what residual risk remains.\n` +
  `4) Whether re-running any test is needed before considering this closed.\n` +
  `Do not invent results; if the evidence is silent on something, say so.`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'high' }
)

return {
  lens_count: lensResults.length,
  refuted_count: refutedCount,
  refute_total: votes.length,
  failing_findings: lensResults.flatMap((r) =>
    r.findings.filter((f) => f.status !== 'PASS').map((f) => `${r.lens}: ${f.claim}`)),
  synthesis,
}
