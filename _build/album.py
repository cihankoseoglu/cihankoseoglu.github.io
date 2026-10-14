#!/usr/bin/env python3
"""Manage the albums on cihankoseoglu.com/photography.

  python3 _build/album.py list
  python3 _build/album.py add "/path/to/photos" ["/another/folder" ...] [--title "Name"] [--year 2026] [--date 2026-03]
  python3 _build/album.py remove <slug>
  python3 _build/album.py rename <slug> "New Title"
  python3 _build/album.py covers

`add` takes one or more folders of photos (combined into one album). If a folder has a "selected" subfolder, only
that is used. Photos are taken in file-name order, resized to 2400px on the
long edge, saved as JPEG with all metadata (including GPS) removed, and written
to photography/photos/<slug>/NN.jpg. The first photo is the album cover.
Adding an album whose slug already exists replaces it.

Needs Pillow. RAW/HEIC files are converted with macOS `sips` first.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'photography', 'albums.js')
PHOTOS = os.path.join(REPO, 'photography', 'photos')
LONG_EDGE = 2400
COVER_EDGE = 900
QUALITY = 82
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic', '.heif',
             '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2'}
HEADER = '// Albums for /photography, newest first. Managed by _build/album.py; titles can be edited by hand.\n'


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
    """Write a small cover.jpg (from the first photo) for the home page strip and set album["cover"]."""
    from PIL import Image
    slug = album['slug']
    im = Image.open(os.path.join(REPO, album['photos'][0]['src'].lstrip('/')))
    icc = im.info.get('icc_profile')
    im = im.convert('RGB')
    im.thumbnail((COVER_EDGE, COVER_EDGE), Image.LANCZOS)
    im.save(os.path.join(PHOTOS, slug, 'cover.jpg'), 'JPEG', quality=80, optimize=True, progressive=True, icc_profile=icc)
    album['cover'] = f'/photography/photos/{slug}/cover.jpg'


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
            im.save(os.path.join(dest, name), 'JPEG', quality=QUALITY, optimize=True, progressive=True, icc_profile=icc)
            photos.append({'src': f'/photography/photos/{slug}/{name}', 'w': im.width, 'h': im.height})
            print(f'  {i}/{len(sources)}', end='\r', flush=True)
    date = a.date or guess_date(folder) or (str(year) if year else None)
    album = {'slug': slug, 'title': title, 'year': year, 'date': date, 'photos': photos}
    make_cover(album)
    albums = load()
    existing = [i for i, x in enumerate(albums) if x['slug'] == slug]
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
    p.add_argument('--slug'); p.add_argument('--date', help='YYYY-MM, used for ordering'); p.set_defaults(f=cmd_add)
    p = sub.add_parser('remove'); p.add_argument('slug'); p.set_defaults(f=cmd_remove)
    p = sub.add_parser('rename'); p.add_argument('slug'); p.add_argument('title'); p.set_defaults(f=cmd_rename)
    p = sub.add_parser('list'); p.set_defaults(f=cmd_list)
    p = sub.add_parser('covers', help='regenerate cover.jpg for every album'); p.set_defaults(f=cmd_covers)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
