# Can Web Surfer embed SearxNG?

**Short answer:** not as a Python import inside the WebView, but yes as a
bundled local service that the browser starts for the user.

## What SearxNG actually is

SearxNG is a metasearch *web application* (Flask + engines + templates). It is
not published as a small library on PyPI. It speaks HTTP, usually on
`127.0.0.1:8888`. License: **AGPL-3.0-or-later**.

A lay person should not have to install Docker or edit `settings.yml`. That
means Web Surfer has to do the ops work.

## Practical approaches (best first)

### 1. Bundle and launch a local instance (recommended)

On first run, Web Surfer would:

1. Unpack or install a known SearxNG version next to the app data dir.
2. Write a private `settings.yml` (`bind_address: 127.0.0.1`, `limiter: false`,
   `formats: [html, json]`, generated `secret_key`).
3. Start `python -m searx.webapp` (or a small Docker/Podman container if present).
4. Set `HOMEPAGE` / `SEARCH_URL` to `http://127.0.0.1:<port>/`.
5. Stop that process when the browser exits.

This is the same pattern used by apps that ship “local SearxNG”: a **separate
process**, talked to over HTTP. The user just opens Web Surfer.

**Costs:** extra Python deps (lxml, httpx, etc.), a few hundred MB of engines
and templates, slower first launch, you must ship SearxNG source (AGPL).

### 2. Default to a public instance, optional local

Simplest for 0.2: `SEARCH_URL` points at a public instance from
[searx.space](https://searx.space), with a setting “use my local SearxNG” later.

Not “embedded,” but zero setup.

### 3. True in-process embed (`import searx`)

Technically possible, legally and operationally painful:

- You pull the entire webapp into Web Surfer’s process.
- AGPL almost certainly applies to the **combined program**.
- You still need all of SearxNG’s templates, settings, and outbound HTTP.

Not worth it versus spawning the official webapp.

## License note

GPLv3 for Web Surfer is compatible with keeping SearxNG as a **separate AGPL
program** started on localhost (mere aggregation over HTTP). If you later
merge SearxNG code into Web Surfer’s own modules, consider relicensing the
combined work as **AGPL-3.0-or-later** so the network copyleft stays intact.

Donations do not conflict with GPL/AGPL.
