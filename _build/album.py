#!/usr/bin/env python3
"""Manage the albums on cihankoseoglu.com/photography.

  python3 _build/album.py list
  python3 _build/album.py add "/path/to/photos" ["/another/folder" ...] [--title "Name"] [--year 2026] [--date 2026-03] [--cover NN]
  python3 _build/album.py remove <slug>
  python3 _build/album.py rename <slug> "New Title"
  python3 _build/album.py set-cover <slug> NN
  python3 _build/album.py covers
  python3 _build/album.py sizes
  python3 _build/album.py pages
  python3 _build/album.py icc

`add` takes one or more folders of photos (combined into one album). If a folder has a "selected" subfolder, only
that is used. Photos are taken in file-name order, resized to 2400px on the
long edge, saved as JPEG with all metadata (including GPS) removed, and written
to photography/photos/<slug>/NN.jpg, plus NN-1200.jpg and NN-1600.jpg for phones,
laptops and smaller screens. The first photo is the album cover and opens the album; pass
--cover NN to move photo NN to the front instead (or use set-cover later).
Adding an album whose slug already exists replaces it.

Each photo can have an "alt" text in albums.js (edit it by hand). Alt texts are
kept when an album is re-added, matched by photo position. Every save also writes
each album's own page at /photography/<slug>/, the search and share tags on
/photography/, the photo strip on the home page and sitemap.xml (see `pages`).

`sizes` creates any missing NN-1200.jpg, NN-1600.jpg, row thumbnail and share image
from the 2400px files in the repo.
`covers` regenerates cover.jpg (1600px), cover-400.jpg, cover-132.jpg (album row) and
share.jpg (1200x630 link preview) for every album.
`pages` rewrites the album pages, home strip, metadata and sitemap without touching photos.
`icc` swaps the 3 KB sRGB colour profile in existing JPEGs for a 456 B one that
describes the same colours (_build/srgb-v2-micro.icc, CC0). New photos get it automatically.

Needs Pillow. RAW/HEIC files are converted with macOS `sips` first.
"""
import argparse, datetime, glob, html, json, os, re, shutil, subprocess, sys, tempfile, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'photography', 'albums.js')
PHOTOS = os.path.join(REPO, 'photography', 'photos')
LONG_EDGE = 2400
MID_EDGE = 1200
EDGES = (1200, 1600)  # smaller files next to each 2400px NN.jpg, for srcset
ROW_EDGE = 132  # album row thumbnails are 44 CSS px, sharp up to 3x screens
SHARE_SIZE = (1200, 630)
COVER_EDGE = 1600
THUMB_EDGE = 400
QUALITY = 82
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic', '.heif',
             '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2'}
HEADER = '// Albums for /photography, newest first. Managed by _build/album.py; titles and alt texts can be edited by hand.\n'
COVERS = os.path.join(REPO, 'photography', 'covers.js')  # no longer used; removed if present
TEMPLATE = os.path.join(REPO, 'photography', 'index.html')
HOME = os.path.join(REPO, 'index.html')
SITE = 'https://www.cihankoseoglu.com'
MICRO_ICC = open(os.path.join(REPO, '_build', 'srgb-v2-micro.icc'), 'rb').read()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared  # noqa: E402


def load():
    if not os.path.exists(DATA):
        return []
    text = open(DATA, encoding='utf-8').read()
    return json.loads(text[text.index('['):text.rindex(']') + 1])


def save(albums):
    # Newest first, by the album's date ("2026-08"), falling back to its year.
    albums.sort(key=lambda x: x.get('date') or str(x.get('year') or ''), reverse=True)
    with open(DATA, 'w', encoding='utf-8') as fh:
        fh.write(HEADER + 'window.ALBUMS = ' + json.dumps(albums, indent=1, ensure_ascii=False) + ';\n')
    publish(albums)


def path_of(src):
    return os.path.join(REPO, src.lstrip('/'))


def mid_path(path, edge=MID_EDGE):
    return path[:-4] + f'-{edge}.jpg'


