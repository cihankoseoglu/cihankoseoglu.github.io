#!/usr/bin/env python3
"""Build the /notes/ section of cihankoseoglu.com from markdown files.

  python3 _build/notes.py

Each note is a markdown file in _build/notes/ that starts with a small header:

  ---
  title: What Consent Mode actually does
  date: 2026-10-20
  description: One sentence for search results and link previews (optional).
  ---

  The text, in markdown.

The file name (minus .md) is the URL: _build/notes/consent-mode.md becomes /notes/consent-mode/.
Drafts live in _build/notes-drafts/ and are never published; move a file into _build/notes/ to publish it.

This writes notes/<slug>/index.html for every note and notes/index.html, puts the latest three
on the home page (between the notes:start and notes:end comments in index.html), and runs
_build/shared.py, which inlines the shared CSS and rewrites sitemap.xml. With no notes, the notes/ folder is removed and the home page shows nothing.
Supported markdown: # headings, paragraphs, - and 1. lists, > quotes, ``` code blocks,
**bold**, *italic*, `code`, [links](url) and ![images](url).
No dependencies beyond Python 3.
"""
import datetime, html, json, os, re, shutil, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, '_build', 'notes')
OUT = os.path.join(REPO, 'notes')
HOME = os.path.join(REPO, 'index.html')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared  # noqa: E402
SITE = 'https://www.cihankoseoglu.com'


def dims(src):
    """ width="..." height="..." for a local PNG or JPEG, so the page doesn't jump while it loads."""
    path = os.path.join(REPO, src.lstrip('/')) if src.startswith('/') else None
    if not path or not os.path.exists(path):
        return ''
    with open(path, 'rb') as fh:
        data = fh.read(1 << 20)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return f' width="{int.from_bytes(data[16:20], "big")}" height="{int.from_bytes(data[20:24], "big")}"'
    i = 2
    while data[:2] == b'\xff\xd8' and i < len(data) - 9:
        marker, n = data[i + 1], int.from_bytes(data[i + 2:i + 4], 'big')
        if marker in (0xC0, 0xC1, 0xC2):
            return f' width="{int.from_bytes(data[i + 7:i + 9], "big")}" height="{int.from_bytes(data[i + 5:i + 7], "big")}"'
        i += 2 + n
    return ''


def inline(text):
    """Markdown inline syntax to HTML; everything else is escaped."""
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for part in parts:
        if part.startswith('`') and part.endswith('`') and len(part) > 1:
            out.append('<code>' + html.escape(part[1:-1]) + '</code>')
            continue
        s = html.escape(part, quote=False)  # & < > are escaped here, so URLs below only need their quotes escaped
        q = lambda v: v.replace('"', '&quot;')
        s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', lambda m: f'<img src="{q(m[2])}" alt="{q(m[1])}"{dims(m[2])} loading="lazy">', s)
        s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: f'<a href="{q(m[2])}">{m[1]}</a>', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
        out.append(s)
    return ''.join(out)


def markdown(text):
    lines = text.split('\n')
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            out.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
        elif not line.strip():
            flush()
        elif m := re.match(r'^(#{1,4})\s+(.*)', line):
            flush()
            n = min(max(len(m[1]), 2), 4)  # the note title is the page's only h1
            out.append(f'<h{n}>{inline(m[2].strip())}</h{n}>')
        elif re.match(r'^\s*([-*]|\d+\.)\s+', line):
            flush()
            tag = 'ol' if re.match(r'^\s*\d+\.', line) else 'ul'
            items = []
            while i < len(lines) and re.match(r'^\s*([-*]|\d+\.)\s+', lines[i]):
                item = re.sub(r'^\s*([-*]|\d+\.)\s+', '', lines[i])
                while i + 1 < len(lines) and re.match(r'^\s{2,}\S', lines[i + 1]) and not re.match(r'^\s*([-*]|\d+\.)\s+', lines[i + 1]):
                    i += 1; item += ' ' + lines[i].strip()
                items.append('<li>' + inline(item) + '</li>'); i += 1
            out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
            continue
        elif line.startswith('>'):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith('>'):
                quote.append(lines[i][1:].strip()); i += 1
            out.append('<blockquote>' + markdown('\n'.join(quote)) + '</blockquote>')
            continue
        else:
            para.append(line.strip())
        i += 1
    flush()
    return '\n'.join(out)


