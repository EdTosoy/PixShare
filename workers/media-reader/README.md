# PixShare media reader

Small read-only Worker for the existing `pixshare-media-reader` service. The
`MEDIA` binding targets the existing private R2 bucket `pixshare-media`. No S3
credentials, secrets, frameworks, runtime dependencies or bucket provisioning
are needed. Keep the bucket's public development URL and public bucket domains
disabled; public image access goes through this Worker only.

## Storage contract

The allowlist follows `app/storage/s3.py`, `app/storage/variants.py` and the
default `s3_prefix` in `app/core/config.py`:

```text
/pixshare/media/<32 lowercase hexadecimal characters>/original.jpg
/pixshare/media/<32 lowercase hexadecimal characters>/original.png
/pixshare/media/<32 lowercase hexadecimal characters>/original.webp
/pixshare/media/<32 lowercase hexadecimal characters>/variants/v1-<edge>.webp
```

`edge` is an integer from 1 to 1920 without leading zeroes. The encoder uses
320/640/1280/1920 maximum edges, but smaller originals produce other edge values.
The backend must use `S3_PREFIX=pixshare/media`; a different prefix or future
variant version requires an explicit Worker allowlist update. The backend's
`S3_PUBLIC_BASE_URL` must be the image origin without an appended key prefix:
`S3Storage.object_url()` already appends the entire `pixshare/media/...` key.

GET streams the original R2 bytes; HEAD uses `head()` without fetching the body.
Both return the MIME type derived from the permitted extension, the object size,
quoted ETag and `X-Content-Type-Options: nosniff`. They use the backend's existing
`public, max-age=31536000, immutable` cache policy. Images can remain in browser
caches after deletion. This does not add a Cloudflare Cache API layer or promise
edge cache hits, and does not implement range or conditional requests.

Query strings are ignored for object selection. Encoded/noncanonical paths,
unknown keys and manifests return 404 before accessing R2. The handler never
decodes paths or normalizes traversal. Browsers/platforms may normalize dot
segments before the handler receives a URL; the resulting path still has to
match the complete image allowlist. Other methods return 405 with
`Allow: GET, HEAD`. Missing objects return 404; failed R2 lookups return a generic
503. All errors use `no-store`; HEAD errors have no body. Stored custom metadata,
arbitrary HTTP metadata and SDK exception details are never copied to responses
or logged. There are no upload, listing or deletion endpoints.

## Local setup and checks

Use Node 24+ and pnpm 11.21.0, from this directory:

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
pnpm test:smoke
pnpm dev
```

Direct dependencies and pnpm are pinned; include `pnpm-lock.yaml` in the future
commit. pnpm 11 can store separate environment and application YAML documents
in this lockfile. Keep the complete generated file. The scoped pnpm workspace
does not include `web` or the Python application.

Only reviewed `esbuild@0.28.2` and `workerd@1.20261019.1` installation scripts are
approved in `pnpm-workspace.yaml`. They install/select and validate their native
binaries. `strictDepBuilds` makes unreviewed build scripts fail installation;
review any new versions before extending the approvals. Do not enable all scripts.

On NixOS, the generic workerd binary can report a loader error during its
postinstall validation. Use the optional local shell before Wrangler development
or smoke testing:

```bash
nix-shell shell.nix
pnpm test:smoke
pnpm dev
```

The shell supplies `MINIFLARE_WORKERD_PATH` through Nix's glibc loader and uses
the workerd binary already installed with Wrangler. It does not patch binaries
in pnpm's store or change the machine configuration. It requires x86_64 Linux,
an available `<nixpkgs>` channel, and Node/pnpm on PATH. Other supported operating
systems do not need this shell.

`pnpm build` is **only** `wrangler deploy --dry-run --outdir dist`: it validates
and bundles without deploying. The compatibility date `2026-10-19` matches the
workerd bundled with pinned Wrangler 4.152.0.

`pnpm test` uses mocked R2 with Node's built-in test runner. `pnpm test:smoke`
seeds one tiny PNG into an isolated temporary local R2 database, starts
`wrangler dev --local` on a loopback port, checks GET/HEAD, a missing image,
manifest rejection and POST rejection, then stops the server and removes its
temporary state. No production objects are read or written. `pnpm dev` also
uses only local R2; `remote: false` is explicit on the binding. Its normal local
bucket is empty until seeded with local fixtures.

## Deployment checkpoint

No custom domain or routes are configured. `workers_dev: true` publishes the
Worker at its account's existing workers.dev namespace when deployment is
authorized. Preview URLs are disabled. No queues, cron jobs, databases, paid
addons, new buckets or migrations are configured. Normal Worker invocations
and R2 reads can still consume the account's usage allowance after deployment.

Before deploying, manually confirm:

1. Wrangler OAuth selects the account containing **both** the existing
   `pixshare-media-reader` Worker and `pixshare-media` bucket. Use
   `pnpm exec wrangler whoami` to check the account. If multiple accounts are
   available, select the existing account with `CLOUDFLARE_ACCOUNT_ID` locally;
   do not guess or deploy into a different account. Wrangler can create a
   same-named service in the wrong account.
2. The bucket remains private, its binding is `MEDIA`, and backend writes will
   use the exact prefix above. The R2 binding grants bucket access at runtime;
   the code restricts that capability to `get()` and `head()`.
3. workers.dev access is available and appropriate for these public images.
   Keep automatic Git builds disabled and configure the custom domain separately
   in a later authorized task.
4. Review the dry-run and authorize the production deployment separately.

Verification on 2026-10-26: `pnpm typecheck` passed; `pnpm test` passed all
72 tests with no skips. A fresh `pnpm install --frozen-lockfile` passed with
registry metadata verification, followed by a successful `pnpm build` (2.07 KiB
bundle) and `nix-shell shell.nix --run 'pnpm test:smoke'` (five HTTP scenarios).
The build and smoke checks ran from an identical temporary copy because this
agent workspace has a case-colliding `/mnt/storage/Projects` symlink: esbuild
selects that path while resolving `/mnt/storage/projects`, then fails to read
the entry point. Deploy from a clean checkout without that collision, or fix
the host path mapping first. The same checkout limitation affects `pnpm dev`.
No host symlinks or system configuration were modified. Live account ownership,
bucket privacy settings and production delivery remain manual checks; no
production R2 objects were accessed.

Exact command **after authorization**, from the repository root:

```bash
cd /mnt/storage/projects/PixShare/workers/media-reader
pnpm deploy
```

This runs `wrangler deploy` with `wrangler.jsonc`, updating the existing Worker
in the selected account. On deployment, Wrangler reports the workers.dev origin.
Only existing allowlisted objects return 200; `/` returns 404 by design. Do not
enable public access on the R2 bucket. This task stops before deployment,
production R2 verification, custom-domain configuration, Git commits and pushes.

References: [R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/),
[local R2 simulation](https://developers.cloudflare.com/r2/get-started/workers-api/),
[compatibility dates](https://developers.cloudflare.com/workers/configuration/compatibility-dates/),
and [pnpm build approvals](https://pnpm.io/settings/build#allowbuilds).
