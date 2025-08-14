import os
import json
import re
import asyncio
from typing import List, Dict

from playwright.async_api import async_playwright


BOROUGHS = ["Queens", "Brooklyn", "Bronx", "Manhattan", "Staten Island"]


async def scrape_profile(username: str, max_posts: int = 20) -> List[Dict]:
    """Return raw post data for a given Instagram username."""
    session_id = os.environ.get("SESSIONID")
    if not session_id:
        raise EnvironmentError("SESSIONID environment variable required")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies([
            {
                "name": "sessionid",
                "value": session_id,
                "domain": ".instagram.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            }
        ])
        page = await context.new_page()
        await page.goto(f"https://www.instagram.com/{username}/")
        # ensure page loaded by waiting for network idle
        await page.wait_for_load_state("networkidle")

        # Fetch profile data via Instagram web API using the page context
        profile_json = await page.evaluate(
            """async (username) => {
                const res = await fetch(`/api/v1/users/web_profile_info/?username=${username}`);
                return await res.json();
            }""",
            username,
        )
        user_id = profile_json.get("data", {}).get("user", {}).get("id")
        if not user_id:
            raise RuntimeError("Unable to retrieve user id")

        feed_json = await page.evaluate(
            """async (uid, count) => {
                const res = await fetch(`/api/v1/feed/user/${uid}/?count=${count}`);
                return await res.json();
            }""",
            user_id,
            max_posts,
        )

        items = feed_json.get("items", [])[:max_posts]

        posts = []
        for item in items:
            shortcode = item.get("code") or item.get("pk")
            reel_url = f"https://www.instagram.com/reel/{shortcode}/" if shortcode else ""
            caption_text = (
                item.get("caption", {}).get("text") if item.get("caption") else ""
            )
            likes = item.get("like_count", 0)
            views = item.get("view_count") or item.get("play_count") or 0
            comments = item.get("comment_count", 0)

            location = ""
            for borough in BOROUGHS:
                if re.search(rf"\b{borough}\b", caption_text, re.IGNORECASE):
                    location = borough
                    break

            apartment_type = ""
            if re.search(r"studio", caption_text, re.IGNORECASE):
                apartment_type = "studio"
            elif re.search(r"1\s*bed(room)?", caption_text, re.IGNORECASE):
                apartment_type = "1 bedroom"

            posts.append(
                {
                    "reel_url": reel_url,
                    "likes": likes,
                    "views": views,
                    "comments": comments,
                    "caption_text": caption_text,
                    "location": location,
                    "apartment_type": apartment_type,
                }
            )

        return posts


def rank_posts(posts: List[Dict]) -> List[Dict]:
    """Rank filtered posts by engagement score."""
    filtered = [p for p in posts if p.get("apartment_type")]

    def score(p: Dict) -> float:
        return p.get("likes", 0) + p.get("comments", 0) + p.get("views", 0) / 100.0

    filtered.sort(key=score, reverse=True)
    top = filtered[:5]
    for idx, post in enumerate(top, 1):
        post["rank"] = idx
    return top


async def main() -> None:
    username = "brooklyn_apartmentrentals"
    posts = await scrape_profile(username)
    ranked = rank_posts(posts)
    print(json.dumps(ranked, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