def read_note(path):
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        sys.exit(f'{os.path.basename(path)}: missing the --- header with title and date')
    meta = dict(re.findall(r'^(\w+):\s*(.*?)\s*$', m[1], re.M))
    for key in ('title', 'date'):
        if not meta.get(key):
            sys.exit(f'{os.path.basename(path)}: header needs a {key}')
    try:
        date = datetime.date.fromisoformat(meta['date'])
    except ValueError:
        sys.exit(f'{os.path.basename(path)}: date should look like 2026-10-20')
    slug = os.path.splitext(os.path.basename(path))[0]
    if not re.match(r'^[a-z0-9-]+$', slug):
        sys.exit(f'{os.path.basename(path)}: use lowercase letters, digits and dashes in the file name')
    return {'slug': slug, 'title': meta['title'], 'date': date, 'description': meta.get('description', ''),
            'body': markdown(text[m.end():])}


def nice_date(d):
    return f'{d.day} {d.strftime("%B")} {d.year}'


HEAD = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{url}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="Cihan Koseoglu">
  <meta property="og:image" content="https://www.cihankoseoglu.com/images/share.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="robots" content="max-image-preview:large">
{extra}  <link rel="canonical" href="{url}">
  <meta name="theme-color" content="#faf8f5">
  <link rel="icon" href="/favicon.ico">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="preload" href="/fonts/iosevka-regular.woff2" as="font" type="font/woff2" crossorigin>
  <!-- shared:start -->
  <!-- shared:end -->
  <style>
{css}  </style>
</head>
<body>
  <main>
    <nav class="crumbs"><a href="/">Cihan Koseoglu</a>{crumb}</nav>
'''

FOOT = '''    <footer>© {year} Cihan Koseoglu · <a href="#" onclick="showConsent(); return false;">Cookie settings</a></footer>
  </main>
  <script src="/js/site.js"></script>