def is_srgb(icc):
    return b'sRGB' in icc[:1024] if icc else True


def compact_icc(icc):
    """The 456 B sRGB profile for sRGB (or untagged) photos; any other profile, such as Display P3, is kept."""
    return MICRO_ICC if is_srgb(icc) else icc


def save_jpeg(im, path, icc, edge=None, quality=QUALITY):
    """Resize (if edge is given) and save without any EXIF/GPS metadata; only the colour profile is kept."""
    from PIL import Image
    if edge:
        im = im.copy()
        im.thumbnail((edge, edge), Image.LANCZOS)
    im.save(path, 'JPEG', quality=quality, optimize=True, progressive=True, icc_profile=compact_icc(icc))
    return im


def make_sizes(path):
    """Write any missing NN-1200.jpg and NN-1600.jpg next to a 2400px NN.jpg. Returns how many were made."""
    from PIL import Image
    missing = [e for e in EDGES if not os.path.exists(mid_path(path, e))]
    if missing:
        im = Image.open(path)
        icc = im.info.get('icc_profile')
        im = im.convert('RGB')
        for e in missing:
            save_jpeg(im, mid_path(path, e), icc, e)
    return len(missing)


def swap_icc(path):
    """Replace an sRGB ICC profile in a JPEG with the compact one without touching the image data."""
    data = open(path, 'rb').read()
    if data[:2] != b'\xff\xd8':
        return False
    i, segs, icc = 2, [], b''
    while i < len(data) - 4 and data[i] == 0xFF and data[i + 1] not in (0xDA, 0xD9):
        n = int.from_bytes(data[i + 2:i + 4], 'big')
        seg = data[i:i + 2 + n]
        if data[i + 1] == 0xE2 and seg[4:16] == b'ICC_PROFILE\0':
            icc += seg[18:]
        else:
            segs.append(seg)
        i += 2 + n
    if not icc or icc == MICRO_ICC or not is_srgb(icc):
        return False
    app2 = b'\xff\xe2' + (2 + 14 + len(MICRO_ICC)).to_bytes(2, 'big') + b'ICC_PROFILE\0\x01\x01' + MICRO_ICC
    # Keep APP0 (JFIF) first, then the profile, then everything else as it was.
    head = [s for s in segs if s[1] == 0xE0]
    rest = [s for s in segs if s[1] != 0xE0]
    with open(path, 'wb') as fh:
        fh.write(b'\xff\xd8' + b''.join(head) + app2 + b''.join(rest) + data[i:])
    return True


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def guess_title(folder):
    # Prefer the nearest dated album folder ("2026-03 Madrid") within three levels up,
    # so ".../2026-03 Madrid/Exports/madrid" becomes "Madrid".
    path = os.path.normpath(folder)
    name = os.path.basename(path)
    for _ in range(3):
        if re.match(r'^20\d\d', os.path.basename(path)):
            name = os.path.basename(path)
            break
        path = os.path.dirname(path)
    t = re.sub(r'\s+', ' ', name.replace('_', ' ')).strip()
    t = re.sub(r'^[\d\s._-]+', '', t) or t  # drop a leading date like "2026-08 "
    return t[:1].upper() + t[1:]


def guess_date(folder):
    """"2026-03" from a folder named like "2026-03 Madrid" or "2026_03 ...", else None."""
    for part in reversed(os.path.normpath(folder).split(os.sep)):
        m = re.match(r'^(20\d\d)[\s._-]?(\d\d)?', part)
        if m:
            return m.group(1) + ('-' + m.group(2) if m.group(2) else '')
    return None


def guess_year(folder):
    m = re.findall(r'(?<!\d)(20\d\d)(?!\d)', folder)
    return int(m[-1]) if m else None


def source_dir(folder):
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        if os.path.isdir(p) and name.lower() == 'selected':
            return p
    return folder


