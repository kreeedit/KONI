#!/bin/bash
# Resumable fetch of the 27 LSJ slices. Skip-if-complete, resume-if-partial.
base="https://raw.githubusercontent.com/PerseusDL/lexica/master/CTS_XML_TEI/perseus/pdllex/grc/lsj"
cd /home/tamask/github/KONI/data/lexicon/raw || exit 1
for n in $(seq 1 27); do
  f="grc.lsj.perseus-eng$n.xml"
  if [ -s "$f" ] && python3 -c "import xml.etree.ElementTree as ET,sys; ET.parse('$f')" 2>/dev/null; then
    echo "skip $f (present and parses)"; continue
  fi
  echo "fetch $f ..."
  curl -sS --retry 3 --retry-delay 2 -C - -o "$f" "$base/$f" || echo "FAILED $f"
  echo "  -> $(wc -c < "$f" 2>/dev/null) bytes"
done
echo "ALL DONE: $(ls -1 grc.lsj.perseus-eng*.xml 2>/dev/null | wc -l) files, $(du -sh . | cut -f1) total"
