"""
merge-results.py
================

Merge multiple IceScraper output CSVs into a single deduplicated file.
Deduplication is on normalized (lowercase, stripped) name.
A 'source' column is prepended to each row.

Supported source files (detected by filename prefix):
    scraper-linkedin_unauth.csv  -> columns: name, title, company
    scraper-linkedin_auth.csv    -> columns: name, title, location, profile_url
    scraper-zoominfo.csv         -> columns: name, company, title, country, state, city
    scraper-hunterio.csv         -> columns: name, position, email, linkedin_url
    scraper-apollo.csv           -> columns: name, title, org, email, linkedin_url
    scraper-github.csv           -> columns: login, html_url, type

Usage:
    python3 merge-results.py <file1> <file2> ... [-o output.csv]

Options:
    -o, --output   Output file path (default: merged-results.csv)

Example:
    python3 merge-results.py scraper-linkedin_auth.csv scraper-zoominfo.csv -o merged.csv
"""

import argparse
import csv
import os
import re
import sys


SOURCE_SCHEMAS = {
    'linkedin_unauth': ['name', 'title', 'company'],
    'linkedin_auth':   ['name', 'title', 'location', 'profile_url'],
    'zoominfo':        ['name', 'company', 'title', 'country', 'state', 'city'],
    'hunterio':        ['name', 'position', 'email', 'linkedin_url'],
    'apollo':          ['name', 'title', 'org', 'email', 'linkedin_url'],
    'github':          ['login', 'html_url', 'type'],
}

ALL_FIELDS = ['source', 'name', 'title', 'company', 'org', 'location',
              'country', 'state', 'city', 'email', 'linkedin_url',
              'profile_url', 'position', 'login', 'html_url', 'type']


def detect_source(filename):
    base = os.path.basename(filename).lower()
    for key in SOURCE_SCHEMAS:
        if key in base:
            return key
    return None


def normalize_name(name):
    return re.sub(r'\s+', ' ', name.strip().lower())


def load_csv(filepath, source_key):
    schema = SOURCE_SCHEMAS.get(source_key, [])
    rows = []
    with open(filepath, newline='', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        for raw in reader:
            record = {'source': source_key}
            for i, field in enumerate(schema):
                record[field] = raw[i].strip() if i < len(raw) else ''
            rows.append(record)
    return rows


def main():
    parser = argparse.ArgumentParser(description='Merge IceScraper CSVs')
    parser.add_argument('files', nargs='+', help='Input CSV files')
    parser.add_argument('-o', '--output', default='merged-results.csv')
    args = parser.parse_args()

    seen_names = {}
    ordered = []

    for filepath in args.files:
        if not os.path.exists(filepath):
            print("Warning: file not found: %s" % filepath, file=sys.stderr)
            continue

        source_key = detect_source(filepath)
        if source_key is None:
            print("Warning: unknown source format for %s — skipping" % filepath, file=sys.stderr)
            continue

        rows = load_csv(filepath, source_key)
        name_field = 'login' if source_key == 'github' else 'name'

        for record in rows:
            raw_name = record.get(name_field, '')
            key = normalize_name(raw_name)
            if not key:
                continue
            if key not in seen_names:
                seen_names[key] = True
                ordered.append(record)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=ALL_FIELDS, extrasaction='ignore',
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for record in ordered:
            row = {field: record.get(field, '') for field in ALL_FIELDS}
            writer.writerow(row)

    print("Wrote %d deduplicated records to %s" % (len(ordered), args.output))


if __name__ == '__main__':
    main()
