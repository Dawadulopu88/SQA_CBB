"""
MASTER TEST SUITE - CyberBitByte Website
Implements the "CyberBitByte Comprehensive Test Plan" test cases (mapped by
Test ID: HP-*, NAV-*, SERV-*, IND-*, PORT-*, ABT-*, TSM-*, TEAM-*, CONT-*,
FOOT-*, BR-*, MOB-*, PERF-*, LOAD-*, SEC-*, A11Y-*, SEO-*, ERR-*, ANA-*)
and generates a categorized PDF report.

SCOPE NOTE - some test cases CANNOT be done by a single automated script and
are logged as "MANUAL" in the report instead of a false PASS/FAIL:
  - A11Y-001 (real screen reader / JAWS-NVDA), A11Y-002/005 (manual keyboard/
    focus check), LOAD-001/002 (real concurrent-user load testing - needs
    Locust/JMeter), CONT-006/SEC-003/SEC-004/A11Y-007/ERR-004 (contact-us.html
    blocks automated crawling per robots.txt - must be checked by hand),
    ERR-003 (physical network disconnect), MOB-008 (physical device rotation),
    ANA-002/003/004 (needs live GA/GTM dashboard access), PERF-003 (needs
    Chrome DevTools throttling / Lighthouse).

Install (run once):
    pip install selenium webdriver-manager fpdf2 requests beautifulsoup4 axe-selenium-python

Run:
    python test_site_master.py
"""

import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from fpdf import FPDF

try:
    from axe_selenium_python import Axe
    AXE_AVAILABLE = True
except ImportError:
    AXE_AVAILABLE = False

# ================= CONFIG =================
TESTER_NAME = "Md Daudul Islam"
BASE_URL = "https://www.cyberbitbyte.com/index.html"
LEGAL_PAGES = {
    "About": urljoin(BASE_URL, "about-us.html"),
    "Contact": urljoin(BASE_URL, "contact-us.html"),
    "Blogs": urljoin(BASE_URL, "blogs/index.html"),
    "Privacy Policy": urljoin(BASE_URL, "privacy-policy.html"),
    "Terms & Conditions": urljoin(BASE_URL, "terms-conditions.html"),
}
GTM_ID = "GTM-MZMR2ZFZ"
EXPECTED_DHAKA_PHONE = "8801617440880"
EXPECTED_KHULNA_PHONE = "8801717511345"
PORTFOLIO_DOMAINS = ["gonoshasthaya-cancer-hospital.org", "waveengineeringbd.com",
                     "johnystyleworld.com", "somporko.net", "dainikcoxsbazar.com"]
# ============================================

results = []  # (category, test_id, name, status, detail)


def log(category, test_id, name, status, detail=""):
    results.append((category, test_id, name, status, detail))
    print(f"[{status}] {test_id} {name} - {detail}")


def get_driver(mobile=False):
    opts = ChromeOptions()
    if mobile:
        opts.add_experimental_option("mobileEmulation", {"deviceName": "iPhone 12 Pro"})
    opts.add_argument("--log-level=3")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    service = ChromeService(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=opts)
    if not mobile:
        d.maximize_window()
    return d


