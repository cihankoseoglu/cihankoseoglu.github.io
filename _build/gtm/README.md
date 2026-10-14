# GTM container: GA4 site events

`GTM-P5KM7P2-ga4.json` is a full GTM container for GTM-P5KM7P2 that sends everything to one GA4 property, G-1LPFGZTQRZ. The site code that feeds it is `/js/analytics.js`.

## What it contains

| Tag | Fires on | Sends |
| --- | --- | --- |
| Google Tag - GA4 | Initialization - All Pages | `page_view` |
| GA4 Event - Site events | dataLayer `select_content`, `album_view`, `album_progress`, `game_of_life_play` | the event with its parameters (below) |
| GA4 Event - konami_code | dataLayer `konamiCodeInitiated` | `konami_code` |
| cHTML - Konami Code Listener | All Pages | pushes `konamiCodeInitiated` when someone types ↑↑↓↓←→←→BA |
| cHTML - Konami Rickroll | dataLayer `konamiCodeInitiated` | the easter egg, unchanged |

Events and parameters:

| Event | When | Parameters |
| --- | --- | --- |
| `select_content` (GA4 recommended) | click on an album cover, "Next album", the home photo strip, or a social link | `content_type` (album, photography_index, social_profile), `content_id` (album slug, photography, x/youtube/linkedin), `link_location` (album_index, next_album, home_strip, say_hi), `social_platform` |
| `album_view` | an album opens | `album_id`, `album_title`, `album_date`, `photo_count` |
| `album_progress` | 25/50/75/90% through an album, once each | `album_id`, `album_title`, `percent_scrolled` |
| `game_of_life_play` | first draw on the home page Game of Life | `content_type`, `content_id` |
| `konami_code` | Konami code typed | none |

Scrolls, outbound clicks and file downloads come from GA4 enhanced measurement, so they are not tagged here.

## Importing

1. GTM > Admin > Import Container, choose `GTM-P5KM7P2-ga4.json`.
2. Workspace: **New** (e.g. "GA4 events").
3. Import option: **Overwrite**. This replaces the old container: the dead Universal Analytics tags, the broken "+90" Google tag, the placeholder purchase / Google Ads tags, and the Google tags for G-8BT93CCKZJ and G-JPRJ9JSMS3 are removed. Use **Merge > Rename conflicting** instead if you want to keep them and delete by hand.
4. Preview with Tag Assistant on the site (after the `ga4-events` branch is live), open an album, scroll, click a social link, then Submit > Publish.

## In GA4 (G-1LPFGZTQRZ)

- Admin > Data streams > web stream > Enhanced measurement: keep Page views (and "Page changes based on browser history events"), Scrolls, Outbound clicks and File downloads on.
- Admin > Custom definitions > Create custom dimensions (event scope) for: `album_id`, `album_title`, `album_date`, `link_location`, `social_platform`, `percent_scrolled`. Optionally a custom metric for `photo_count`. `content_type` and `content_id` are built in.
- Optionally mark `album_view` as a key event.
