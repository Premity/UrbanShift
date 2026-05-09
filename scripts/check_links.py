#!/usr/bin/env python3
"""
Usage:
    docker compose exec api python -m scripts.check_links
"""

import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import httpx

ROOT = Path(__file__).resolve().parent.parent

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class LinkOccurrence:
    def __init__(self, file_name: str, entry_id: str, entry_name: str, field: str):
        self.file_name = file_name
        self.entry_id = entry_id
        self.entry_name = entry_name
        self.field = field


async def check_single_url(
    client_verify: httpx.AsyncClient,
    client_no_verify: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> Tuple[str, bool, str]:
    """
    Checks a single URL and returns (url, is_valid, error_message).
    """
    async with semaphore:
        # First try with SSL verification
        try:
            response = await client_verify.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
            if response.status_code >= 400:
                return url, False, f"HTTP {response.status_code}"
            return url, True, ""
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            return url, False, "Timeout"
        except Exception as first_exc:
            # If the first attempt failed, try with verify=False to see if it's an SSL/trust issue
            try:
                response = await client_no_verify.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
                if response.status_code >= 400:
                    return url, False, f"HTTP {response.status_code} (SSL Warning)"
                return url, True, "SSL Warning (unverified certificate)"
            except Exception:
                # If both fail, report the first error
                err_name = type(first_exc).__name__
                if "SSLError" in err_name or "ssl" in str(first_exc).lower():
                    return url, False, "SSL Error"
                return url, False, f"Connection Error: {err_name}"


async def check_all_links(urls_map: Dict[str, List[LinkOccurrence]]) -> None:
    unique_urls = list(urls_map.keys())
    print(f"Total unique URLs to check: {len(unique_urls)}\n")

    # Limit concurrency to 15 concurrent requests to avoid overload or rate-limiting
    semaphore = asyncio.Semaphore(15)

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
    async with httpx.AsyncClient(limits=limits, verify=True) as client_verify, \
               httpx.AsyncClient(limits=limits, verify=False) as client_no_verify:
        
        tasks = [
            check_single_url(client_verify, client_no_verify, url, semaphore)
            for url in unique_urls
        ]
        
        # Gather results with progress feedback
        results = []
        completed = 0
        for future in asyncio.as_completed(tasks):
            url, is_valid, err = await future
            results.append((url, is_valid, err))
            completed += 1
            if completed % 10 == 0 or completed == len(unique_urls):
                print(f" Progress: {completed}/{len(unique_urls)} checked...")

    # Process results
    valid_count = 0
    invalid_count = 0
    ssl_warning_count = 0
    
    url_results = {}
    for url, is_valid, err in results:
        url_results[url] = (is_valid, err)
        if is_valid:
            valid_count += 1
            if "SSL Warning" in err:
                ssl_warning_count += 1
        else:
            invalid_count += 1

    print("\n" + "="*80)
    print(" LINK CHECKER SUMMARY")
    print("="*80)
    print(f"Total unique URLs checked: {len(unique_urls)}")
    print(f"✓ Valid URLs:             {valid_count} (including {ssl_warning_count} with SSL warnings)")
    print(f"✗ Invalid URLs:           {invalid_count}")
    print("="*80 + "\n")

    if invalid_count > 0:
        print("INVALID LINKS DETAILS:")
        print("-" * 120)
        print(f"{'FILE':<25} | {'ENTRY ID':<15} | {'ENTRY NAME':<30} | {'FIELD':<12} | {'ERROR':<25} | {'URL'}")
        print("-" * 120)

        # Sort entries by file, then ID
        all_invalid_occurrences = []
        for url, occurrences in urls_map.items():
            is_valid, err = url_results[url]
            if not is_valid:
                for occ in occurrences:
                    all_invalid_occurrences.append((occ, err, url))

        all_invalid_occurrences.sort(key=lambda x: (x[0].file_name, x[0].entry_id))

        for occ, err, url in all_invalid_occurrences:
            name_truncated = occ.entry_name[:28] + ".." if len(occ.entry_name) > 30 else occ.entry_name
            print(f"{occ.file_name:<25} | {occ.entry_id:<15} | {name_truncated:<30} | {occ.field:<12} | {err:<25} | {url}")
        print("-" * 120)
    else:
        print("🎉 High Five! All links in all files are valid and reachable!")


def main() -> None:
    urls_map: Dict[str, List[LinkOccurrence]] = {}

    # 1. Load schemes.json
    schemes_file = ROOT / "data" / "seed" / "schemes.json"
    if schemes_file.exists():
        try:
            with open(schemes_file, "r", encoding="utf-8") as f:
                schemes_data = json.load(f)
                for item in schemes_data:
                    entry_id = item.get("id", "?")
                    entry_name = item.get("name", "?")
                    
                    for field in ("apply_link", "source_url"):
                        url = item.get(field)
                        if url and url.startswith("http"):
                            occ = LinkOccurrence("schemes.json", entry_id, entry_name, field)
                            urls_map.setdefault(url, []).append(occ)
            print(f"Loaded schemes.json successfully ({len(schemes_data)} entries)")
        except Exception as e:
            print(f"Error reading schemes.json: {e}")
    else:
        print(f"Warning: schemes.json not found at {schemes_file}")

    # 2. Load housing.json
    housing_file = ROOT / "data" / "seed" / "housing.json"
    if housing_file.exists():
        try:
            with open(housing_file, "r", encoding="utf-8") as f:
                housing_data = json.load(f)
                for item in housing_data:
                    entry_id = item.get("id", "?")
                    entry_name = item.get("name", "?")
                    url = item.get("source_url")
                    if url and url.startswith("http"):
                        occ = LinkOccurrence("housing.json", entry_id, entry_name, "source_url")
                        urls_map.setdefault(url, []).append(occ)
            print(f"Loaded housing.json successfully ({len(housing_data)} entries)")
        except Exception as e:
            print(f"Error reading housing.json: {e}")
    else:
        print(f"Warning: housing.json not found at {housing_file}")

    # 3. Load jobs_with_scheme_links.csv
    jobs_file = ROOT / "data" / "seed" / "jobs_with_scheme_links.csv"
    if jobs_file.exists():
        try:
            with open(jobs_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                jobs_count = 0
                for row in reader:
                    jobs_count += 1
                    entry_id = row.get("id", "?")
                    entry_name = row.get("title", "?")
                    url = row.get("source_url")
                    if url and url.startswith("http"):
                        occ = LinkOccurrence("jobs_with_scheme_links.csv", entry_id, entry_name, "source_url")
                        urls_map.setdefault(url, []).append(occ)
            print(f"Loaded jobs_with_scheme_links.csv successfully ({jobs_count} entries)")
        except Exception as e:
            print(f"Error reading jobs_with_scheme_links.csv: {e}")
    else:
        print(f"Warning: jobs_with_scheme_links.csv not found at {jobs_file}")

    if not urls_map:
        print("No valid URLs found in any of the seed files.")
        return

    # Run check
    asyncio.run(check_all_links(urls_map))


if __name__ == "__main__":
    main()