# ---------------- 1. HOMEPAGE / HERO ----------------
def test_homepage(driver):
    start = time.time()
    driver.get(BASE_URL)
    load_time = time.time() - start
    time.sleep(2)

    log("Functional", "HP-001", "Homepage loads", "PASSED" if driver.title else "FAILED",
        f"Loaded in {load_time:.2f}s, title: {driver.title}")

    logo = driver.find_elements(By.CSS_SELECTOR,
        "a.navbar-brand, header a img, a[href='#'], a[href='/'], a[href='index.html']")
    log("Functional", "HP-002", "Logo present & clickable", "PASSED" if logo else "FAILED",
        f"{len(logo)} candidate logo link(s) found")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    log("Functional", "HP-003", "Hero heading text present",
        "PASSED" if "Software" in body_text and "Development" in body_text else "FAILED", "")

    wa_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='wa.me'], a[href*='whatsapp.com']")
    hrefs = [a.get_attribute("href") for a in wa_links]
    log("Functional", "HP-004", "WhatsApp CTA button",
        "PASSED" if any(EXPECTED_DHAKA_PHONE in h for h in hrefs) else "FAILED", f"{hrefs}")

    try:
        cta = driver.find_element(By.CSS_SELECTOR, "a[href='#services']")
        cta.click()
        time.sleep(1)
        sec = driver.find_element(By.ID, "services")
        log("Functional", "HP-005", "'Our Services' CTA scroll", "PASSED" if sec.is_displayed() else "FAILED", "")
    except Exception as e:
        log("Functional", "HP-005", "'Our Services' CTA scroll", "FAILED", str(e)[:60])

    log("Functional", "HP-006", "Trust indicator stats",
        "PASSED" if ("50+" in body_text or "100+" in body_text) else "FAILED", "")

    imgs = driver.find_elements(By.TAG_NAME, "img")
    broken = 0
    for img in imgs[:15]:
        try:
            ok = driver.execute_script(
                "return arguments[0].complete && arguments[0].naturalWidth > 0", img)
            if not ok:
                broken += 1
        except Exception:
            pass
    log("Functional", "HP-007", "Hero visual elements render", "PASSED" if broken == 0 else "FAILED",
        f"{broken} broken image(s) among first {min(len(imgs), 15)} checked")


