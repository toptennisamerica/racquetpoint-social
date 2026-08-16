# Racquet Point daily social poster

Publishes one queued post per day to the Racquet Point **Facebook Page** and
**Instagram** account, images and all, from GitHub's servers. Nothing runs on your
machine and nothing needs you to be awake.

## Why this exists rather than Business Suite

Business Suite schedules posts perfectly well by hand. It cannot be driven
automatically, because attaching an image needs a native file picker dialog that no
automation can reach. GitHub Actions talks to the Meta Graph API directly and has no
such problem.

## Why the repository is public

Instagram will not accept an uploaded file. It requires a **publicly reachable URL**
that it fetches itself. The images therefore have to be served from somewhere public,
and `raw.githubusercontent.com` on a public repo is the simplest option that costs
nothing and never expires.

**Your credentials are not exposed by this.** GitHub Actions secrets are encrypted
and are never readable from a public repo, not in the code, not in logs, not by forks.
What *is* public is the post text and images, meaning someone who found the repo could
read next week's captions early. For a tennis shop's content calendar that is a
non-issue, but it is the tradeoff and you should know it.

If that ever stops being acceptable, host the images elsewhere public and point
`IMAGE_BASE_URL` at that instead. Nothing else changes.

---

## Setup, once

You need a GitHub account. About fifteen minutes.

### 1. Create the repository

Make a new **public** repository and upload the contents of this folder:

```
.github/workflows/daily-post.yml
posts/queue.json
images/               16 files, Facebook sizing
images/ig/            16 files, Instagram 4:5 sizing
post_to_facebook.py
README.md
```

### 2. Confirm the Instagram permissions on the Meta app

The app `Racquet Point Page Posting` (ID `1711147073515686`) already has
`pages_show_list`, `pages_read_engagement` and `pages_manage_posts`. Instagram needs
two more:

- `instagram_basic`
- `instagram_content_publish`

Add them under **Use cases** then **Customize** on the app dashboard, then regenerate
the token in step 3 so it carries the new scopes. A token issued before you add these
will fail on Instagram with a permissions error while Facebook keeps working, which is
a confusing way to find out.

Your Instagram account also has to be a **Business or Creator** account linked to the
Page. It already appears in Business Suite alongside the Page, so this is almost
certainly already true.

### 3. Get the Page ID and a permanent Page token

