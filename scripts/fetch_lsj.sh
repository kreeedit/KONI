#!/usr/bin/env bash
# Fetch the Perseus LSJ slices into data/lexicon/raw/.
#
# The source is PerseusDL/lexica on GitHub, path
# CTS_XML_TEI/perseus/pdllex/grc/lsj/ : 27 alphabetical slices,
# grc.lsj.perseus-eng1..27.xml, about 330 MB in total. They are NOT in this
# repository and must not be: the licence (CC BY-SA 4.0) is fine for a data
# file, but a 330 MB binary blob does not belong in git. The build output in
# data/lexicon/out/ is what the app reads.
#
# RESUMABLE: a slice that already parses as XML is skipped, so an interrupted
# run continues instead of starting over. Delete the file to force a refetch.
#
# The commit below is PerseusDL/lexica master at the time of writing, and the
# files it served were checksummed against the local copy (eng6 matched). It
# is pinned because this is a dictionary that was typeset once, in 1940: the
# transcription is stable, and pinning means a rebuild next year reproduces
# this index instead of silently following an upstream edit. Override with
# LSJ_COMMIT=<sha> to test another revision.
set -u

COMMIT="${LSJ_COMMIT:-56061ca127f4a2844980baffc5f2b6d1332897b3}"
BASE="https://raw.githubusercontent.com/PerseusDL/lexica/$COMMIT/CTS_XML_TEI/perseus/pdllex/grc/lsj"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$HERE/../data/lexicon/raw}"
mkdir -p "$DEST" || exit 1

ok=0; skipped=0; failed=0
for i in $(seq 1 27); do
  f="grc.lsj.perseus-eng$i.xml"
  out="$DEST/$f"
  if [ -s "$out" ] && head -c 200 "$out" | grep -q "<TEI"; then
    skipped=$((skipped + 1)); continue
  fi
  printf 'fetch %s … ' "$f"
  if curl -fsSL --retry 3 --retry-delay 2 -o "$out.part" "$BASE/$f"; then
    mv "$out.part" "$out"
    printf '%s bytes\n' "$(wc -c < "$out")"
    ok=$((ok + 1))
  else
    rm -f "$out.part"
    printf 'FAILED\n'
    failed=$((failed + 1))
  fi
done

echo
echo "fetched $ok, already present $skipped, failed $failed"
du -sh "$DEST" 2>/dev/null
echo
echo "Now build the index:  python3 scripts/build_lexicon.py"
[ "$failed" -eq 0 ] || exit 1
