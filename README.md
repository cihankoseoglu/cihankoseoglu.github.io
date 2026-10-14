# cihankoseoglu.com

My personal website, served with GitHub Pages from the `master` branch at [www.cihankoseoglu.com](https://www.cihankoseoglu.com).

Plain HTML, CSS and JavaScript with no build step:

- `index.html`: the home page
- `photography/`: photo albums (add or remove them with `python3 _build/album.py`)
- `notes/`: short writing, built from markdown in `_build/notes/` with `python3 _build/notes.py`
- `css/site.css` and `fonts/`: shared colours, self-hosted fonts and base type
- `js/`: Game of Life header, analytics events, cookie banner and a small easter egg

To preview locally, run `python3 -m http.server 8000` in this folder and open http://localhost:8000.

Photos stay in this repo until the `photography/photos` folder passes about 300 MB, then they move to Cloudflare R2.
