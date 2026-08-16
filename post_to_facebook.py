#!/usr/bin/env python3
"""
Publish the queued post for today to the Racquet Point Facebook Page
and Instagram account.

Reads posts/queue.json, finds the entry whose date matches today in the
queue's timezone, and publishes to whichever platforms are configured.

Facebook uploads the image file directly. Instagram does not allow that:
it requires a publicly reachable image URL, which it fetches itself. That
is why IMAGE_BASE_URL must point at the raw files in a public repo.

Environment:
  FB_PAGE_ID       numeric Page ID                      (Facebook)
  FB_PAGE_TOKEN    long-lived Page access token         (both)
  IG_USER_ID       Instagram Business account ID        (Instagram)
  IMAGE_BASE_URL   public base URL for the repo files   (Instagram)
  PLATFORMS        "facebook,instagram" by default
  DRY_RUN          "1" to validate without publishing

Exit codes:
  0  published, or nothing queued for today
  1  configuration or API failure
"""

import json
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests

GRAPH = "https://graph.facebook.com/v26.0"
QUEUE_PATH = "posts/queue.json"
LOG_PATH = "posts/published.json"


def fail(msg):
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"::warning::{msg}")


# --------------------------------------------------------------------------- FB

def publish_facebook(page_id, token, text, image_path=None, image_url=None):
    """
    Publish a photo post. Returns post id.

    Two ways to supply the image:
      image_url   Facebook fetches it itself. Use for anything already on a
                  public CDN, such as Shopify product shots. Nothing to host.
      image_path  a local file in the repo, uploaded directly.
    """
    data = {"caption": text, "access_token": token, "published": "true"}
    if image_url:
        data["url"] = image_url
        r = requests.post(f"{GRAPH}/{page_id}/photos", data=data, timeout=180)
    else:
        with open(image_path, "rb") as fh:
            r = requests.post(f"{GRAPH}/{page_id}/photos", data=data,
                              files={"source": fh}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Facebook {r.status_code}: {r.text[:600]}")
    body = r.json()
    return body.get("post_id") or body.get("id")


# --------------------------------------------------------------------------- IG

def publish_instagram(ig_user_id, token, caption, image_url):
    """Two step: create a media container, wait for it, then publish it."""
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"Instagram container {r.status_code}: {r.text[:600]}\n"
            f"  image_url was: {image_url}\n"
            f"  Instagram must be able to fetch that URL anonymously."
        )
    creation_id = r.json()["id"]

    # Containers are usually ready immediately for photos, but not guaranteed.
    for attempt in range(12):
        s = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=60,
        )
        status = s.json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram container failed: {s.json().get('status')}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram container never reached FINISHED")

    p = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=120,
    )
    if p.status_code != 200:
        raise RuntimeError(f"Instagram publish {p.status_code}: {p.text[:600]}")
    return p.json()["id"]


# ------------------------------------------------------------------------- misc

def load_queue():
    if not os.path.exists(QUEUE_PATH):
        fail(f"{QUEUE_PATH} not found")
    data = json.load(open(QUEUE_PATH))
    if not data.get("posts"):
        fail("queue contains no posts")
    return data


def read_log():
    return json.load(open(LOG_PATH)) if os.path.exists(LOG_PATH) else {}


def write_log(log):
    json.dump(log, open(LOG_PATH, "w"), indent=2, sort_keys=True)


