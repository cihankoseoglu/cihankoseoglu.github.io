#!/usr/bin/env python3
"""Shared build steps for cihankoseoglu.com. album.py and notes.py run these after every change.

  python3 _build/shared.py

1. Inlines js/gtag.js and css/site.css into every page, between the shared:start and
   shared:end comments, so no page waits for a separate CSS or tag file before it can draw.
   Edit js/gtag.js or css/site.css, then run this.
2. Rewrites sitemap.xml from the pages that exist, with lastmod dates and album photos.

No dependencies beyond Python 3.
"""
import datetime, glob, html, json, os, re, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.cihankoseoglu.com'
SITEMAP = os.path.join(REPO, 'sitemap.xml')
ALBUMS = os.path.join(REPO, 'photography', 'albums.js')
MARK = re.compile(r'( *)<!-- shared:start.*?-->\n.*?<!-- shared:end -->', re.S)


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def load_albums():
    if not os.path.exists(ALBUMS):
        return []
    text = read(ALBUMS)
    return json.loads(text[text.index('['):text.rindex(']') + 1])


def shared_block(pad='  '):
    js = read(os.path.join(REPO, 'js', 'gtag.js')).strip()
    css = read(os.path.join(REPO, 'css', 'site.css')).strip()
    return (f'{pad}<!-- shared:start (written by _build/shared.py from js/gtag.js and css/site.css; edit those) -->\n'
            f'{pad}<script>\n{js}\n</script>\n{pad}<style>\n{css}\n</style>\n{pad}<!-- shared:end -->')


def inline_shared(text):
    return MARK.sub(lambda m: shared_block(m[1]), text)


def pages():
    """Every published HTML page, as (path on disk, URL path)."""
    out = []
    for path in sorted(glob.glob(os.path.join(REPO, '**', 'index.html'), recursive=True)):
        rel = os.path.relpath(path, REPO)
        if rel.startswith(('_', '.')) or os.sep + '_' in rel or 'node_modules' in rel:
            continue
        url = '/' + os.path.dirname(rel).replace(os.sep, '/')
        out.append((path, url.rstrip('/') + '/'))
    return out


def lastmod(path):
    """Date of the last commit that touched the file, or today if it has uncommitted changes."""
    rel = os.path.relpath(path, REPO)
    try:
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', rel], cwd=REPO, capture_output=True, text=True).stdout.strip()
        date = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', rel], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        dirty, date = 'x', ''
    return datetime.date.today().isoformat() if dirty or not date else date


def write_sitemap():
    albums = {a['slug']: a for a in load_albums()}
    rows = []
    for path, url in pages():
        if url == '/404/':
            continue
        row = f'  <url><loc>{SITE}{url}</loc><lastmod>{lastmod(path)}</lastmod>'
        m = re.match(r'^/photography/([^/]+)/$', url)
        if m and m[1] in albums:
            for p in albums[m[1]]['photos']:
                row += f'\n    <image:image><image:loc>{SITE}{p["src"]}</image:loc></image:image>'
            row += '\n  '
        rows.append(row + '</url>\n')
    write(SITEMAP, '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                   'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + ''.join(rows) + '</urlset>\n')


def build():
    files = [p for p, _ in pages()] + [os.path.join(REPO, '404.html')]
    changed = 0
    for path in files:
        if not os.path.exists(path):
            continue
        text = read(path)
        new = inline_shared(text)
        if new != text:
            write(path, new)
            changed += 1
    write_sitemap()
    return changed


if __name__ == '__main__':
    n = build()
    print(f'Shared CSS and tag inlined in {n} page(s); sitemap.xml written')