def open_image(path, tmpdir):
    from PIL import Image
    try:
        im = Image.open(path)
        im.load()
        return im
    except Exception:
        out = os.path.join(tmpdir, os.path.basename(path) + '.jpg')
        subprocess.run(['sips', '-s', 'format', 'jpeg', path, '--out', out],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        im = Image.open(out)
        im.load()
        return im


def crop_to(im, w, h):
    """Centre-crop to the w:h shape and resize to exactly w x h."""
    from PIL import Image
    r = w / h
    if im.width / im.height > r:
        cw = round(im.height * r); box = ((im.width - cw) // 2, 0, (im.width - cw) // 2 + cw, im.height)
    else:
        ch = round(im.width / r); box = (0, (im.height - ch) // 2, im.width, (im.height - ch) // 2 + ch)
    return im.resize((w, h), Image.LANCZOS, box=box)


def make_cover(album, only_missing=False):
    """Write cover.jpg (1600px, album index), cover-400.jpg (home page), cover-132.jpg (album row, square)
    and share.jpg (1200x630 link preview) from the first photo."""
    from PIL import Image
    slug = album['slug']
    d = os.path.join(PHOTOS, slug)
    files = {'cover.jpg': None, 'cover-400.jpg': None, 'cover-132.jpg': None, 'share.jpg': None}
    todo = [f for f in files if not (only_missing and os.path.exists(os.path.join(d, f)))]
    if todo:
        im = Image.open(path_of(album['photos'][0]['src']))
        icc = im.info.get('icc_profile')
        im = im.convert('RGB')
        if 'cover.jpg' in todo:
            save_jpeg(im, os.path.join(d, 'cover.jpg'), icc, COVER_EDGE, 80)
        if 'cover-400.jpg' in todo:
            save_jpeg(im, os.path.join(d, 'cover-400.jpg'), icc, THUMB_EDGE, 78)
        if 'cover-132.jpg' in todo:
            save_jpeg(crop_to(im, ROW_EDGE, ROW_EDGE), os.path.join(d, 'cover-132.jpg'), icc, None, 78)
        if 'share.jpg' in todo:
            save_jpeg(crop_to(im, *SHARE_SIZE), os.path.join(d, 'share.jpg'), icc, None, 82)
    album['cover'] = f'/photography/photos/{slug}/cover.jpg'
    album['thumb'] = f'/photography/photos/{slug}/cover-400.jpg'
    album['row'] = f'/photography/photos/{slug}/cover-132.jpg'
    album['share'] = f'/photography/photos/{slug}/share.jpg'
    return len(todo)


def move_to_front(album, n):
    """Make photo number n (1-based, as shown in its caption) the first photo, renaming files to keep NN in order."""
    photos = album['photos']
    if not 1 <= n <= len(photos):
        sys.exit(f'Photo {n} does not exist; {album["slug"]} has {len(photos)} photos.')
    photos.insert(0, photos.pop(n - 1))
    slug = album['slug']
    renames = []
    for i, p in enumerate(photos, 1):
        old = path_of(p['src'])
        p['src'] = f'/photography/photos/{slug}/{i:02d}.jpg'
        renames.append((old, path_of(p['src'])))
    # Two passes through temporary names so nothing is overwritten.
    for old, new in renames:
        for a, b in [(old, new)] + [(mid_path(old, e), mid_path(new, e)) for e in EDGES]:
            if os.path.exists(a):
                os.rename(a, b + '.tmp')
    for old, new in renames:
        for b in [new] + [mid_path(new, e) for e in EDGES]:
            if os.path.exists(b + '.tmp'):
                os.rename(b + '.tmp', b)


def cmd_add(a):
    from PIL import Image, ImageOps
    folders = [os.path.abspath(os.path.expanduser(f)) for f in a.folder]
    sources = []  # (source dir, file name), folders in the order given, files in name order
    for folder in folders:
        if not os.path.isdir(folder):
            sys.exit(f'Not a folder: {folder}')
        src = source_dir(folder)
        sources += [(src, f) for f in sorted(os.listdir(src))
                    if not f.startswith('.') and os.path.splitext(f)[1].lower() in IMAGE_EXT]
    if not sources:
        sys.exit('No photos found in ' + ', '.join(folders))
    folder = folders[0]
    title = a.title or guess_title(folder)
    year = a.year or guess_year(folder)
    slug = a.slug or slugify(title)
    dest = os.path.join(PHOTOS, slug)
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    photos = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (src, f) in enumerate(sources, 1):
            im = open_image(os.path.join(src, f), tmp)
            icc = im.info.get('icc_profile')
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)
            name = f'{i:02d}.jpg'
            # No exif= argument, so no camera or GPS metadata is written; only the colour profile is kept.
            save_jpeg(im, os.path.join(dest, name), icc)
            for e in EDGES:
                save_jpeg(im, mid_path(os.path.join(dest, name), e), icc, e)
            photos.append({'src': f'/photography/photos/{slug}/{name}', 'w': im.width, 'h': im.height})
            print(f'  {i}/{len(sources)}', end='\r', flush=True)
    date = a.date or guess_date(folder) or (str(year) if year else None)
    album = {'slug': slug, 'title': title, 'year': year, 'date': date, 'photos': photos}
    albums = load()
    existing = [i for i, x in enumerate(albums) if x['slug'] == slug]
    if existing:  # keep hand-written alt texts, matched by position
        for p, old in zip(photos, albums[existing[0]]['photos']):
            if old.get('alt'):
                p['alt'] = old['alt']
    if a.cover:
        move_to_front(album, a.cover)
    make_cover(album)
    if existing:
        albums[existing[0]] = album
    else:
        albums.append(album)
    save(albums)
    size = sum(os.path.getsize(os.path.join(dest, f)) for f in os.listdir(dest))
    print(f'{"Replaced" if existing else "Added"} "{title}" ({year}): {len(photos)} photos from {len(folders)} folder(s), {size / 1e6:.1f} MB')


def cmd_remove(a):
    albums = load()
    keep = [x for x in albums if x['slug'] != a.slug]
    if len(keep) == len(albums):
        sys.exit(f'No album with slug {a.slug}. Run "list" to see them.')
    save(keep)
    shutil.rmtree(os.path.join(PHOTOS, a.slug), ignore_errors=True)
    print(f'Removed {a.slug}')


def cmd_rename(a):
    albums = load()
    for x in albums:
        if x['slug'] == a.slug:
            x['title'] = a.title
            save(albums)
            print(f'Renamed {a.slug} to "{a.title}"')
            return
    sys.exit(f'No album with slug {a.slug}.')


def find(albums, slug):
    for x in albums:
        if x['slug'] == slug:
            return x
    sys.exit(f'No album with slug {slug}. Run "list" to see them.')


def cmd_set_cover(a):
    albums = load()
    album = find(albums, a.slug)
    move_to_front(album, a.number)
    make_cover(album)
    save(albums)
    print(f'Photo {a.number} is now the cover of {a.slug}')


def cmd_sizes(a):
    made = 0
    albums = load()
    for x in albums:
        for p in x['photos']:
            made += make_sizes(path_of(p['src']))
        made += make_cover(x, only_missing=True)
    save(albums)
    print(f'Made {made} files')


def cmd_icc(a):
    n = 0
    for path in sorted(glob.glob(os.path.join(PHOTOS, '*', '*.jpg'))):
        n += swap_icc(path)
    print(f'Swapped the colour profile in {n} files')


def cmd_pages(a):
    publish(load())
    print('Album pages, home strip, metadata and sitemap written')


# ---- Pages: /photography/ metadata, one page per album, the home page strip ----

def esc(s):
    return html.escape(str(s), quote=True)


def month(album):
    d = album.get('date') or ''
    if re.match(r'^\d{4}-\d{2}$', d):
        return datetime.date(int(d[:4]), int(d[5:]), 1).strftime('%B %Y')
    return str(album.get('year') or '')


def count(n):
    return f'{n} photo' + ('' if n == 1 else 's')


def srcset(p):
    long = max(p['w'], p['h'])
    out = [f'{p["src"][:-4]}-{e}.jpg {round(p["w"] * e / long)}w' for e in EDGES if long > e]
    return ', '.join(out + [f'{p["src"]} {p["w"]}w'])


PERSON = {'@type': 'Person', '@id': SITE + '/#person', 'name': 'Cihan Koseoglu', 'url': SITE + '/'}


def head_block(album, albums):
    """The tags between meta:start and meta:end for /photography/ (album=None) or one album."""
    if album:
        url = f'{SITE}/photography/{album["slug"]}/'
        title = f'{album["title"]} · Photography · Cihan Koseoglu'
        desc = f'{album["title"]}: {count(len(album["photos"]))} by Cihan Koseoglu, {month(album)}.'
        share = album.get('share') or album['cover']
        first = album['photos'][0]
        r = first['w'] / first['h']
        preload = (f'  <link rel="preload" as="image" href="{first["src"]}" imagesrcset="{srcset(first)}" '
                   f'imagesizes="max(100vw, calc(92vh * {r:.4f}))" fetchpriority="high">\n')
        ld = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'ImageGallery', '@id': url, 'url': url, 'name': album['title'], 'description': desc,
             'author': PERSON, 'datePublished': album.get('date') or str(album.get('year') or ''),
             'image': [{'@type': 'ImageObject', 'contentUrl': SITE + p['src'], 'width': p['w'], 'height': p['h'],
                        **({'caption': p['alt']} if p.get('alt') else {}),
                        'creator': PERSON, 'copyrightNotice': 'Cihan Koseoglu'} for p in album['photos']]},
            {'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Cihan Koseoglu', 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Photography', 'item': SITE + '/photography/'},
                {'@type': 'ListItem', 'position': 3, 'name': album['title'], 'item': url}]}]}
        og_title = album['title']
    else:
        url = f'{SITE}/photography/'
        title = 'Photography · Cihan Koseoglu'
        names = [x['title'] for x in albums]
        desc = 'Photography by Cihan Koseoglu' + (': ' + ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else
                                                    (': ' + names[0] if names else '')) + '.'
        share = albums[0].get('share') or albums[0]['cover'] if albums else '/apple-touch-icon.png'
        preload = ''
        if albums:
            a, p = albums[0], albums[0]['photos'][0]
            preload = (f'  <link rel="preload" as="image" href="{a["cover"]}" imagesrcset="{a["thumb"]} '
                       f'{round(400 * min(1, p["w"] / p["h"]))}w, {a["cover"]} {round(1600 * min(1, p["w"] / p["h"]))}w" '
                       f'imagesizes="calc(100vw - 32px)" fetchpriority="high">\n')
        ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', '@id': url, 'url': url, 'name': 'Photography',
              'description': desc, 'author': PERSON,
              'hasPart': [{'@type': 'ImageGallery', 'name': x['title'], 'url': f'{SITE}/photography/{x["slug"]}/'} for x in albums]}
        og_title = 'Photography'
    return (f'  <title>{esc(title)}</title>\n'
            f'  <meta name="description" content="{esc(desc)}">\n'
            f'  <meta name="robots" content="max-image-preview:large">\n'
            f'  <link rel="canonical" href="{url}">\n'
            f'  <meta property="og:title" content="{esc(og_title)}">\n'
            f'  <meta property="og:description" content="{esc(desc)}">\n'
            f'  <meta property="og:url" content="{url}">\n'
            f'  <meta property="og:type" content="website">\n'
            f'  <meta property="og:site_name" content="Cihan Koseoglu">\n'
            f'  <meta property="og:image" content="{SITE}{share}">\n'
            f'  <meta property="og:image:width" content="{SHARE_SIZE[0]}">\n'
            f'  <meta property="og:image:height" content="{SHARE_SIZE[1]}">\n'
            f'  <meta name="twitter:card" content="summary_large_image">\n'
            + preload +
            f'  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')