def main():
    dry = os.environ.get("DRY_RUN") == "1"
    platforms = [p.strip().lower() for p in
                 os.environ.get("PLATFORMS", "facebook,instagram").split(",") if p.strip()]

    token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    ig_user_id = os.environ.get("IG_USER_ID")
    base_url = (os.environ.get("IMAGE_BASE_URL") or "").rstrip("/")

    data = load_queue()
    tz = ZoneInfo(data.get("timezone", "America/New_York"))
    today = datetime.now(tz).strftime("%Y-%m-%d")
    print(f"Local date in {tz}: {today}")
    print(f"Platforms requested: {', '.join(platforms)}")

    todays = [p for p in data["posts"] if p["date"] == today]
    if not todays:
        print(f"Nothing queued for {today}. Queue runs "
              f"{data['posts'][0]['date']} to {data['posts'][-1]['date']}.")
        return
    post = todays[0]

    log = read_log()
    done = log.get(today, {})

    results = {}
    failures = []

    # ---- Facebook
    if "facebook" in platforms:
        if done.get("facebook"):
            print(f"Facebook already published for {today}, skipping.")
        elif not dry and (not page_id or not token):
            failures.append("facebook: FB_PAGE_ID or FB_PAGE_TOKEN missing")
        else:
            remote = post.get("image_url")
            img = None if remote else post.get("image")
            if remote:
                print(f"Facebook: {len(post['text'])} chars, remote {remote}")
            elif img and os.path.exists(img):
                print(f"Facebook: {len(post['text'])} chars, {img} "
                      f"({os.path.getsize(img)/1e6:.2f} MB)")
            else:
                failures.append(f"facebook: no usable image ({img or 'none'})")
                img = None
            if remote or img:
                if dry:
                    print("  DRY_RUN, not publishing")
                else:
                    try:
                        results["facebook"] = publish_facebook(
                            page_id, token, post["text"],
                            image_path=img, image_url=remote)
                        print(f"  published {results['facebook']}")
                    except Exception as e:
                        failures.append(f"facebook: {e}")

    # ---- Instagram
    if "instagram" in platforms:
        if done.get("instagram"):
            print(f"Instagram already published for {today}, skipping.")
        elif not dry and (not ig_user_id or not token):
            failures.append("instagram: IG_USER_ID or FB_PAGE_TOKEN missing")
        elif not dry and not base_url and not (
                post.get("ig_image_url") or post.get("image_url")):
            # base_url is only needed when the image lives in this repo
            failures.append("instagram: IMAGE_BASE_URL missing and post has no image_url")
        else:
            caption = post.get("ig_caption", post["text"])
            # A remote URL is used as-is. Otherwise build one from the repo path.
            remote = post.get("ig_image_url") or post.get("image_url")
            img = None
            if remote:
                url = remote
                print(f"Instagram: {len(caption)} chars, remote {url}")
            else:
                img = post.get("ig_image", post.get("image"))
                if not img or not os.path.exists(img):
                    failures.append(f"instagram: image missing {img}")
                    url = None
                else:
                    url = f"{base_url}/{quote(img)}"
                    print(f"Instagram: {len(caption)} chars, {img} -> {url}")
            if url:
                if dry:
                    if url.startswith("http"):
                        try:
                            h = requests.head(url, timeout=30, allow_redirects=True)
                            if h.status_code == 200:
                                print(f"  image URL reachable ({h.headers.get('content-type')})")
                            else:
                                warn(f"  image URL returned {h.status_code}. "
                                     f"Instagram will not be able to fetch it.")
                        except Exception as e:
                            warn(f"  could not reach image URL: {e}")
                    else:
                        warn("  IMAGE_BASE_URL not set, cannot verify image reachability")
                    print("  DRY_RUN, not publishing")
                else:
                    try:
                        results["instagram"] = publish_instagram(
                            ig_user_id, token, caption, url)
                        print(f"  published {results['instagram']}")
                    except Exception as e:
                        failures.append(f"instagram: {e}")

    # ---- record and report
    if results:
        entry = log.get(today, {})
        entry.update(results)
        entry["published_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
        log[today] = entry
        write_log(log)

    if post.get("bio_link") and "instagram" in platforms and not dry:
        print(f"\nReminder: Instagram bio link for today should be\n  {post['bio_link']}")

    if failures:
        for f in failures:
            print(f"::error::{f}", file=sys.stderr)
        # A partial success is still worth keeping. Fail the run so it is visible.
        sys.exit(1)


if __name__ == "__main__":
    main()
