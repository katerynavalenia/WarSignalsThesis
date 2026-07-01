"""
GKG bulk download — memory-bounded, monthly batches.

Processes one month at a time:
  1. Download all days in the month in parallel (6 workers)
  2. Parse + filter each day immediately, discard raw CSV
  3. Save per-(query, month) parquet
  4. Clear memory, move to next month

Memory bounded to ~1 month of GKG data (~3-4 GB).
Resumable: skips months where all 4 query parquets already exist.
"""
import gc
import io
import sys
import time
import zipfile
import logging
from pathlib import Path
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import yaml

logging.basicConfig(
    filename='/tmp/gkg_download.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s',
)
log = logging.getLogger(__name__)

sys.path.insert(0, '/home/mykyta/Desktop/katya/WarSignalsThesis')

# =========================================================================
# Config
# =========================================================================
with open('config/gdelt_queries.yaml') as f:
    cfg = yaml.safe_load(f)
QUERIES = cfg['queries']

OUTPUT_DIR = Path('/home/mykyta/Desktop/katya/WarSignalsThesis/data/news_colab_sim/war_signals_phase3/raw_enriched')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START = date(2022, 9, 29)
END = date(2026, 6, 21)

GKG_BASE = "http://data.gdeltproject.org/gkg"
WORKERS = 2  # 2 parallel downloads, parse sequentially to bound memory


# =========================================================================
# Helpers
# =========================================================================
def flatten_keywords(per_lang) -> list[str]:
    out = []
    if isinstance(per_lang, list):
        return list(per_lang)
    if isinstance(per_lang, dict):
        for lang, words in per_lang.items():
            if isinstance(words, list):
                out.extend(words)
    return out


QUERY_KEYWORDS = []
for q in QUERIES:
    kw_any = [k.lower() for k in flatten_keywords(q.get('keywords_any', {}))]
    kw_weapon = [k.lower() for k in flatten_keywords(q.get('keywords_weapon_any', {}))]
    QUERY_KEYWORDS.append((q['name'], kw_any, kw_weapon))


def _parse_tone(tone_field: str) -> dict[str, float]:
    """Parse GKG TONE field (field 7) into component scores.

    Format: COMMA-separated values (verified from actual GKG data)
        tone, positive_score, negative_score, polarity, activity_density,
        self_group_density, [word_count]
    Example: "-3.162,0.988,4.150,5.138,18.379,0"
    Returns dict with keys: tone_avg, tone_positive, tone_negative,
    tone_polarity, tone_activity. Missing/invalid → None.
    """
    if not tone_field or not tone_field.strip():
        return {'tone_avg': None, 'tone_positive': None,
                'tone_negative': None, 'tone_polarity': None,
                'tone_activity': None}
    try:
        parts = tone_field.split(',')
        return {
            'tone_avg': float(parts[0]) if len(parts) > 0 and parts[0].strip() else None,
            'tone_positive': float(parts[1]) if len(parts) > 1 and parts[1].strip() else None,
            'tone_negative': float(parts[2]) if len(parts) > 2 and parts[2].strip() else None,
            'tone_polarity': float(parts[3]) if len(parts) > 3 and parts[3].strip() else None,
            'tone_activity': float(parts[4]) if len(parts) > 4 and parts[4].strip() else None,
        }
    except (ValueError, IndexError):
        return {'tone_avg': None, 'tone_positive': None,
                'tone_negative': None, 'tone_polarity': None,
                'tone_activity': None}


def _parse_countries_from_locations(locations_field: str) -> str:
    """Extract country codes from GKG LOCATIONS field (field 4).

    GKG LOCATIONS format: semicolon-separated location entries, each like:
        "4#Black Sea, Oceans (General), Oceans#OS#OS00#43#35#-1506338"
    The 2-letter country code appears after the first '#' and before the
    second '#' in each entry.

    Returns semicolon-separated ISO 3166-1 alpha-2 country codes.
    Example: "OS;RS;UP" (Black Sea, Russia, Ukraine)
    """
    if not locations_field or not locations_field.strip():
        return ""
    codes = []
    for entry in locations_field.split(';'):
        # Each entry: "offset#Location Name#COUNTRY_CODE#..."
        parts = entry.split('#')
        if len(parts) >= 3:
            code = parts[2].strip().upper()
            # Validate: must be 2 alpha chars
            if len(code) == 2 and code.isalpha():
                codes.append(code)
    return ';'.join(codes)


