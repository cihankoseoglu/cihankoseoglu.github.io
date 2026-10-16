#!/bin/sh
# Rebuilds the Latin subsets in fonts/ from the complete Iosevka files in fonts/full/.
# Needs fontTools and brotli (pip install fonttools brotli). The unicode range must match
# the one in css/site.css. Glyph names, the name table, hinting and the default layout
# features (including calt, which draws // and ->) are kept so text renders the same.
set -e
cd "$(dirname "$0")/.."
RANGE="U+0000-017F,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212"
for w in regular medium semibold bold italic; do
  pyftsubset "fonts/full/iosevka-$w.woff2" --unicodes="$RANGE" --glyph-names \
    --name-IDs='*' --name-legacy --name-languages='*' --notdef-outline \
    --flavor=woff2 --output-file="fonts/iosevka-$w.woff2"
done
ls -l fonts/*.woff2
