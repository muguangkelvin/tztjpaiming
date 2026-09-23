import os
import re
import json
import sys
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
DATA_DIR = os.path.join(ROOT_DIR, "data")

def run_verification():
    print("=== Starting Comprehensive Site Verification for tztjpaiming.xyz ===")
    errors = []
    warnings = []

    # 1. Check Public Dir Exists
    if not os.path.exists(PUBLIC_DIR):
        errors.append("PUBLIC_DIR does not exist.")
        return errors, warnings

    # 2. Check Robots.txt and Sitemap.xml
    robots_path = os.path.join(PUBLIC_DIR, "robots.txt")
    if not os.path.exists(robots_path):
        errors.append("robots.txt is missing.")
    else:
        with open(robots_path, "r", encoding="utf-8") as f:
            txt = f.read()
            if "Sitemap: https://tztjpaiming.xyz/sitemap.xml" not in txt:
                errors.append("robots.txt does not contain valid Sitemap directive.")

    sitemap_path = os.path.join(PUBLIC_DIR, "sitemap.xml")
    if not os.path.exists(sitemap_path):
        errors.append("sitemap.xml is missing.")
    else:
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            locs = [elem.text for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            print(f"[Pass] sitemap.xml parsed successfully with {len(locs)} URLs.")
            for loc in locs:
                if not loc.startswith("https://tztjpaiming.xyz/"):
                    errors.append(f"Invalid domain in sitemap URL: {loc}")
        except Exception as e:
            errors.append(f"Failed to parse sitemap.xml: {e}")

    # 3. Check 28 Providers Data & Links
    providers_path = os.path.join(DATA_DIR, "providers.json")
    with open(providers_path, "r", encoding="utf-8") as f:
        providers = json.load(f)

    if len(providers) != 28:
        errors.append(f"Expected 28 providers, found {len(providers)}")
    else:
        print(f"[Pass] Exactly 28 providers configured in providers.json.")

    # Check Top 4 Fixed Order
    expected_top4 = ["lingdong", "twilight", "flycat-cloud", "breezenet"]
    actual_top4 = [p["slug"] for p in providers[:4]]
    if actual_top4 != expected_top4:
        errors.append(f"Top 4 provider order mismatch! Expected {expected_top4}, got {actual_top4}")
    else:
        print("[Pass] Top 4 provider rankings verified (#1 LingDong Cloud, #2 Twilight, #3 FlyCat Cloud, #4 Breezenet).")

    # 4. Scan HTML Files for H1, Title, Canonical, and Blocklist
    blocklist = ["猫梦博客", "三毛机场", "星维机场", "一毛机场", "Gaterank", "根据某博客"]
    html_count = 0

    for root_dir, dirs, files in os.walk(PUBLIC_DIR):
        for fname in files:
            if fname.endswith(".html"):
                html_count += 1
                fpath = os.path.join(root_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Blocklist Check
                for b_term in blocklist:
                    if b_term in html_content:
                        errors.append(f"Blocklisted term '{b_term}' found in file: {fpath}")

                # H1 Count
                h1_matches = re.findall(r"<h1[^>]*>.*?</h1>", html_content, re.DOTALL | re.IGNORECASE)
                if len(h1_matches) == 0:
                    errors.append(f"No H1 tag found in {fpath}")
                elif len(h1_matches) > 1:
                    errors.append(f"Multiple H1 tags ({len(h1_matches)}) found in {fpath}")

                # Title Tag
                if "<title>" not in html_content:
                    errors.append(f"Missing <title> tag in {fpath}")

                # Canonical
                if 'rel="canonical"' not in html_content:
                    errors.append(f"Missing canonical tag in {fpath}")

                # Sponsored rel attribute check on affiliate links
                aff_links = re.findall(r'href="(https://[^"]*code=[^"]*)"([^>]*)', html_content)
                for aff_url, attrs in aff_links:
                    if 'rel="sponsored nofollow noopener"' not in attrs:
                        errors.append(f"Affiliate link missing required rel attributes: {aff_url} in {fpath}")

    print(f"[Pass] Scanned {html_count} HTML files for structural integrity and compliance.")

    # 5. Summary
    print(f"=== Verification Completed: {len(errors)} Errors, {len(warnings)} Warnings ===")
    return errors, warnings

if __name__ == "__main__":
    errs, warns = run_verification()
    if errs:
        print("ERRORS FOUND:")
        for e in errs:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
