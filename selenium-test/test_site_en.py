"""
Complete end-to-end website test for cyberbitbyte.com
- Crawls homepage + every internal page it can find
- Dynamically tests every in-page anchor link (no hardcoded section list)
- Dynamically tests every clickable button/element (does clicking actually do something?)
- Checks internal links resolve properly (catches soft-404s like "404 Not Found" titles)
- Checks address text is actually linked to a map (not just present as text)
- Checks contact/social links (email, phone, facebook, youtube, linkedin)
- Generates a PDF report with all results

Run with:  python test_site_full.py
"""

import time
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, TimeoutException
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from fpdf import FPDF

# ==================== CONFIG ====================
TESTER_NAME = "Md Daudul Islam"
BASE_URL = "https://www.cyberbitbyte.com/index.html"
DOMAIN = "cyberbitbyte.com"
MAX_PAGES = 25              # safety limit so it doesn't crawl forever
WAIT_SECONDS = 2            # wait after each page load
CLICK_WAIT = 1.5            # wait after clicking a button/element
MAP_DOMAINS = ["google.com/maps", "goo.gl/maps", "maps.app.goo.gl", "openstreetmap.org"]
REQUIRED_CONTACTS = ["Email", "Phone", "Facebook", "YouTube", "LinkedIn"]  # Instagram dropped - not on site
NOT_FOUND_MARKERS = ["404", "not found", "page not found", "error"]
# ==================================================

results = []                 # (test_name, status, detail)
visited_pages = set()
social_links_found = {}      # e.g. {"Facebook": "https://facebook.com/..."}


def log(name, status, detail=""):
    results.append((name, status, detail))
    print(f"[{status}] {name} - {detail}")


def is_soft_404(title):
    t = (title or "").lower()
    return any(marker in t for marker in NOT_FOUND_MARKERS)


def normalize_url(url):
    """
    Treat these as the SAME page, so nothing gets crawled/tested twice under
    two different-looking URLs pointing at the same content:
      - https://site.com/index.html  vs  https://site.com
      - https://www.site.com/page    vs  https://site.com/page  (www vs non-www)
      - trailing slash vs no trailing slash
    """
    u = url.split("?")[0].split("#")[0].rstrip("/")
    if u.lower().endswith("/index.html"):
        u = u[: -len("/index.html")]
    u = u.replace("://www.", "://")
    return u


def short_page_label(url):
    """
    Turn a full URL into a short, unambiguous label for the report:
    the path only (e.g. '/blogs/website-speed'), or 'Homepage' for the root.
    Keeps report rows readable instead of getting cut off by long domain names.
    """
    try:
        path = urlparse(url).path.rstrip("/")
    except Exception:
        path = url
    return path if path else "Homepage"


def collect_links(driver):
    """Find every <a> on the current page. Sort into internal pages vs social/contact links."""
    internal_pages = set()
    anchors = driver.find_elements(By.TAG_NAME, "a")
    for a in anchors:
        try:
            href = a.get_attribute("href")
            if not href:
                continue
            href_lower = href.lower()

            if "facebook.com" in href_lower:
                social_links_found["Facebook"] = href
            elif "youtube.com" in href_lower or "youtu.be" in href_lower:
                social_links_found["YouTube"] = href
            elif "linkedin.com" in href_lower:
                social_links_found["LinkedIn"] = href
            elif "wa.me" in href_lower or "whatsapp.com" in href_lower:
                social_links_found["WhatsApp"] = href
            elif href_lower.startswith("mailto:"):
                social_links_found["Email"] = href
            elif href_lower.startswith("tel:"):
                social_links_found["Phone"] = href
            elif DOMAIN in href_lower and "#" not in href:
                internal_pages.add(normalize_url(href))
        except Exception:
            continue
    return internal_pages


def nearest_anchor(driver, el):
    """Walk up from an element to find the nearest wrapping <a> tag, if any."""
    try:
        return el.find_element(By.XPATH, "./ancestor-or-self::a[1]")
    except NoSuchElementException:
        return None


def classify_contact_text(text):
    """
    Guess what KIND of contact item a piece of text is (email/phone/whatsapp/
    website/address), based on its own content - same categories seen in a
    typical office contact card (Dhaka Office / Khulna Office style).
    Returns None if it doesn't look like any of these.
    """
    t = text.strip()
    tl = t.lower()

    if "@" in t and " " not in t and "." in t.split("@")[-1]:
        return "Email"
    if tl.startswith("whatsapp") or "chat on whatsapp" in tl:
        return "WhatsApp"
    digits_only = t.replace(" ", "").replace("-", "").replace("+", "")
    if (t.startswith("+") or tl.startswith("880")) and digits_only.isdigit() and len(digits_only) >= 8:
        return "Phone"
    if tl.startswith("www.") or tl.startswith("http://") or tl.startswith("https://"):
        return "Website"
    if "," in t and any(k in tl for k in
                         ["road", "street", "avenue", "office", "dhaka", "khulna",
                          "mirpur", "bangladesh", "sher-e-bangla", "shewrapara"]):
        return "Address"
    return None


