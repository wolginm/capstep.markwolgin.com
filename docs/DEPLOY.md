# Deploying the site

The site is a static build: `web/dist/` holds an `index.html`, content-hashed files in
`assets/`, and the catalog, bibliography and AI-usage log in `data/`. It uses
relative paths and hash-based routes (`/#/song/401k`), so the same build works at a
domain root or under any sub-path, with no server rewrite rules [VITE-STATIC-DEPLOY]
[REACT-ROUTER-HASHROUTER].

No audio is ever deployed. The player streams each recording from its Wayback
Machine capture, and only when the listener presses play.

## Option 1: GitHub Pages (automatic)

`.github/workflows/deploy.yml` runs every check and test on each push and pull
request. On `main` it then deploys `web/dist/` to Pages [GH-PAGES-CUSTOM-WORKFLOW].

One-time setup, done by the developer:

1. Create an empty repository on GitHub (done: `wolginm/capstep.markwolgin.com`), then
   add it as a remote and push:
   ```bash
   git remote add origin git@github.com:wolginm/capstep.markwolgin.com.git
   git push -u origin main
   ```
2. In the repository, open **Settings → Pages** and set **Source** to
   **GitHub Actions** [GH-PAGES-PUBLISHING-SOURCE].
3. Re-run the "CI and deploy" workflow from the **Actions** tab, or push again. The site
   appears at `https://wolginm.github.io/capstep.markwolgin.com/` until the custom domain
   below is set up. The deploy job's summary links to it.
4. *Recommended:* GitHub creates the `github-pages` environment on the first deploy.
   Under **Settings → Environments → github-pages**, add a deployment branch rule
   allowing only `main` [GH-PAGES-CUSTOM-WORKFLOW].

The workflow itself deploys only from `main`. Pull requests and runs on other
branches go through the checks but never deploy. The branch rule in step 4 enforces the
same on GitHub's side.

### Custom domain: `capstep.markwolgin.com`

The site is served at **<https://capstep.markwolgin.com/>**. Because the build uses
relative paths, moving from `wolginm.github.io/capstep.markwolgin.com/` to the domain root needs no
rebuild and no code change. Because the site deploys through a custom Actions
workflow, **no `CNAME` file is needed** in the repository. GitHub ignores one if it
exists. The domain is a repository setting [GH-PAGES-CUSTOM-DOMAIN].

Follow these steps in order. GitHub warns that creating the DNS record before the
domain is added to a site lets someone else claim the subdomain
[GH-PAGES-CUSTOM-DOMAIN].

1. **Verify `markwolgin.com` (recommended, once per account).** Open your GitHub
   **profile Settings → Pages → Add a domain**, enter `markwolgin.com`, and add the TXT
   record GitHub shows at your DNS provider. The record is named
   `_github-pages-challenge-wolginm.markwolgin.com`. Keep the record in place
   afterward. Verification stops other GitHub accounts from taking over the domain, and
   it covers immediate subdomains such as `capstep` [GH-PAGES-VERIFY-DOMAIN]:
   ```bash
   dig _github-pages-challenge-wolginm.markwolgin.com +nostats +nocomments +nocmd TXT
   ```
2. **Add the domain to the repository.** **Settings → Pages → Custom domain**: enter
   `capstep.markwolgin.com` and click **Save** [GH-PAGES-CUSTOM-DOMAIN].
3. **Create the DNS record** at the DNS provider for `markwolgin.com`
   [GH-PAGES-CUSTOM-DOMAIN]:

   | Type | Name (host) | Value |
   |---|---|---|
   | `CNAME` | `capstep` | `wolginm.github.io` |

   Use the account's `github.io` name with no repository path. Do not use the
   `*.pages.github.io` name shown in Pages settings, and do not add a wildcard
   (`*.markwolgin.com`) record. If the domain has CAA records, one of them must allow
   `letsencrypt.org` [GH-PAGES-DOMAIN-TROUBLESHOOTING]. Check the record:
   ```bash
   dig capstep.markwolgin.com +nostats +nocomments +nocmd   # should show wolginm.github.io
   ```
   DNS changes can take up to 24 hours to propagate [GH-PAGES-CUSTOM-DOMAIN].
4. **Enforce HTTPS.** Once the DNS check in **Settings → Pages** passes, select
   **Enforce HTTPS** [GH-PAGES-HTTPS]. The certificate can take up to an hour to be
   issued [GH-PAGES-DOMAIN-TROUBLESHOOTING]. If it is still missing after that,
   remove the custom domain, save it again, and wait [GH-PAGES-HTTPS].

Enforcing HTTPS causes no mixed-content warnings [GH-PAGES-HTTPS]. The site loads only
its own files and `https://web.archive.org/` URLs. The catalog's `http://` capsteps.com
addresses appear only inside those Wayback URLs, or as displayed file names.

### Monthly link check

`.github/workflows/links.yml` runs `tools/check_links.py` at 14:17 UTC on the 1st of
each month, and on demand from the Actions tab [GH-ACTIONS-EVENTS]. Each run checks
20 randomly sampled recordings and every reference URL, one request per second. The
seed is printed in the log, so a failure can be reproduced locally:

```bash
python3 tools/check_links.py --seed <seed from the log>
```

A failed run triggers GitHub's normal failure email. GitHub **disables scheduled
workflows in public repositories after 60 days without repository activity**. If that
happens, re-enable "Monthly link check" from the Actions tab [GH-ACTIONS-EVENTS].

## Option 2: Self-hosted

Build the site (Node 24, see `.nvmrc`):

```bash
cd web
npm ci
npm run build        # copies data/ into the build, type-checks, writes web/dist/
npm run preview      # optional: serve dist/ locally at http://localhost:4173/
```

Copy the *contents* of `web/dist/` to the web server, e.g.

```bash
rsync -a --delete web/dist/ user@server:/var/www/capitol-steps/
```

Then point any static web server at that directory. Two samples are included:

- [`deploy/nginx.conf`](../deploy/nginx.conf): an nginx `server` block [NGINX-CORE]
- [`deploy/Caddyfile`](../deploy/Caddyfile): Caddy, with automatic HTTPS [CADDY-FILE-SERVER]

Both set the same cache policy [MDN-CACHE-CONTROL]:

| Path | Cache-Control | Why |
|---|---|---|
| `/assets/*` | `public, max-age=31536000, immutable` | File names contain a content hash; a new build gets new names |
| everything else (`index.html`, `/data/*`) | `no-cache` | Browsers revalidate, so a new build or catalog shows up at once |

Check a running server with:

```bash
curl -sI http://<host>/ | grep -i cache-control              # no-cache
curl -sI http://<host>/data/catalog.json | grep -i cache-control
curl -sI http://<host>/assets/<file from dist/assets> | grep -i cache-control   # immutable
```

**Serving under a sub-path** (e.g. `https://example.org/capitol-steps/`): no rebuild
is needed. Place the files in that directory under the document root and prefix the
location paths in the sample (e.g. nginx `location /capitol-steps/assets/`, Caddy
`path /capitol-steps/assets/*`).

## Updating the catalog

The catalog only changes when ingestion is re-run (see the README). Commit the new
`data/catalog.json`. On GitHub Pages the push redeploys the site. When self-hosting,
rebuild and copy `web/dist/` again.
