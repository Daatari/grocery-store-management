"""End-to-end browser and failover checks against the actual Compose deployment."""
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8080"


def main():
    values = dict(line.split("=", 1) for line in (ROOT / "deployment/.env").read_text().splitlines() if "=" in line)
    screenshots = ROOT / "screenshots"
    screenshots.mkdir(exist_ok=True)
    compose = ["docker", "compose", "--env-file", str(ROOT / "deployment/.env"), "-f", str(ROOT / "deployment/compose.yaml")]
    nodes = set()
    for _ in range(8):
        with urllib.request.urlopen(BASE + "/health/", timeout=10) as response:
            nodes.add(response.headers["X-Server-Node"])
    assert nodes == {"web-a", "web-b"}, nodes
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def sign_in(username, password):
            page.goto(BASE + "/accounts/login/")
            page.get_by_label("Username", exact=True).fill(username)
            page.get_by_label("Password", exact=True).fill(password)
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_role("button", name="Sign out")).to_be_visible()
        sign_in("customer", values["GROCERY_DEMO_PASSWORD"])
        page.screenshot(path=str(screenshots / "stores-desktop.png"), full_page=True)
        page.goto(BASE + "/stores/east-market/")
        card = page.locator("article").filter(has=page.get_by_role("heading", name="Apples", exact=True))
        card.get_by_label("Quantity", exact=True).fill("2")
        card.get_by_role("button", name="Add to cart").click()
        expect(page.get_by_role("heading", name="Your cart")).to_be_visible()
        page.screenshot(path=str(screenshots / "customer-cart.png"), full_page=True)
        page.get_by_role("button", name="Place demo order").click()
        expect(page.get_by_role("heading", name="Order confirmed.")).to_be_visible(timeout=20000)
        # Session cookies must work regardless of which instance receives the request.
        authenticated_nodes = set()
        for _ in range(8):
            response = page.request.get(BASE + "/orders/")
            assert response.status == 200
            authenticated_nodes.add(response.headers["x-server-node"])
            assert "East Market" in response.text()
        assert authenticated_nodes == {"web-a", "web-b"}
        guest = browser.new_page()
        for scenario, heading in [("decline", "Payment declined."), ("timeout", "Order confirmed.")]:
            guest.goto(BASE + "/stores/east-market/")
            item = guest.locator("article").filter(has=guest.get_by_role("heading", name="Bananas", exact=True))
            item.get_by_role("button", name="Add to cart").click()
            guest.get_by_label("Payment simulation").select_option(scenario)
            guest.get_by_role("button", name="Place demo order").click()
            expect(guest.get_by_role("heading", name=heading)).to_be_visible(timeout=30000)
            # The signed-in customer's session cannot inspect this guest's order.
            assert page.request.get(guest.url).status == 404
        guest.screenshot(path=str(screenshots / "guest-order.png"), full_page=True)
        guest.close()
        page.get_by_role("button", name="Sign out").click()
        sign_in("manager-east", values["GROCERY_DEMO_PASSWORD"])
        page.goto(BASE + "/manage/east-market/")
        expect(page.get_by_role("heading", name="Inventory", exact=True)).to_be_visible()
        page.screenshot(path=str(screenshots / "management.png"), full_page=True)
        page.goto(BASE + "/manage/east-market/import/")
        expect(page.get_by_role("heading", name="Add a product", exact=True)).to_be_visible()
        page.screenshot(path=str(screenshots / "catalog-import.png"), full_page=True)
        assert page.request.get(BASE + "/manage/harbour-market/").status == 403
        page.get_by_role("button", name="Sign out").click()
        sign_in("admin", values["GROCERY_ADMIN_PASSWORD"])
        page.goto(BASE + "/warehouses/")
        page.get_by_label("Stock", exact=True).select_option(label="Central warehouse: Apples")
        page.get_by_label("Quantity", exact=True).fill("10")
        page.get_by_role("button", name="Record movement").click()
        expect(page.get_by_text("Central warehouse · Apples · 10", exact=True)).to_be_visible()
        page.get_by_label("Stock", exact=True).select_option(label="Central warehouse: Apples")
        page.get_by_label("Destination", exact=True).select_option(label="East Market: Apples")
        page.get_by_label("Quantity", exact=True).fill("3")
        page.get_by_role("button", name="Record movement").click()
        expect(page.get_by_text("Central warehouse · Apples · 7", exact=True)).to_be_visible()
        page.screenshot(path=str(screenshots / "warehouse.png"), full_page=True)
        for attempt in range(12):
            page.goto(BASE + "/operations/logs/")
            if page.locator("td", has_text="web-a").count() and page.locator("td", has_text="web-b").count():
                break
            time.sleep(2)
        else:
            raise AssertionError("Central logs did not contain both server instances")
        page.select_option("select[name=level]", "WARN")
        page.get_by_role("button", name="Filter events").click()
        expect(page.get_by_text("http_403", exact=True).first).to_be_visible()
        page.screenshot(path=str(screenshots / "centralized-logs.png"), full_page=True)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=1)
        mobile.goto(BASE)
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
        mobile.screenshot(path=str(screenshots / "stores-mobile.png"), full_page=True)
        browser.close()
        assert not errors, errors
    subprocess.run(compose + ["stop", "web-b"], check=True)
    try:
        for _ in range(4):
            with urllib.request.urlopen(BASE + "/health/", timeout=10) as response:
                assert response.headers["X-Server-Node"] == "web-a"
    finally:
        subprocess.run(compose + ["start", "web-b"], check=True)
    print(json.dumps({"nodes": sorted(nodes), "customer_checkout": "passed", "manager_scope": "passed",
                      "central_logs": "passed", "mobile_layout": "passed", "failover": "passed"}))


if __name__ == "__main__":
    main()
