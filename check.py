import sys
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://www.citaconsular.es/es/hosteds/widgetdefault/25b3b7e5d8d13fe8b416ceb916c83ed6a"
NTFY_URL = "https://ntfy.sh/consulate-miami-alerts"

NO_SLOT_PHRASES = [
    "no hay citas disponibles",
    "agenda completa",
    "sin citas",
]


def check_appointments():
    print(f"Loading {URL} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(URL, timeout=60_000)
            # Wait for the booking widget to hydrate
            page.wait_for_load_state("networkidle", timeout=60_000)
        except PlaywrightTimeoutError:
            print("WARNING: page load timed out, continuing with partial render")

        # Give JS-driven content a moment to settle
        page.wait_for_timeout(3_000)

        content = page.content().lower()

        # Check for explicit "no slots" messages
        for phrase in NO_SLOT_PHRASES:
            if phrase in content:
                print(f'No slots available — found phrase: "{phrase}"')
                browser.close()
                return False

        # Look for enabled (clickable) calendar day cells
        enabled_days = page.query_selector_all(
            "td.day:not(.disabled):not(.old):not(.new), "
            "[class*='day']:not([class*='disabled']):not([class*='unavailable'])"
        )
        print(f"Enabled calendar cells found: {len(enabled_days)}")

        browser.close()

        if enabled_days:
            print("Slots appear to be available!")
            return True

        print("No enabled calendar slots detected.")
        return False


def send_notification():
    print("Sending push notification to ntfy.sh ...")
    response = requests.post(
        NTFY_URL,
        headers={
            "Title": "Consulate appointment available!",
            "Priority": "urgent",
            "Tags": "passport,es,rotating_light",
        },
        data="Appointment slots are open at the Spanish Consulate in Miami for Primer Pasaporte. Book now!",
        timeout=15,
    )
    if response.ok:
        print(f"Notification sent (status {response.status_code})")
    else:
        print(f"Notification failed (status {response.status_code}): {response.text}")


def main():
    available = check_appointments()
    if available:
        send_notification()
        sys.exit(0)
    else:
        print("No action needed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
