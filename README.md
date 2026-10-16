# cihankoseoglu.com

My personal website, served with GitHub Pages from the `master` branch at [www.cihankoseoglu.com](https://www.cihankoseoglu.com).

Plain HTML, CSS and JavaScript with no build step:

- `index.html`: the home page
- `photography/`: photo albums (add or remove them with `python3 _build/album.py`)
- `notes/`: short writing, built from markdown in `_build/notes/` with `python3 _build/notes.py`
- `css/site.css` and `js/gtag.js`: shared colours, fonts, base type and the Google tag. They are
  inlined into every page by `python3 _build/shared.py` (album.py and notes.py run it too), so
  run that after editing either file
- `fonts/`: Latin subsets of Iosevka (rebuild with `_build/fonts.sh`); `fonts/full/` has the complete files
- `js/site.js`: cookie banner, analytics events and a small easter egg; `js/life.js`: the Game of Life header
- `.github/workflows/pages.yml`: the deploy, which keeps each file's last-commit date so caches survive deploys

To preview locally, run `python3 -m http.server 8000` in this folder and open http://localhost:8000.

Photos stay in this repo until the `photography/photos` folder passes about 300 MB, then they move to Cloudflare R2.