def test_contact_info_clickability(driver, page_label):
    """
    Find every email / phone / whatsapp / website / address item shown on the
    page and check that clicking it actually goes somewhere correct:
      - Email text  -> must be wrapped in a mailto: link
      - Phone text  -> must be wrapped in a tel: link
      - WhatsApp    -> must link to wa.me / whatsapp.com
      - Website     -> must have a real href
      - Address     -> must be wrapped in a link to an actual map (Google Maps /
                        OpenStreetMap etc). Plain text with a pin icon next to it
                        does NOT count - this is exactly the "everything else
                        works but address doesn't open a map" case.
    """
    candidates = driver.find_elements(
        By.XPATH, "//*[not(self::script) and not(self::style)][text()[normalize-space()]]"
    )

    seen = set()
    for el in candidates:
        try:
            text = el.text.strip() if el.text else ""
        except StaleElementReferenceException:
            continue
        if not text or len(text) > 120:
            continue

        category = classify_contact_text(text)
        if not category:
            continue

        key = (category, text[:60])
        if key in seen:
            continue
        seen.add(key)

        anchor = nearest_anchor(driver, el)
        href = (anchor.get_attribute("href") if anchor else None) or ""
        href_l = href.lower()

        if category == "Email":
            ok = href_l.startswith("mailto:")
            detail = href if ok else "Not clickable - no mailto: link (icon/text present but does nothing)"
        elif category == "Phone":
            ok = href_l.startswith("tel:")
            detail = href if ok else "Not clickable - no tel: link (icon/text present but does nothing)"
        elif category == "WhatsApp":
            ok = "wa.me" in href_l or "whatsapp.com" in href_l
            detail = href if ok else "Not clickable - no WhatsApp link (icon/text present but does nothing)"
        elif category == "Website":
            ok = bool(href)
            detail = href if ok else "Not clickable - no link (icon/text present but does nothing)"
        elif category == "Address":
            ok = any(md in href_l for md in MAP_DOMAINS)
            if ok:
                detail = href
            else:
                # static href didn't point to a map - some sites open the map via
                # JS (onclick) instead of a real href. Actually click and see.
                ok, detail = live_click_check_for_map(driver, anchor or el)
        else:
            continue

        log(f"{category} Clickable - {page_label} - '{text[:40]}'",
            "PASSED" if ok else "FAILED", detail)


def live_click_check_for_map(driver, el):
    """
    Some sites don't put a real href on the address - they open the map via
    JS onclick instead. Static href checking can't catch that, so actually
    click the element and see if a map opens (new tab or URL change).
    Restores original state afterwards. Returns (ok, detail).
    """
    original_url = driver.current_url
    original_handles = set(driver.window_handles)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
        time.sleep(CLICK_WAIT)

        new_handles = set(driver.window_handles)
        opened = list(new_handles - original_handles)

        if opened:
            driver.switch_to.window(opened[0])
            new_url = driver.current_url
            driver.close()
            driver.switch_to.window(list(original_handles)[0])
            if any(md in new_url.lower() for md in MAP_DOMAINS):
                return True, f"Opens map on click: {new_url}"
            return False, f"Click opened a new tab but not a map: {new_url}"

        current_url = driver.current_url
        if current_url != original_url:
            ok = any(md in current_url.lower() for md in MAP_DOMAINS)
            driver.get(original_url)
            time.sleep(WAIT_SECONDS)
            return ok, (current_url if ok else f"Click navigated but not to a map: {current_url}")

        return False, "Not clickable - no link, no onclick effect (icon/text present but does nothing)"
    except Exception as e:
        try:
            driver.get(original_url)
            time.sleep(WAIT_SECONDS)
        except Exception:
            pass
        return False, f"Not clickable - {str(e)[:50]}"