1. Open the [Graph API Explorer](https://developers.facebook.com/tools/explorer/1711147073515686/).
   Check **Meta App** reads `Racquet Point Page Posting`.
2. Add all five permissions listed above.
3. Click **Generate Access Token** and approve, selecting the Racquet Point Page
   when it asks which Pages to allow.
4. Click the small **i** to the left of the token, then **Open in Access Token Tool**.
5. Click **Extend Access Token**. Copy the long token it returns.
6. Back in the Explorer, paste that token into the Access Token field.
7. Set the path to `me/accounts?fields=id,name,access_token` and hit **Submit**.
8. Find the `Racquet Point` entry. Its `id` is **FB_PAGE_ID**, its `access_token` is
   **FB_PAGE_TOKEN**.

Step 5 is the one people skip. A Page token derived from a short-lived user token dies
in about an hour. Extend first, then pull the Page token, and it does not expire.

### 4. Get the Instagram account ID

Still in the Explorer, with the Page token in the field, request:

```
me?fields=instagram_business_account
```

The `id` it returns is **IG_USER_ID**. If the field comes back empty, the Instagram
account is not linked to the Page, or it is still a personal account rather than
Business or Creator.

### 5. Add three secrets

**Settings** then **Secrets and variables** then **Actions** then
**New repository secret**.

| Name | Value |
|---|---|
| `FB_PAGE_ID` | the `id` from step 8 |
| `FB_PAGE_TOKEN` | the `access_token` from step 8 |
| `IG_USER_ID` | the id from step 4 |

Paste them yourself. They should not travel through chat, email, or a text file.

### 6. Test before trusting it

**Actions** then **Daily social post** then **Run workflow**, leaving
**Validate without publishing** ticked. It checks that it can find today's post, read
both images, and that Instagram can actually reach the image URL over HTTP. That last
check is the one worth watching, because a URL Instagram cannot fetch is the most
common failure and the dry run catches it before it matters.

Then run again unticked to publish for real. You can also restrict a run to one
platform from the dropdown, which is handy when only one side is misbehaving.

---

## Images from a URL instead of the repo

A queue entry can point at an image already hosted somewhere public rather than
committing a file:

```json
{
  "date": "2026-08-24",
  "image_url": "https://cdn.shopify.com/s/files/.../product.png",
  "bio_link": "https://www.racquetpoint.com/products/...",
  "text": "...",
  "ig_caption": "..."
}
```

Both platforms fetch it themselves, Facebook via the `url` parameter and Instagram via
its normal container flow. Nothing gets hosted and nothing gets committed.

This is the easy way to post anything already in your Shopify catalog. Grab the product
image URL from the product page or the admin, drop it in as `image_url`, done. Week two
uses this for the Pro Staff Classic, Blade and Pro Staff 87 posts.

Add `ig_image_url` as well if Instagram should use a differently cropped version.

**Resolution matters more than you would think.** Instagram displays at 1080px wide and
upscales anything smaller, which looks soft on a phone. Brand images pulled from
manufacturer websites are often 500 to 650px and will look noticeably worse than your
own Shopify product shots, which run 1292px. Prefer the Shopify URL where one exists.

---

## Instagram bio link

Instagram captions cannot contain clickable links, so each post says "link in bio" and
carries a `bio_link` telling you where the bio should point that day. Three weeks queued,
Aug 16 to Sep 5:

| Date | Brand | Bio link |
|---|---|---|
| 08-16 | service | /products/racquet-restringing-service-and-repair |
| 08-17 | tecnifibre | /products/tecnifibre-fire-300-tennis-racquet |
| 08-18 | selkirk | /products/selkirk-courtstrike-pro-3-0-mens-pickleball-shoes |
| 08-19 | wilson | /products/wilson-blade-98-16x19-v10-tennis-racquet |
| 08-20 | holbrook | /products/holbrook-fuze-pickleball-paddle |
| 08-21 | tecnifibre | /collections/tecnifibre-tennis-racquets |
| 08-22 | community |  |
| 08-23 | service | /products/racquet-restringing-service-and-repair |
| 08-24 | diadem | /products/diadem-court-flo-men-s-tennis-shoes |
| 08-25 | wilson | /products/wilson-pro-staff-97-classic-tennis-racquet |
| 08-26 | holbrook | /products/holbrook-pro-aero-t-elongated-pickleball-paddle-14mm-16mm |
| 08-27 | service | /products/racquet-restringing-service-and-repair |
| 08-28 | wilson | /products/wilson-blade-100ul-v10-tennis-racquet |
| 08-29 | tecnifibre | /products/tecnifibre-fire-300-tennis-racquet |
| 08-30 | community |  |
| 08-31 | wilson | /products/wilson-ultra-100-v5-tennis-racquet |
| 09-01 | selkirk | /products/selkirk-legacy-pro-mens-pickleball-shoes |
| 09-02 | tecnifibre | /products/tecnifibre-tour-endurance-6r-white-bag |
| 09-03 | service | /products/racquet-restringing-service-and-repair |
| 09-04 | diadem | /products/diadem-court-burst-men-s-shoes-white |
| 09-05 | wilson | /products/wilson-ultra-team-v5-tennis-racquet |

The workflow log prints the correct link on every run, so you can check the Actions tab
rather than this table. Two consecutive days point at stringing, so in practice this is
about fifteen bio changes across the three weeks.

If the daily swap gets tiresome, a link-in-bio landing page with all of them listed
removes the chore permanently.

---

## Brand rotation and stock discipline

Two rules the calendar follows, both learned the hard way.

**No two consecutive posts share a brand.** Tennis and pickleball alternate too. The
calendar is checked for adjacent repeats when it is built; the current one has zero.

**Every product is verified before it is written about.** Not just `totalInventory`,
which lies. The Wilson Pro Staff 87 shoe reported `totalInventory: 32` while variant
level showed a single pair in one size. Always check `variants { inventoryQuantity }`
and confirm `status: ACTIVE` with a non-null `publishedAt` before a product goes in the
queue.

## Per-post platform restriction

A post can limit itself to one platform:

```json
{ "platforms": ["facebook"] }
```

Used for the Selkirk posts, because every Selkirk image on the Shopify CDN is 1500x2000,
a 3:4 ratio. Instagram's minimum is 4:5 and rejects anything taller. Once 4:5 or square
Selkirk images exist, drop the `platforms` key and they publish to both.

---

## How it runs

Schedule is `30 21 * * *`, which is **17:30 Eastern** during daylight saving. GitHub
cron is always UTC and ignores DST, so in November this drifts to 16:30 local. Change
the cron to `30 22 * * *` then.

Each run:

1. Works out today's date in `America/New_York`
2. Finds the matching entry in `posts/queue.json`
3. Exits quietly if nothing is queued, which is not an error
4. Publishes to Facebook by uploading the file from `images/`
5. Publishes to Instagram by giving it the public URL of the file in `images/ig/`
6. Logs each platform separately in `posts/published.json`

The per-platform log matters. If Instagram fails and Facebook succeeds, a re-run
publishes only the Instagram half. It cannot double post to Facebook.

GitHub's scheduler runs late under load, occasionally by fifteen minutes. Irrelevant
for brand posting, but worth knowing before you wonder why 17:30 became 17:41.

## Adding next week

Append to the `posts` array in `posts/queue.json`:

```json
{
  "date": "2026-08-23",
  "image": "images/whatever.jpg",
  "ig_image": "images/ig/whatever.jpg",
  "bio_link": "https://www.racquetpoint.com/products/something",
  "text": "Facebook copy. Links here are clickable.",
  "ig_caption": "Instagram copy. No clickable links, so say link in bio.\n\n#tennis"
}
```

Only `date`, `image` and `text` are required. Without `ig_image` it falls back to the
Facebook image, and without `ig_caption` it reuses the Facebook text, links and all,
which reads badly on Instagram. Write both.

**Image sizing.** Facebook is relaxed. Instagram requires an aspect ratio between
**4:5 and 1.91:1** and rejects anything taller. Four of the seven originals here were
3:4 or 2:3, too tall, so `images/ig/` holds 1080x1350 versions built by fitting the
original onto a 4:5 canvas over a blurred copy of itself. Nothing is cropped and the
padding is invisible on dark backgrounds. Reuse that approach for new tall images.

## When it breaks

Failures land in the Actions tab.

- **`(#190) Error validating access token`** revoked, or you skipped the extend step
  in section 3. Redo it.
- **`(#200) Permissions error`** on Instagram only: the token predates
  `instagram_content_publish`. Add the permission, regenerate, update the secret.
- **`Instagram container` error mentioning the image URL** the repo went private, or
  the file is not where the queue says. Open the URL from the log in a private browser
  window. If you cannot see it, neither can Instagram.
- **`The user is not an Instagram Business`** the account is still personal. Convert it
  in the Instagram app under Settings, Account type.
- **Nothing posted, no failure** the queue ran dry. Add more entries.

Instagram also enforces a rate limit of 50 published posts per 24 hours. One a day is
nowhere near it.
