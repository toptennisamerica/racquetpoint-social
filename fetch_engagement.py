#!/usr/bin/env python3
"""
Collect engagement for every post that has already been published and write it
to posts/engagement.json, which the calendar page reads.

Why this is a separate script rather than something the web page does itself:
the calendar is a static page on a public repo, so it has nowhere to keep a
token. Anything it could read, so could a stranger. This runs inside GitHub
Actions instead, where FB_PAGE_TOKEN is an encrypted secret, and publishes only
the resulting numbers.

Metrics are deliberately limited to what the current token can already see:

  Facebook   reactions, comments, shares      pages_read_engagement
  Instagram  likes, comments                  instagram_basic

Reach and impressions are NOT collected. They need read_insights and
instagram_manage_insights, which would mean adding permissions and reissuing
the token. Reactions plus comments plus shares is also exactly how the
competitor benchmark was measured, so the numbers stay comparable.

Environment:
  FB_PAGE_TOKEN   long-lived Page access token
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

GRAPH = "https://graph.facebook.com/v26.0"
LOG_PATH = "posts/published.json"
OUT_PATH = "posts/engagement.json"


def warn(msg):
    print(f"::warning::{msg}")


def facebook_stats(post_id, token):
    r = requests.get(
        f"{GRAPH}/{post_id}",
        params={
            "fields": "reactions.summary(total_count).limit(0),"
                      "comments.summary(total_count).limit(0),shares",
            "access_token": token,
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    b = r.json()
    reactions = b.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments = b.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares = (b.get("shares") or {}).get("count", 0)
    return {"reactions": reactions, "comments": comments, "shares": shares,
            "total": reactions + comments + shares}


def instagram_stats(media_id, token):
    r = requests.get(
        f"{GRAPH}/{media_id}",
        params={"fields": "like_count,comments_count,permalink",
                "access_token": token},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    b = r.json()
    likes = b.get("like_count", 0)
    comments = b.get("comments_count", 0)
    out = {"likes": likes, "comments": comments, "total": likes + comments}
    if b.get("permalink"):
        out["permalink"] = b["permalink"]
    return out


def main():
    token = os.environ.get("FB_PAGE_TOKEN")
    if not token:
        print("::error::FB_PAGE_TOKEN missing", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(LOG_PATH):
        print(f"{LOG_PATH} not found, nothing has published yet.")
        return

    log = json.load(open(LOG_PATH))
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    failures = 0

    for date in sorted(log):
        entry = log[date]
        day = {}
        if entry.get("facebook"):
            try:
                day["facebook"] = facebook_stats(entry["facebook"], token)
            except Exception as e:
                warn(f"{date} facebook: {e}")
                failures += 1
        if entry.get("instagram"):
            try:
                day["instagram"] = instagram_stats(entry["instagram"], token)
            except Exception as e:
                warn(f"{date} instagram: {e}")
                failures += 1
        if day:
            day["total"] = sum(v["total"] for v in day.values() if isinstance(v, dict))
            out[date] = day
            bits = ", ".join(f"{k} {v['total']}" for k, v in day.items()
                             if isinstance(v, dict))
            print(f"{date}: {bits}")

    json.dump(out, open(OUT_PATH, "w"), indent=2, sort_keys=True)
    days = [k for k in out if k != "updated"]
    grand = sum(out[d]["total"] for d in days)
    print(f"\n{len(days)} published days, {grand} total engagements "
          f"({grand/len(days):.1f} per day)" if days else "\nNothing published yet.")

    # A token problem is worth failing on. One dud post id is not.
    if failures and not days:
        sys.exit(1)


if __name__ == "__main__":
    main()