def replace_block(text, name, block, path):
    m = re.search(rf'( *)<!-- {name}:start.*?-->\n(.*?)( *)<!-- {name}:end -->', text, re.S)
    if not m:
        sys.exit(f'{path} has no <!-- {name}:start --> / <!-- {name}:end --> markers')
    return text[:m.start(2)] + block + text[m.start(3):]


def home_strip(albums):
    imgs = ''.join(f'<img src="{esc(x.get("thumb") or x["cover"])}" alt="" loading="lazy">' for x in albums[:4])
    n = sum(len(x['photos']) for x in albums)
    return (f'        <div id="photoStrip" class="photo-strip" aria-hidden="true">{imgs}</div>\n'
            f'        <div class="photo-cta">\n'
            f'          <span class="photo-title">See the albums</span>\n'
            f'          <span id="photoMeta" class="photo-meta">{len(albums)} albums, {n} photos</span>\n'
            f'          <span class="photo-arrow" aria-hidden="true">&rarr;</span>\n'
            f'        </div>\n')


def publish(albums):
    template = shared.read(TEMPLATE)
    shared.write(TEMPLATE, replace_block(template, 'meta', head_block(None, albums), TEMPLATE))
    template = shared.read(TEMPLATE)
    slugs = {x['slug'] for x in albums}
    # Remove pages of albums that no longer exist (only folders this script made).
    for d in glob.glob(os.path.join(REPO, 'photography', '*', 'index.html')):
        if os.path.basename(os.path.dirname(d)) not in slugs and 'album-page' in shared.read(d):
            shutil.rmtree(os.path.dirname(d))
    for x in albums:
        page = replace_block(template, 'meta', head_block(x, albums), TEMPLATE)
        page = page.replace('<html lang="en">', '<html lang="en" class="album-page">', 1)
        shared.write(os.path.join(REPO, 'photography', x['slug'], 'index.html'), page)
    home = shared.read(HOME)
    shared.write(HOME, replace_block(home, 'strip', home_strip(albums), HOME))
    if os.path.exists(COVERS):
        os.remove(COVERS)
    # The home page and notes use the newest album's link preview image.
    if albums and os.path.exists(path_of(albums[0].get('share') or '')):
        shutil.copyfile(path_of(albums[0]['share']), os.path.join(REPO, 'images', 'share.jpg'))
    shared.build()


