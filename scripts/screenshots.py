"""Capture README screenshots of the running app (light + dark).

    streamlit run app.py --server.port 8794 --server.headless true   # terminal 1
    python scripts/screenshots.py http://localhost:8794               # terminal 2

Uses Playwright with the locally installed Chrome (no browser download).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8794"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screens"
TABS = {"plan": "Your plan", "market": "The market", "roles": "Which role fits", "postings": "Postings", "about": "About the data"}


def settle(page, ms=2500):
    page.wait_for_timeout(ms)
    for _ in range(60):
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        page.wait_for_timeout(250)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for scheme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme=scheme)
            page = ctx.new_page()
            page.goto(URL)
            page.locator(".hero").first.wait_for(timeout=90000)
            settle(page, 4000)
            for slug, label in TABS.items():
                page.get_by_role("tab", name=re.compile(re.escape(label))).click()
                settle(page)
                # the plan shot keeps the hero; the others start at the tab bar so their own content is visible
                page.evaluate("""slug => { const tabs = document.querySelector('[data-testid="stTabs"]');
                    const main = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
                    const y = slug === 'plan' ? 0 : tabs.getBoundingClientRect().top + main.scrollTop - 12;
                    main.scrollTo(0, y); window.scrollTo(0, y); }""", slug)
                page.wait_for_timeout(600)
                page.screenshot(path=OUT / f"{slug}-{scheme}.jpg", type="jpeg", quality=85)
                print("saved", f"{slug}-{scheme}.jpg")
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