def element_label(el, idx):
    """Build a clear, distinguishable label: index + tag + id/class + visible text."""
    try:
        tag = el.tag_name
        el_id = el.get_attribute("id") or ""
        el_class = (el.get_attribute("class") or "").split()
        text = (el.text or el.get_attribute("aria-label") or "").strip()
        bits = [f"#{idx}", tag]
        if el_id:
            bits.append(f"#{el_id}")
        elif el_class:
            bits.append(f".{el_class[0]}")
        label = " ".join(bits)
        if text:
            label += f" '{text[:20]}'"
        return label[:45]
    except Exception:
        return f"#{idx} element"


def ui_state_snapshot(driver, el):
    """Snapshot body class + element's own class/aria-expanded, to detect
    menu/accordion-style toggles that don't change URL or open a modal."""
    try:
        body_class = driver.execute_script("return document.body.className;")
    except Exception:
        body_class = None
    try:
        el_class = el.get_attribute("class")
        el_aria = el.get_attribute("aria-expanded")
    except Exception:
        el_class, el_aria = None, None
    return (body_class, el_class, el_aria)


def get_clickable_elements(driver):
    """
    Dynamically find things that LOOK clickable but aren't plain navigational
    <a href="..."> links: buttons, a[href='#'], a[href^='javascript:'], and
    elements with an onclick attribute. These are exactly the elements that can
    silently do nothing when clicked.
    """
    elements = []
    elements.extend(driver.find_elements(By.TAG_NAME, "button"))
    elements.extend(driver.find_elements(
        By.CSS_SELECTOR, "a[href='#'], a[href^='javascript:'], [onclick]"
    ))
    # de-dupe while preserving order
    seen = set()
    unique = []
    for el in elements:
        key = id(el)
        if key not in seen:
            seen.add(key)
            unique.append(el)
    return unique


def modal_or_popup_visible(driver):
    """Heuristic check for a modal/dialog/popup having appeared."""
    selectors = "[role='dialog'], .modal, .popup, .lightbox, .dialog"
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, selectors):
            if el.is_displayed():
                return True
    except Exception:
        pass
    return False


def test_clickable_elements(driver, page_label):
    """Click every button-like element on the current page and verify SOMETHING happens."""
    original_url = driver.current_url
    original_handles = set(driver.window_handles)
    elements = get_clickable_elements(driver)

    for idx, el in enumerate(elements, start=1):
        label = element_label(el, idx)
        try:
            before_state = ui_state_snapshot(driver, el)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(CLICK_WAIT)

            new_handles = set(driver.window_handles)
            new_url = driver.current_url

            if len(new_handles) > len(original_handles):
                # opened a new tab/window - close it and return to original
                extra = list(new_handles - original_handles)
                for h in extra:
                    driver.switch_to.window(h)
                    driver.close()
                driver.switch_to.window(list(original_handles)[0])
                log(f"Clickable - {page_label} - {label}", "PASSED", "Opened new tab/window")

            elif new_url != original_url:
                log(f"Clickable - {page_label} - {label}", "PASSED", f"Navigated to {new_url}")
                driver.get(original_url)
                time.sleep(WAIT_SECONDS)

            elif modal_or_popup_visible(driver):
                log(f"Clickable - {page_label} - {label}", "PASSED", "Opened modal/popup")

            else:
                after_state = ui_state_snapshot(driver, el)
                if after_state != before_state:
                    log(f"Clickable - {page_label} - {label}", "PASSED",
                        "Toggled UI state (menu/accordion class or aria-expanded changed)")
                else:
                    log(f"Clickable - {page_label} - {label}", "FAILED", "Click had no visible effect")

        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            log(f"Clickable - {page_label} - {label}", "SKIPPED", str(e)[:50])
        except Exception as e:
            log(f"Clickable - {page_label} - {label}", "FAILED", str(e)[:50])


# ==================== SETUP ====================
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.maximize_window()

# ==================== STEP 1: Homepage load ====================
driver.get(BASE_URL)
time.sleep(WAIT_SECONDS)

page_title = driver.title
log("Homepage - Load & Title", "PASSED" if page_title and not is_soft_404(page_title) else "FAILED",
    f"Title: {page_title}")

# ==================== STEP 2: Dynamic in-page anchor navigation ====================
# Instead of a hardcoded section list, discover every a[href^='#'] actually on the page.
anchor_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='#']")
anchor_hrefs = []
for a in anchor_links:
    href = a.get_attribute("href") or ""
    if "#" in href:
        section_id = href.split("#")[-1]
        if section_id:
            anchor_hrefs.append(section_id)
anchor_hrefs = list(dict.fromkeys(anchor_hrefs))  # de-dupe, preserve order