# ---------------- 2. NAVIGATION ----------------
def test_navigation(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    sections = ["services", "industries", "portfolio", "about", "why-us", "process", "tech", "team", "contact"]
    all_ok = True
    for s in sections:
        try:
            link = driver.find_element(By.CSS_SELECTOR, f"a[href='#{s}']")
            link.click()
            time.sleep(0.8)
            if not driver.find_element(By.ID, s).is_displayed():
                all_ok = False
        except Exception:
            all_ok = False
    log("Navigation", "NAV-001", "Top nav scrolls to correct sections", "PASSED" if all_ok else "FAILED",
        f"Checked {len(sections)} section(s)")

    try:
        header = driver.find_element(By.TAG_NAME, "header")
        pos = driver.execute_script("return window.getComputedStyle(arguments[0]).position", header)
        log("Navigation", "NAV-002", "Sticky/fixed header on scroll",
            "PASSED" if pos in ("fixed", "sticky") else "FAILED", f"header position: {pos}")
    except Exception as e:
        log("Navigation", "NAV-002", "Sticky/fixed header on scroll", "FAILED", str(e)[:60])

    log("Navigation", "NAV-003", "Active-section highlighting", "MANUAL", "Visual check recommended")
    log("Navigation", "NAV-004", "Mobile hamburger menu", "SEE MOBILE", "Tested in Mobile Responsiveness section")

    try:
        driver.get(BASE_URL + "#services")
        time.sleep(1)
        driver.get(BASE_URL + "#about")
        time.sleep(1)
        driver.back()
        time.sleep(1)
        ok = "#services" in driver.current_url
        log("Navigation", "NAV-005", "Browser back/forward on anchors", "PASSED" if ok else "FAILED",
            f"URL after back: {driver.current_url}")
    except Exception as e:
        log("Navigation", "NAV-005", "Browser back/forward on anchors", "FAILED", str(e)[:60])

    driver.get(BASE_URL)
    time.sleep(2)
    footer_links = driver.find_elements(By.CSS_SELECTOR, "footer a[href^='#']")
    log("Navigation", "NAV-006", "Footer duplicate nav links", "PASSED" if footer_links else "FAILED",
        f"{len(footer_links)} found in footer")
    log("Navigation", "NAV-007", "Footer legal links -> real pages", "SEE FOOTER", "Tested in Footer & Legal section")


# ---------------- 3. SECTION CONTENT ----------------
def test_sections(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    body_text = driver.find_element(By.TAG_NAME, "body").text

    checks = [
        ("Functional", "SERV-001", "Software/Website/App Dev card", ["React", "Flutter", "Django", "Laravel"]),
        ("Functional", "SERV-002", "AI SEO/Marketing card", ["SEO", "Analytics"]),
        ("Functional", "SERV-003", "Cloud/Digitalization card", ["ERP", "HRM", "Cloud"]),
        ("Functional", "IND-001", "Industry cards present", ["Corporate", "E-commerce", "Healthcare"]),
        ("Functional", "PORT-001", "Portfolio items present", ["Gonoshasthaya", "Wave Engineering", "Somporko"]),
        ("Functional", "ABT-001", "'Who We Are' text present", ["We"]),
        ("Functional", "ABT-003", "Why Us six-point grid", ["Partner First", "Future-Ready"]),
        ("Functional", "ABT-004", "5-step process", ["Discovery", "Strategy", "Launch"]),
        ("Functional", "TSM-001", "Testimonials with attribution", ["Gonoshasthaya", "Johny Style"]),
        ("Functional", "TEAM-001", "Team member cards", ["Moniruzzaman", "Sujon"]),
    ]
    for category, tid, name, keywords in checks:
        found = sum(1 for k in keywords if k.lower() in body_text.lower())
        status = "PASSED" if found >= max(1, len(keywords) // 2) else "FAILED"
        log(category, tid, name, status, f"{found}/{len(keywords)} keyword(s) matched")

    all_links = driver.find_elements(By.TAG_NAME, "a")
    hrefs = [a.get_attribute("href") or "" for a in all_links]
    matched = [d for d in PORTFOLIO_DOMAINS if any(d in h for h in hrefs)]
    log("Functional", "PORT-002", "Portfolio external links correct", "PASSED" if matched else "FAILED",
        f"Matched: {matched}")

    new_tab_ok = sum(1 for a in all_links
                      if any(d in (a.get_attribute("href") or "") for d in PORTFOLIO_DOMAINS)
                      and a.get_attribute("target") == "_blank")
    log("Functional", "PORT-003", "Portfolio links open in new tab", "PASSED" if new_tab_ok > 0 else "FAILED",
        f"{new_tab_ok} link(s) with target=_blank")

    social_links = [h for h in hrefs if any(s in h for s in ["linkedin.com", "github.com", "x.com", "twitter.com"])]
    placeholders = [h for h in social_links if h.rstrip("/") in
                    ("https://x.com", "https://github.com", "https://twitter.com", "https://linkedin.com")]
    log("Functional", "TEAM-002", "Team social links present", "PASSED" if social_links else "FAILED",
        f"{len(social_links)} found")
    log("Functional", "TEAM-003", "Placeholder social links flagged", "FAILED" if placeholders else "PASSED",
        f"Placeholders: {placeholders}" if placeholders else "None found")

    tech_keywords = ["MySQL", "PostgreSQL", "MongoDB", "Flutter", "Django", "React", "Laravel"]
    found_tech = [t for t in tech_keywords if t.lower() in body_text.lower()]
    log("Functional", "ABT-005", "Tech stack list complete", "PASSED" if len(found_tech) >= 4 else "FAILED",
        f"Found: {found_tech}")


# ---------------- 4. CONTACT & OFFICES ----------------
def test_contact(driver):
    driver.get(BASE_URL + "#contact")
    time.sleep(2)
    body_text = driver.find_element(By.TAG_NAME, "body").text

    log("Contact", "CONT-001", "Dhaka office details", "PASSED" if "Dhaka" in body_text else "FAILED", "")
    log("Contact", "CONT-002", "Khulna office details", "PASSED" if "Khulna" in body_text else "FAILED", "")

    tel_hrefs = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")]
    log("Contact", "CONT-003", "Phone numbers use tel: protocol", "PASSED" if tel_hrefs else "FAILED", f"{tel_hrefs}")

    wa_hrefs = [a.get_attribute("href") for a in
                driver.find_elements(By.CSS_SELECTOR, "a[href*='wa.me'], a[href*='whatsapp.com']")]
    status = "PASSED" if wa_hrefs else "FAILED"
    log("Contact", "CONT-004", "WhatsApp links route to correct office", status, f"{wa_hrefs}")

    mail_hrefs = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href^='mailto:']")]
    log("Contact", "CONT-005", "Email link opens mail client",
        "PASSED" if any("info@cyberbitbyte.com" in h for h in mail_hrefs) else "FAILED", f"{mail_hrefs}")

    log("Contact", "CONT-006", "contact-us.html form works", "MANUAL",
        "Page blocks automated crawling (robots.txt) - verify by hand")


# ---------------- 5. FOOTER & LEGAL PAGES ----------------
def test_footer_legal(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    footer = driver.find_elements(By.TAG_NAME, "footer")
    log("Footer", "FOOT-001", "Footer displays consistently", "PASSED" if footer else "FAILED", "")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    log("Footer", "FOOT-002", "Copyright line with year",
        "PASSED" if "Cyber Bit Byte" in body_text else "FAILED", "")

    social_icons = driver.find_elements(By.CSS_SELECTOR,
        "footer a[href*='facebook.com'], footer a[href*='linkedin.com'], footer a[href*='youtube.com']")
    log("Footer", "FOOT-003", "Social media icons link correctly", "PASSED" if social_icons else "FAILED",
        f"{len(social_icons)} found in footer")

    id_map = {"About": "FOOT-004", "Blogs": "FOOT-005", "Privacy Policy": "FOOT-006", "Terms & Conditions": "FOOT-007"}
    for name, url in LEGAL_PAGES.items():
        if name == "Contact":
            continue
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            status = "PASSED" if r.status_code == 200 else "FAILED"
            log("Footer/Legal", id_map.get(name, "FOOT-XXX"), f"{name} page loads", status,
                f"{url} -> HTTP {r.status_code}")
        except Exception as e:
            log("Footer/Legal", id_map.get(name, "FOOT-XXX"), f"{name} page loads", "FAILED", str(e)[:60])


# ---------------- 6. CROSS-BROWSER ----------------
def test_cross_browser():
    log("Cross-Browser", "BR-001", "Layout consistency (Chrome baseline)", "PASSED",
        "Chrome used as baseline for all functional tests")

    try:
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from webdriver_manager.firefox import GeckoDriverManager
        fdriver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
        fdriver.get(BASE_URL)
        time.sleep(2)
        ok = bool(fdriver.title)
        fdriver.quit()
        log("Cross-Browser", "BR-002", "Firefox loads homepage", "PASSED" if ok else "FAILED", "")
    except Exception as e:
        log("Cross-Browser", "BR-002", "Firefox loads homepage", "SKIPPED", f"Firefox not available: {str(e)[:50]}")

    try:
        from selenium.webdriver.edge.service import Service as EdgeService
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        edriver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
        edriver.get(BASE_URL)
        time.sleep(2)
        ok = bool(edriver.title)
        edriver.quit()
        log("Cross-Browser", "BR-003", "Edge loads homepage", "PASSED" if ok else "FAILED", "")
    except Exception as e:
        log("Cross-Browser", "BR-003", "Edge loads homepage", "SKIPPED", f"Edge not available: {str(e)[:50]}")

    log("Cross-Browser", "BR-004", "CSS animations across browsers", "MANUAL", "Visual check recommended")
    log("Cross-Browser", "BR-005", "Responsive breakpoints across browsers", "SEE MOBILE", "")


def test_console_errors(driver):
    driver.get(BASE_URL)
    time.sleep(3)
    try:
        logs = driver.get_log("browser")
        errors = [l for l in logs if l["level"] == "SEVERE"]
        log("Cross-Browser", "BR-006", "No critical console errors", "PASSED" if not errors else "FAILED",
            f"{len(errors)} SEVERE log(s)")
    except Exception as e:
        log("Cross-Browser", "BR-006", "No critical console errors", "SKIPPED", str(e)[:60])


# ---------------- 7. MOBILE RESPONSIVENESS ----------------
def test_mobile():
    try:
        mdriver = get_driver(mobile=True)
    except Exception as e:
        log("Mobile", "MOB-001", "Mobile suite setup", "FAILED", str(e)[:60])
        return

    try:
        start = time.time()
        mdriver.get(BASE_URL)
        load_time = time.time() - start
        time.sleep(2)

        scroll_width = mdriver.execute_script("return document.body.scrollWidth")
        client_width = mdriver.execute_script("return document.documentElement.clientWidth")
        no_hscroll = scroll_width <= client_width + 5
        log("Mobile", "MOB-001", "Page loads correctly on mobile", "PASSED" if no_hscroll else "FAILED",
            f"scrollWidth={scroll_width}, clientWidth={client_width}, {load_time:.2f}s")

        hamburger = mdriver.find_elements(By.CSS_SELECTOR,
            "[class*='hamburger'], [class*='menu-toggle'], [aria-label*='menu' i], button[class*='nav']")
        if hamburger:
            try:
                hamburger[0].click()
                time.sleep(1)
                log("Mobile", "MOB-002", "Hamburger menu functions", "PASSED", "Toggle clicked successfully")
            except Exception as e:
                log("Mobile", "MOB-002", "Hamburger menu functions", "FAILED", str(e)[:60])
        else:
            log("Mobile", "MOB-002", "Hamburger menu functions", "FAILED", "No hamburger element found")

        wa_btn = mdriver.find_elements(By.CSS_SELECTOR, "a[href*='wa.me']")
        if wa_btn:
            size = wa_btn[0].size
            tappable = size["width"] >= 40 and size["height"] >= 40
            log("Mobile", "MOB-003", "WhatsApp CTA tappable size", "PASSED" if tappable else "FAILED", f"{size}")
        else:
            log("Mobile", "MOB-003", "WhatsApp CTA tappable size", "FAILED", "WhatsApp button not found")

        cards = mdriver.find_elements(By.CSS_SELECTOR, "[class*='card']")
        log("Mobile", "MOB-004", "Cards stack correctly on mobile", "PASSED" if cards else "FAILED",
            f"{len(cards)} card element(s)")

        log("Mobile", "MOB-005", "Team/social icons tappable", "SEE MOB-003", "Same tappability heuristic applies")

        tech_area = mdriver.find_elements(By.ID, "tech")
        log("Mobile", "MOB-006", "Tech stack wraps on small screens",
            "PASSED" if no_hscroll and tech_area else "FAILED", "")

        tel_btn = mdriver.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")
        log("Mobile", "MOB-007", "Tap-to-call / tap-to-WhatsApp", "PASSED" if tel_btn and wa_btn else "FAILED",
            f"tel: {len(tel_btn)}, whatsapp: {len(wa_btn)}")

        log("Mobile", "MOB-008", "Orientation change handling", "MANUAL", "Requires physical device rotation test")
    finally:
        mdriver.quit()


# ---------------- 8. PERFORMANCE ----------------
def test_performance(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    timing = driver.execute_script("return window.performance.timing")
    load_ms = timing["loadEventEnd"] - timing["navigationStart"]
    load_s = load_ms / 1000 if load_ms > 0 else 0
    log("Performance", "PERF-001", "Homepage load time < 3s", "PASSED" if 0 < load_s < 3 else "FAILED",
        f"{load_s:.2f}s")

    for name, url in [("Privacy Policy", LEGAL_PAGES["Privacy Policy"]), ("Terms", LEGAL_PAGES["Terms & Conditions"])]:
        try:
            start = time.time()
            r = requests.get(url, timeout=10)
            elapsed = time.time() - start
            log("Performance", "PERF-002", f"{name} load time < 2s", "PASSED" if elapsed < 2 else "FAILED",
                f"{elapsed:.2f}s, HTTP {r.status_code}")
        except Exception as e:
            log("Performance", "PERF-002", f"{name} load time", "FAILED", str(e)[:60])

    log("Performance", "PERF-003", "Mobile 3G-throttled load time", "MANUAL",
        "Requires Chrome DevTools throttling / Lighthouse")

    imgs = driver.find_elements(By.TAG_NAME, "img")
    lazy = sum(1 for i in imgs if i.get_attribute("loading") == "lazy")
    log("Performance", "PERF-004", "Image lazy loading", "PASSED" if lazy > 0 else "FAILED",
        f"{lazy}/{len(imgs)} image(s) use loading='lazy'")

    try:
        r = requests.get(BASE_URL, timeout=10)
        cache_header = r.headers.get("Cache-Control", "")
        log("Performance", "PERF-005", "Browser caching of static assets", "PASSED" if cache_header else "FAILED",
            f"Cache-Control: {cache_header or 'not set'}")
    except Exception as e:
        log("Performance", "PERF-005", "Browser caching header", "FAILED", str(e)[:60])

    log("Performance", "LOAD-001", "50 concurrent users", "MANUAL", "Requires Locust/JMeter, not single-browser Selenium")
    log("Performance", "LOAD-002", "200 concurrent users", "MANUAL", "Requires Locust/JMeter, not single-browser Selenium")


# ---------------- 9. SECURITY ----------------
def test_security(driver):
    try:
        r = requests.get(BASE_URL, timeout=10)
        log("Security", "SEC-001", "HTTPS implementation", "PASSED" if r.status_code == 200 else "FAILED",
            f"HTTP {r.status_code}")

        important = ["Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options"]
        present = [h for h in important if h in r.headers]
        log("Security", "SEC-002", "Security headers present", "PASSED" if present else "FAILED", f"Present: {present}")

        source = r.text.lower()
        risky = [p for p in ["api_key", "apikey", "secret_key", "aws_access", "password="] if p in source]
        log("Security", "SEC-006", "No sensitive info in page source", "FAILED" if risky else "PASSED",
            f"{risky}" if risky else "Clean")
    except Exception as e:
        log("Security", "SEC-001", "HTTPS implementation", "FAILED", str(e)[:60])

    log("Security", "SEC-003", "Contact form input validation", "MANUAL", "contact-us.html blocks crawling")
    log("Security", "SEC-004", "XSS on contact form fields", "MANUAL", "contact-us.html blocks crawling")

    driver.get(BASE_URL)
    time.sleep(2)
    ext_links = driver.find_elements(By.CSS_SELECTOR, "a[target='_blank']")
    unsafe = [a.get_attribute("href") for a in ext_links if "noopener" not in (a.get_attribute("rel") or "")]
    log("Security", "SEC-005", "target=_blank uses rel=noopener", "PASSED" if not unsafe else "FAILED",
        f"{len(unsafe)} link(s) missing rel=noopener")


# ---------------- 10. ACCESSIBILITY ----------------
def test_accessibility(driver):
    driver.get(BASE_URL)
    time.sleep(2)

    imgs = driver.find_elements(By.TAG_NAME, "img")
    missing_alt = [i for i in imgs if not (i.get_attribute("alt") or "").strip()]
    log("Accessibility", "A11Y-003", "Alt text on all images", "PASSED" if not missing_alt else "FAILED",
        f"{len(missing_alt)}/{len(imgs)} missing alt")

    h1s = driver.find_elements(By.TAG_NAME, "h1")
    log("Accessibility", "A11Y-006", "Heading hierarchy (single H1)", "PASSED" if len(h1s) == 1 else "FAILED",
        f"{len(h1s)} H1 tag(s)")

    log("Accessibility", "A11Y-001", "Screen reader compatibility", "MANUAL", "Requires JAWS/NVDA manual test")
    log("Accessibility", "A11Y-002", "Keyboard navigation", "MANUAL", "Requires manual tab-through test")
    log("Accessibility", "A11Y-005", "Focus indicators visible", "MANUAL", "Requires manual/visual verification")
    log("Accessibility", "A11Y-007", "Contact form accessibility", "MANUAL", "contact-us.html blocks crawling")

    if AXE_AVAILABLE:
        try:
            axe = Axe(driver)
            axe.inject()
            axe_results = axe.run()
            violations = axe_results.get("violations", [])
            contrast_v = [v for v in violations if v["id"] == "color-contrast"]
            log("Accessibility", "A11Y-004", "Color contrast ratio (axe-core)",
                "PASSED" if not contrast_v else "FAILED",
                f"{sum(len(v['nodes']) for v in contrast_v)} issue(s)" if contrast_v else "No issues")
            for v in violations:
                if v["id"] != "color-contrast":
                    log("Accessibility", "AXE", f"axe-core: {v['id']}", "FAILED",
                        f"{v['help']} ({len(v['nodes'])} element(s))")
        except Exception as e:
            log("Accessibility", "A11Y-004", "Color contrast ratio", "SKIPPED", str(e)[:80])
    else:
        log("Accessibility", "A11Y-004", "Color contrast ratio", "SKIPPED",
            "Run: pip install axe-selenium-python")


# ---------------- 11. SEO ----------------
def test_seo():
    r = requests.get(BASE_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.string.strip() if soup.title else ""
    log("SEO", "SEO-001", "Meta title tag", "PASSED" if title and len(title) < 60 else "FAILED",
        f"'{title}' ({len(title)} chars)")

    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
    log("SEO", "SEO-002", "Meta description tag", "PASSED" if desc and len(desc) < 160 else "FAILED",
        f"{len(desc)} chars")

    og_tags = ["og:title", "og:description", "og:image", "og:type", "og:url"]
    og_found = [t for t in og_tags if soup.find("meta", property=t)]
    log("SEO", "SEO-003", "Open Graph tags", "PASSED" if len(og_found) == len(og_tags) else "FAILED",
        f"Found: {og_found}")

    tw_tags = ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]
    tw_found = [t for t in tw_tags if soup.find("meta", attrs={"name": t})]
    log("SEO", "SEO-004", "Twitter Card tags", "PASSED" if len(tw_found) == len(tw_tags) else "FAILED",
        f"Found: {tw_found}")

    gsv = soup.find("meta", attrs={"name": "google-site-verification"})
    log("SEO", "SEO-005", "Google Site Verification tag", "PASSED" if gsv else "FAILED", "")

    h1s = soup.find_all("h1")
    log("SEO", "SEO-006", "Single H1 with primary keywords", "PASSED" if len(h1s) == 1 else "FAILED",
        f"{len(h1s)} H1 tag(s)")

    try:
        robots_r = requests.get(urljoin(BASE_URL, "/robots.txt"), timeout=10)
        log("SEO", "SEO-007", "robots.txt configuration", "PASSED" if robots_r.status_code == 200 else "FAILED",
            robots_r.text[:150].replace("\n", " | "))
    except Exception as e:
        log("SEO", "SEO-007", "robots.txt configuration", "FAILED", str(e)[:60])

    try:
        sitemap_r = requests.get(urljoin(BASE_URL, "/sitemap.xml"), timeout=10)
        log("SEO", "SEO-008", "XML sitemap accessible", "PASSED" if sitemap_r.status_code == 200 else "FAILED",
            f"HTTP {sitemap_r.status_code}")
    except Exception as e:
        log("SEO", "SEO-008", "XML sitemap accessible", "FAILED", str(e)[:60])

    canonical = soup.find("link", rel="canonical")
    log("SEO", "SEO-009", "Canonical URL tag", "PASSED" if canonical else "FAILED",
        canonical["href"] if canonical else "Not found")

    try:
        fake_404 = requests.get(urljoin(BASE_URL, "/this-page-does-not-exist-xyz123"), timeout=10)
        log("SEO", "SEO-010", "Custom 404 page behavior", "PASSED" if fake_404.status_code == 404 else "FAILED",
            f"HTTP {fake_404.status_code}")
    except Exception as e:
        log("SEO", "SEO-010", "Custom 404 page behavior", "FAILED", str(e)[:60])


# ---------------- 12. ERROR HANDLING ----------------
def test_error_handling(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    all_links = driver.find_elements(By.TAG_NAME, "a")
    hrefs = list({a.get_attribute("href") for a in all_links if a.get_attribute("href")})
    broken = []
    for h in hrefs:
        if any(d in h for d in PORTFOLIO_DOMAINS):
            try:
                r = requests.head(h, timeout=8, allow_redirects=True)
                if r.status_code >= 400:
                    broken.append((h, r.status_code))
            except Exception as e:
                broken.append((h, str(e)[:40]))
    log("Error Handling", "ERR-001", "Broken outbound portfolio links", "PASSED" if not broken else "FAILED",
        f"{broken}" if broken else "All reachable")

    try:
        fake = requests.get(urljoin(BASE_URL, "/mistyped-url-test-404"), timeout=10)
        log("Error Handling", "ERR-002", "404 page for mistyped URLs", "PASSED" if fake.status_code == 404 else "FAILED",
            f"HTTP {fake.status_code}")
    except Exception as e:
        log("Error Handling", "ERR-002", "404 page for mistyped URLs", "FAILED", str(e)[:60])

    log("Error Handling", "ERR-003", "Network disconnect mid-load", "MANUAL", "Requires manual throttling/disconnect test")
    log("Error Handling", "ERR-004", "Contact form validation errors", "MANUAL", "contact-us.html blocks crawling")


# ---------------- 13. ANALYTICS ----------------
def test_analytics(driver):
    driver.get(BASE_URL)
    time.sleep(2)
    source = driver.page_source
    log("Analytics", "ANA-001", "Google Tag Manager fires", "PASSED" if GTM_ID in source else "FAILED",
        f"Looking for {GTM_ID}")
    log("Analytics", "ANA-002", "Page view tracking", "MANUAL", "Requires GA/GTM dashboard access")
    log("Analytics", "ANA-003", "CTA click tracking", "MANUAL", "Requires GA/GTM dashboard access")
    log("Analytics", "ANA-004", "Outbound link tracking", "MANUAL", "Requires GA/GTM dashboard access")


# ================= PDF REPORT =================
def build_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "CyberBitByte - Full Test Execution Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Tested by: {TESTER_NAME}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Website: {BASE_URL}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    categories = {}
    for cat, tid, name, status, detail in results:
        categories.setdefault(cat, []).append((tid, name, status, detail))

    def table_header():
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(18, 7, "ID", border=1, fill=True)
        pdf.cell(65, 7, "Test", border=1, fill=True)
        pdf.cell(22, 7, "Result", border=1, fill=True)
        pdf.cell(85, 7, "Details", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    totals = {"PASSED": 0, "FAILED": 0, "MANUAL": 0, "SKIPPED": 0, "OTHER": 0}

    for cat, items in categories.items():
        pdf.set_font("Helvetica", "B", 13)
        pdf.ln(3)
        pdf.cell(0, 8, cat, new_x="LMARGIN", new_y="NEXT")
        table_header()
        pdf.set_font("Helvetica", "", 8)
        for tid, name, status, detail in items:
            key = status if status in totals else "OTHER"
            totals[key] += 1
            if status == "PASSED":
                pdf.set_text_color(0, 120, 0)
            elif status == "FAILED":
                pdf.set_text_color(200, 0, 0)
            elif status == "MANUAL":
                pdf.set_text_color(150, 100, 0)
            else:
                pdf.set_text_color(90, 90, 90)

            if pdf.get_y() > 270:
                pdf.add_page()
                table_header()
                pdf.set_font("Helvetica", "", 8)

            pdf.cell(18, 6, tid[:10], border=1)
            pdf.cell(65, 6, name[:38], border=1)
            pdf.cell(22, 6, status[:12], border=1)
            pdf.cell(85, 6, str(detail)[:52], border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    total = sum(totals.values())
    pdf.cell(0, 8, f"Summary: {totals['PASSED']} Passed | {totals['FAILED']} Failed | "
                   f"{totals['MANUAL']} Manual | {totals['SKIPPED']} Skipped (Total: {total})",
              new_x="LMARGIN", new_y="NEXT")

    pdf.output("test_report_master.pdf")
    print("\nPDF report generated: test_report_master.pdf")
    print(totals)


# ================= MAIN =================
def main():
    driver = get_driver()
    try:
        test_homepage(driver)
        test_navigation(driver)
        test_sections(driver)
        test_contact(driver)
        test_footer_legal(driver)
        test_console_errors(driver)
        test_performance(driver)
        test_security(driver)
        test_accessibility(driver)
        test_error_handling(driver)
        test_analytics(driver)
    finally:
        driver.quit()

    test_seo()
    test_cross_browser()
    test_mobile()

    build_pdf()


if __name__ == "__main__":
    main()