def parse_and_filter(csv_text: str) -> dict[str, list[dict]]:
    """Parse one day's GKG CSV and filter for all queries.

    Returns {query_name: [matched_rows]}.
    Each row contains: date, domain, url, tone_*, countries, persons, orgs, themes.
    Discards the raw CSV text immediately after parsing.
    """
    # Parse into rows with haystack
    all_rows = []
    for line in csv_text.splitlines():
        if not line.startswith('20'):
            continue
        fields = line.split('\t')
        if len(fields) < 11:
            continue
        date_str = fields[0]
        themes = fields[3] if len(fields) > 3 else ''
        locations = fields[4] if len(fields) > 4 else ''
        persons = fields[5] if len(fields) > 5 else ''
        orgs = fields[6] if len(fields) > 6 else ''
        tone_field = fields[7] if len(fields) > 7 else ''
        # Field 8 = CAMEOEVENTIDS (NOT countries — countries are in LOCATIONS)
        sources_str = fields[9] if len(fields) > 9 else ''
        urls_str = fields[10] if len(fields) > 10 else ''

        sources = [s.strip() for s in sources_str.split(';') if s.strip()]
        urls = [u.strip() for u in urls_str.split(';') if u.strip()]

        haystack = " ".join([themes, locations, persons, orgs,
                             sources_str, urls_str]).lower()

        # Parse tone (field 7, comma-separated) and countries (from LOCATIONS field 4)
        tone = _parse_tone(tone_field)
        countries = _parse_countries_from_locations(locations)

        n = max(len(sources), len(urls), 1)
        for i in range(n):
            src = sources[i] if i < len(sources) else (sources[0] if sources else '')
            url = urls[i] if i < len(urls) else (urls[0] if urls else '')
            all_rows.append((src, url, haystack, tone, countries,
                             persons, orgs, themes))

    # Filter for each query
    result: dict[str, list[dict]] = {q[0]: [] for q in QUERY_KEYWORDS}
    for src, url, haystack, tone, countries, persons, orgs, themes in all_rows:
        for qname, kw_any, kw_weapon in QUERY_KEYWORDS:
            if not kw_any and not kw_weapon:
                continue
            if kw_any and not any(k in haystack for k in kw_any):
                continue
            if kw_weapon and not any(k in haystack for k in kw_weapon):
                continue
            result[qname].append({
                'date': date_str,
                'domain': src,
                'url': url,
                'tone_avg': tone['tone_avg'],
                'tone_positive': tone['tone_positive'],
                'tone_negative': tone['tone_negative'],
                'tone_polarity': tone['tone_polarity'],
                'tone_activity': tone['tone_activity'],
                'countries': countries,
                'persons': persons,
                'orgs': orgs,
                'themes': themes,
            })
    return result


def download_gkg_day(d: date) -> tuple:
    """Download a single GKG daily zip. Returns (date, csv_text or None)."""
    url = f"{GKG_BASE}/{d.strftime('%Y%m%d')}.gkg.csv.zip"
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                return d, zf.read(zf.namelist()[0]).decode('utf-8', errors='replace')
        elif r.status_code == 404:
            return d, None
    except Exception as e:
        log.warning(f"download error for {d}: {e}")
    return d, None


def month_is_done(month_key: str) -> bool:
    """Check if all 4 queries have a parquet for this month."""
    for qname, _, _ in QUERY_KEYWORDS:
        if not (OUTPUT_DIR / f"raw_{qname}_{month_key}.parquet").exists():
            return False
    return True


def get_month_days(month_key: str) -> list[date]:
    """Get all days in a month that fall within [START, END]."""
    y, m = map(int, month_key.split('-'))
    first = date(y, m, 1)
    if m == 12:
        last = date(y, m, 31)
    else:
        last = date(y, m + 1, 1) - timedelta(days=1)
    days = []
    d = max(first, START)
    while d <= min(last, END):
        days.append(d)
        d += timedelta(days=1)
    return days