for section_id in anchor_hrefs:
    try:
        nav_link = driver.find_element(By.CSS_SELECTOR, f"a[href='#{section_id}']")
        driver.execute_script("arguments[0].click();", nav_link)
        time.sleep(1)
        target = driver.find_element(By.ID, section_id)
        if target.is_displayed():
            log(f"Homepage Section - {section_id}", "PASSED", "Section visible")
        else:
            log(f"Homepage Section - {section_id}", "FAILED", "Section not visible")
    except NoSuchElementException:
        log(f"Homepage Section - {section_id}", "FAILED", "Anchor links to id that does not exist")
    except Exception as e:
        log(f"Homepage Section - {section_id}", "FAILED", str(e)[:50])

# ==================== STEP 3: Test clickable buttons/elements on homepage ====================
driver.get(BASE_URL)
time.sleep(WAIT_SECONDS)
test_clickable_elements(driver, "Homepage")
test_contact_info_clickability(driver, "Homepage")

# ==================== STEP 4: Discover & crawl every internal page ====================
driver.get(BASE_URL)
time.sleep(WAIT_SECONDS)
visited_pages.add(normalize_url(BASE_URL))

queue = list(collect_links(driver))

while queue and len(visited_pages) < MAX_PAGES:
    link = queue.pop(0)
    if link in visited_pages:
        continue
    visited_pages.add(link)

    try:
        driver.get(link)
        time.sleep(WAIT_SECONDS)
        t = driver.title
        page_name = short_page_label(link)

        if t and not is_soft_404(t):
            log(f"Page Load - {page_name}", "PASSED", f"Title: {t} | URL: {link}")
        elif t:
            log(f"Page Load - {page_name}", "FAILED", f"Soft 404 - Title: {t} | URL: {link}")
        else:
            log(f"Page Load - {page_name}", "FAILED", f"No title / blank page | URL: {link}")

        # look for more links / socials on this page too
        new_links = collect_links(driver)
        for nl in new_links:
            if nl not in visited_pages and nl not in queue:
                queue.append(nl)

        # test clickable buttons/elements on this page too
        test_clickable_elements(driver, page_name)

        # email / phone / whatsapp / website / address - each checked individually
        test_contact_info_clickability(driver, page_name)

    except Exception as e:
        log(f"Page Load - {short_page_label(link)}", "FAILED", f"{str(e)[:50]} | URL: {link}")

# ==================== STEP 5: Verify required contact / social links found anywhere on the site ====================
for c in REQUIRED_CONTACTS:
    if c in social_links_found:
        log(f"Contact/Social Link - {c}", "PASSED", social_links_found[c])
    else:
        log(f"Contact/Social Link - {c}", "FAILED", "Not found anywhere on site")

driver.quit()

# ==================== STEP 6: Build the PDF report ====================
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "Website Full Test Report", new_x="LMARGIN", new_y="NEXT", align="C")

pdf.set_font("Helvetica", "", 12)
pdf.cell(0, 8, f"Tested by: {TESTER_NAME}", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, f"Website: {BASE_URL}", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, f"Pages Crawled: {len(visited_pages)}", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# Table header
def table_header():
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(75, 8, "Test Name", border=1, fill=True)
    pdf.cell(25, 8, "Result", border=1, fill=True)
    pdf.cell(90, 8, "Details", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

table_header()
pdf.set_font("Helvetica", "", 9)

passed_count = 0
failed_count = 0
skipped_count = 0

for name, status, detail in results:
    if status == "PASSED":
        passed_count += 1
        pdf.set_text_color(0, 120, 0)
    elif status == "FAILED":
        failed_count += 1
        pdf.set_text_color(200, 0, 0)
    else:
        skipped_count += 1
        pdf.set_text_color(150, 100, 0)

    # re-print header if we're about to hit a page break
    if pdf.get_y() > 270:
        pdf.add_page()
        table_header()
        pdf.set_font("Helvetica", "", 9)

    pdf.cell(75, 7, name[:45], border=1)
    pdf.cell(25, 7, status, border=1)
    pdf.cell(90, 7, str(detail)[:55], border=1, new_x="LMARGIN", new_y="NEXT")

pdf.set_text_color(0, 0, 0)
pdf.ln(5)
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, f"Summary: {passed_count} Passed | {failed_count} Failed | {skipped_count} Skipped "
               f"(Total: {len(results)})", new_x="LMARGIN", new_y="NEXT")

pdf.output("test_report_full.pdf")
print("\nPDF report generated: test_report_full.pdf")
print(f"Total pages crawled: {len(visited_pages)}")
print(f"Passed: {passed_count} | Failed: {failed_count} | Skipped: {skipped_count}")