def cmd_covers(a):
    albums = load()
    for x in albums:
        make_cover(x)
        print(f'Cover for {x["slug"]}')
    save(albums)


def cmd_list(a):
    for x in load():
        print(f'{x["slug"]:32} {x.get("date") or x["year"]}  {x["title"]}, {len(x["photos"])} photos')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('add'); p.add_argument('folder', nargs='+', help='one or more photo folders, combined in this order'); p.add_argument('--title'); p.add_argument('--year', type=int)
    p.add_argument('--slug'); p.add_argument('--date', help='YYYY-MM, used for ordering')
    p.add_argument('--cover', type=int, metavar='NN', help='use photo NN as the cover (it opens the album)'); p.set_defaults(f=cmd_add)
    p = sub.add_parser('remove'); p.add_argument('slug'); p.set_defaults(f=cmd_remove)
    p = sub.add_parser('rename'); p.add_argument('slug'); p.add_argument('title'); p.set_defaults(f=cmd_rename)
    p = sub.add_parser('list'); p.set_defaults(f=cmd_list)
    p = sub.add_parser('set-cover', help='make photo NN the cover and first photo of an album')
    p.add_argument('slug'); p.add_argument('number', type=int, metavar='NN'); p.set_defaults(f=cmd_set_cover)
    p = sub.add_parser('covers', help='regenerate cover.jpg, cover-400.jpg, cover-132.jpg and share.jpg for every album'); p.set_defaults(f=cmd_covers)
    p = sub.add_parser('sizes', help='create missing NN-1200.jpg/NN-1600.jpg, row thumbnails and share images'); p.set_defaults(f=cmd_sizes)
    p = sub.add_parser('pages', help='rewrite album pages, home strip, metadata and sitemap'); p.set_defaults(f=cmd_pages)
    p = sub.add_parser('icc', help='swap the 3 KB sRGB profile in existing JPEGs for the 456 B one'); p.set_defaults(f=cmd_icc)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