</body>
</html>
'''

CSS = '''/* Notes pages. Inlined by _build/notes.py; edit the CSS in that script. */
:root { --bg: #faf8f5; }
body { background: var(--bg); font-size: 17px; line-height: 1.7; }
main { max-width: 640px; margin: 0 auto; padding: 48px 20px 64px; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color .2s; }
a:hover { border-bottom-color: currentColor; }
.crumbs { font-size: 15px; color: var(--muted); margin-bottom: 48px; }
.crumbs a { color: var(--text); font-weight: 500; }
.crumbs span { margin: 0 8px; }
h1 { font: 400 clamp(40px, 8vw, 56px)/1.08 var(--serif); letter-spacing: -0.01em; margin: 0 0 12px; }
.date { color: var(--muted); font-size: 15px; margin: 0 0 40px; }
article h2, article h3, article h4 { font: 400 28px/1.2 var(--serif); margin: 40px 0 12px; }
article h3, article h4 { font-size: 22px; }
article p, article ul, article ol { margin: 0 0 18px; }
article li { margin-bottom: 6px; }
article img { max-width: 100%; height: auto; display: block; margin: 28px 0; }
article code { font: 15px/1.5 var(--mono); background: #f1ede7; padding: 1px 5px; border-radius: 4px; }
article pre { background: #f1ede7; padding: 16px; overflow-x: auto; border-radius: 6px; margin: 0 0 18px; }
article pre code { background: none; padding: 0; }
article blockquote { margin: 0 0 18px; padding: 2px 0 2px 20px; border-left: 2px solid var(--accent); color: var(--muted); }
.list { list-style: none; padding: 0; margin: 0 0 48px; }
.list li { display: flex; gap: 16px; align-items: baseline; padding: 12px 0; border-bottom: 1px solid var(--line); }
.list li:first-child { border-top: 1px solid var(--line); }
.list a { font: 400 24px/1.25 var(--serif); color: var(--text); }
.list a:hover { color: var(--accent); border-bottom-color: transparent; }
.list time { margin-left: auto; color: var(--muted); font-size: 14px; white-space: nowrap; }
footer { border-top: 1px solid var(--line); padding-top: 20px; margin-top: 56px; color: var(--muted); font-size: 14px; }
'''


def esc(s):
    return html.escape(s, quote=True)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def build_pages(notes):
    year = datetime.date.today().year
    shutil.rmtree(OUT, ignore_errors=True)
    if not notes:
        return
    for n in notes:
        url = f'{SITE}/notes/{n["slug"]}/'
        ld = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': n['title'], 'url': url,
              'datePublished': n['date'].isoformat(), 'description': n['description'] or n['title'],
              'author': {'@type': 'Person', '@id': SITE + '/#person', 'name': 'Cihan Koseoglu', 'url': SITE + '/'}}
        extra = (f'  <meta property="article:published_time" content="{n["date"].isoformat()}">\n'
                 f'  <meta property="article:author" content="{SITE}/">\n'
                 f'  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')
        page = HEAD.format(title=esc(n['title']) + ' · Cihan Koseoglu', og_title=esc(n['title']), url=url, og_type='article',
                           description=esc(n['description'] or n['title']), extra=extra, css=CSS,
                           crumb='<span>/</span><a href="/notes/">Notes</a>')
        page += (f'    <article>\n      <h1>{esc(n["title"])}</h1>\n'
                 f'      <p class="date"><time datetime="{n["date"].isoformat()}">{nice_date(n["date"])}</time></p>\n'
                 f'{n["body"]}\n    </article>\n')
        write(os.path.join(OUT, n['slug'], 'index.html'), page + FOOT.format(year=year))
    page = HEAD.format(title='Notes · Cihan Koseoglu', og_title='Notes', url=f'{SITE}/notes/', og_type='website',
                       description='Notes by Cihan Koseoglu on marketing, data, privacy, measurement, AI and code.',
                       extra='', css=CSS, crumb='')
    page += '    <h1>Notes</h1>\n    <ul class="list">\n'
    for n in notes:
        page += (f'      <li><a href="/notes/{n["slug"]}/">{esc(n["title"])}</a>'
                 f'<time datetime="{n["date"].isoformat()}">{nice_date(n["date"])}</time></li>\n')
    write(os.path.join(OUT, 'index.html'), page + '    </ul>\n' + FOOT.format(year=year))


def update_home(notes):
    text = open(HOME, encoding='utf-8').read()
    m = re.search(r'( *)<!-- notes:start.*?-->\n(.*?)( *)<!-- notes:end -->', text, re.S)
    if not m:
        sys.exit('index.html has no <!-- notes:start --> / <!-- notes:end --> markers')
    pad = m[1]
    block = ''
    if notes:
        items = ''.join(f'{pad}    <li><a href="/notes/{n["slug"]}/">{esc(n["title"])}</a>'
                        f'<time datetime="{n["date"].isoformat()}">{nice_date(n["date"])}</time></li>\n' for n in notes[:3])
        block = (f'{pad}<section>\n{pad}  <h2>Notes</h2>\n{pad}  <ul class="notes-list">\n{items}{pad}  </ul>\n'
                 f'{pad}  <a class="notes-all" href="/notes/">All notes &rarr;</a>\n{pad}</section>\n')
    text = text[:m.start(2)] + block + text[m.end(2):]
    with open(HOME, 'w', encoding='utf-8') as fh:
        fh.write(text)


def main():
    files = sorted(f for f in os.listdir(SRC) if f.endswith('.md')) if os.path.isdir(SRC) else []
    notes = sorted((read_note(os.path.join(SRC, f)) for f in files), key=lambda n: (n['date'], n['slug']), reverse=True)
    build_pages(notes)
    update_home(notes)
    shared.build()  # inlines the shared CSS and tag into the new pages, rewrites sitemap.xml
    print(f'{len(notes)} note(s) published' + ''.join(f'\n  /notes/{n["slug"]}/  {n["date"]}  {n["title"]}' for n in notes))


if __name__ == '__main__':
    main()