def process_month(month_key: str) -> dict[str, int]:
    """Download + filter + save one month. Returns {query_name: n_articles}."""
    days = get_month_days(month_key)
    if not days:
        return {}

    # Accumulate per-query for this month only
    monthly: dict[str, list[dict]] = {q[0]: [] for q in QUERY_KEYWORDS}
    n_ok = 0
    n_404 = 0

    # Download in parallel (2 workers), but parse sequentially
    # so we never hold more than 1 CSV (~100MB) in memory at a time
    pending_csvs: list[tuple[date, str]] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(download_gkg_day, d): d for d in days}
        for fut in as_completed(futures):
            d, csv_text = fut.result()
            if csv_text is None:
                n_404 += 1
                continue
            n_ok += 1
            # Parse + filter immediately, then discard the CSV
            filtered = parse_and_filter(csv_text)
            del csv_text  # free ~100MB immediately
            for qname, rows in filtered.items():
                monthly[qname].extend(rows)
            del filtered
            gc.collect()  # force cleanup after each day

    # Save per-query parquets for this month
    counts = {}
    for qname, _, _ in QUERY_KEYWORDS:
        rows = monthly[qname]
        if rows:
            df = pd.DataFrame(rows)
            # Dedup by URL within the month
            df = df.drop_duplicates(subset=['url'], keep='last')
            out_file = OUTPUT_DIR / f"raw_{qname}_{month_key}.parquet"
            df.to_parquet(out_file)
            counts[qname] = len(df)
        else:
            # Save empty marker so month_is_done() returns True
            pd.DataFrame(columns=['date', 'domain', 'url', 'tone_avg',
                                  'tone_positive', 'tone_negative',
                                  'tone_polarity', 'tone_activity',
                                  'countries', 'persons', 'orgs', 'themes']
                         ).to_parquet(OUTPUT_DIR / f"raw_{qname}_{month_key}.parquet")
            counts[qname] = 0

    # Free memory
    del monthly
    gc.collect()

    log.info(f"month {month_key}: ok={n_ok} 404={n_404} counts={counts}")
    return counts


def main():
    # Generate list of months
    months = []
    d = START.replace(day=1)
    while d <= END:
        months.append(d.strftime('%Y-%m'))
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)

    # Skip already-done months
    todo = [m for m in months if not month_is_done(m)]

    print("=" * 70)
    print("GKG BULK DOWNLOAD — Phase 3 (monthly batches, memory-bounded)")
    print("=" * 70)
    print(f"Date range: {START} → {END}")
    print(f"Total months: {len(months)}")
    print(f"Already done: {len(months) - len(todo)}")
    print(f"To download: {len(todo)}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Workers: {WORKERS}")
    print()

    if not todo:
        print("All months done!")
        _print_summary()
        return

    t0 = time.time()
    for i, month_key in enumerate(todo):
        mt0 = time.time()
        print(f"[{i+1}/{len(todo)}] Month {month_key}...", end=" ", flush=True)
        counts = process_month(month_key)
        elapsed = time.time() - mt0
        total = sum(counts.values())
        print(f"{total:,} articles ({elapsed/60:.1f}m) "
              f"R={counts.get('russian_attack_direct', 0):,} "
              f"U={counts.get('ukraine_defense_energy', 0):,} "
              f"D={counts.get('defense_industry_western', 0):,} "
              f"E={counts.get('energy_war', 0):,}")

    print(f"\n{'='*70}")
    print("DONE")
    print("=" * 70)
    print(f"Wall time: {(time.time()-t0)/60:.1f} min")
    _print_summary()


def _print_summary():
    for qname, _, _ in QUERY_KEYWORDS:
        files = list(OUTPUT_DIR.glob(f'raw_{qname}_*.parquet'))
        total = sum(len(pd.read_parquet(f)) for f in files)
        print(f"  {qname}: {total:,} articles in {len(files)} months")


if __name__ == "__main__":
    main()