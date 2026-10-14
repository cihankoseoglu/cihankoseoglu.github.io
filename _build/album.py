#!/usr/bin/env python3
"""Manage the albums on cihankoseoglu.com/photography.

  python3 _build/album.py list
  python3 _build/album.py add "/path/to/photos" ["/another/folder" ...] [--title "Name"] [--year 2026] [--date 2026-03] [--cover NN]
  python3 _build/album.py remove <slug>
  python3 _build/album.py rename <slug> "New Title"
  python3 _build/album.py set-cover <slug> NN
  python3 _build/album.py covers
  python3 _build/album.py sizes

`add` takes one or more folders of photos (combined into one album). If a folder has a "selected" subfolder, only
that is used. Photos are taken in file-name order, resized to 2400px on the
long edge, saved as JPEG with all metadata (including GPS) removed, and written
to photography/photos/<slug>/NN.jpg, plus NN-1200.jpg (1200px) for phones and
smaller screens. The first photo is the album cover and opens the album; pass
--cover NN to move photo NN to the front instead (or use set-cover later).
Adding an album whose slug already exists replaces it.

Each photo can have an "alt" text in albums.js (edit it by hand). Alt texts are
kept when an album is re-added, matched by photo position. Every save also
writes photography/covers.js, a small list the home page uses.

`sizes` creates any missing NN-1200.jpg files from the 2400px files in the repo.
`covers` regenerates cover.jpg (1600px) and cover-400.jpg for every album.

Needs Pillow. RAW/HEIC files are converted with macOS `sips` first.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'photography', 'albums.js')
PHOTOS = os.path.join(REPO, 'photography', 'photos')
LONG_EDGE = 2400
MID_EDGE = 1200
COVER_EDGE = 1600
THUMB_EDGE = 400
QUALITY = 82
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic', '.heif',
             '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2'}
HEADER = '// Albums for /photography, newest first. Managed by _build/album.py; titles and alt texts can be edited by hand.\n'
COVERS = os.path.join(REPO, 'photography', 'covers.js')
COVERS_HEADER = '// Written by _build/album.py from albums.js: one line per album for the home page. Do not edit.\n'


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
    covers = [{'slug': x['slug'], 'title': x['title'], 'year': x.get('year'), 'cover': x.get('cover'),
               'thumb': x.get('thumb'), 'count': len(x['photos'])} for x in albums]
    with open(COVERS, 'w', encoding='utf-8') as fh:
        fh.write(COVERS_HEADER + 'window.ALBUM_COVERS = [\n' +
                 ',\n'.join(' ' + json.dumps(c, ensure_ascii=False) for c in covers) + '\n];\n')


def path_of(src):
    return os.path.join(REPO, src.lstrip('/'))


def mid_path(path):
    return path[:-4] + '-1200.jpg'


def save_jpeg(im, path, icc, edge=None, quality=QUALITY):
    """Resize (if edge is given) and save without any EXIF/GPS metadata; only the colour profile is kept."""
    from PIL import Image
    if edge:
        im = im.copy()
        im.thumbnail((edge, edge), Image.LANCZOS)
    im.save(path, 'JPEG', quality=quality, optimize=True, progressive=True, icc_profile=icc)
    return im


def make_mid(path):
    """Write NN-1200.jpg next to a 2400px NN.jpg."""
    from PIL import Image
    im = Image.open(path)
    icc = im.info.get('icc_profile')
    save_jpeg(im.convert('RGB'), mid_path(path), icc, MID_EDGE)


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


def make_cover(album):
    """Write cover.jpg (1600px, album index) and cover-400.jpg (home page and album row) from the first photo."""
    from PIL import Image
    slug = album['slug']
    im = Image.open(path_of(album['photos'][0]['src']))
    icc = im.info.get('icc_profile')
    im = im.convert('RGB')
    save_jpeg(im, os.path.join(PHOTOS, slug, 'cover.jpg'), icc, COVER_EDGE, 80)
    save_jpeg(im, os.path.join(PHOTOS, slug, 'cover-400.jpg'), icc, THUMB_EDGE, 78)
    album['cover'] = f'/photography/photos/{slug}/cover.jpg'
    album['thumb'] = f'/photography/photos/{slug}/cover-400.jpg'


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
        for a, b in ((old, new), (mid_path(old), mid_path(new))):
            if os.path.exists(a):
                os.rename(a, b + '.tmp')
    for old, new in renames:
        for b in (new, mid_path(new)):
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
            save_jpeg(im, mid_path(os.path.join(dest, name)), icc, MID_EDGE)
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
    for x in load():
        for p in x['photos']:
            path = path_of(p['src'])
            if not os.path.exists(mid_path(path)):
                make_mid(path)
                made += 1
    print(f'Made {made} 1200px files')


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
    p = sub.add_parser('covers', help='regenerate cover.jpg and cover-400.jpg for every album'); p.set_defaults(f=cmd_covers)
    p = sub.add_parser('sizes', help='create missing NN-1200.jpg files for existing albums'); p.set_defaults(f=cmd_sizes)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
