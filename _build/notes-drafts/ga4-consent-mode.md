---
title: GA4 Consent Mode, in plain words
date: 2026-10-20
description: What Consent Mode does, what it doesn't do, and how this site uses it.
---

DRAFT, written by Claude for Cihan to edit. Not published: drafts in _build/notes-drafts/ are never built.
To publish, rewrite it in your own words, delete this paragraph, set the date, move the file to
_build/notes/ and run python3 _build/notes.py.

Most cookie banners ask a question and then quietly ignore the answer. Consent Mode is Google's way
of making the answer actually change what the tags do.

## The short version

Consent Mode is a set of switches that Google tags (gtag.js, Google Tag Manager) read before they do
anything. Each switch is either `granted` or `denied`:

- `analytics_storage`: may Analytics set and read its cookies?
- `ad_storage`: may advertising tags set and read their cookies?
- `ad_user_data`: may user data be sent to Google for advertising?
- `ad_personalization`: may it be used for personalised ads, like remarketing?

You set a default when the page loads, and you update it when the visitor answers your banner.

## Default first, then the tag

The order matters. The default has to be set before the Google tag is configured, otherwise the tag
has already started with cookies on. On this site the first script in the page sets everything to
`denied` (or `granted` for analytics, if you said yes on an earlier visit), and only then loads GA4.

When you click Accept, the banner calls `gtag('consent', 'update', { analytics_storage: 'granted' })`
and remembers your choice. Decline stores `denied` and nothing changes.

## What happens when consent is denied

This is the part that surprises people. With the tag loaded and consent denied, GA4 still sends
pings, but without cookies: no client ID that survives the page, nothing stored on your device. Google
calls this "advanced" Consent Mode. The "basic" setup doesn't load the tag at all until someone accepts.

Those cookieless pings feed GA4's behavioural modelling, which estimates what the people who said no
probably did, based on the people who said yes. It only kicks in on properties with enough traffic,
so on a small personal site you mostly just see fewer, cleaner numbers.

## What it doesn't do

- It doesn't make a site compliant on its own. The banner, the wording and what you do with the data
  are still on you.
- It doesn't block other scripts. Only tags that understand Consent Mode listen to it.
- It doesn't bring back the people who declined. Modelled data is an estimate, not a recount.

## Why I bother on a personal site

TODO: your reason, in your words.
