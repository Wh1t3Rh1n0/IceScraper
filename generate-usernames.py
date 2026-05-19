from os.path import exists
import argparse
import csv
import re
import sys


def extract_names(filename):
    """Returns list of names from first column of a CSV or text file."""
    names = []
    if exists(filename):
        with open(filename, newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in csvreader:
                names.append(row[0])
    return [name.strip() for name in names]


def load_aliases(filename):
    """Returns dict mapping lowercase full name -> list of aliases."""
    aliases = {}
    if not filename or not exists(filename):
        return aliases
    with open(filename, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in csvreader:
            if len(row) < 2:
                continue
            key = row[0].strip().lower()
            aliases[key] = [a.strip().lower() for a in row[1:] if a.strip()]
    return aliases


def clean_and_sort_names(names):
    """Remove titles, suffixes, non-alpha chars; deduplicate and sort."""
    titles_suffixes = r'\([^)]+\)?|, ?[a-z]?[A-Z.]+|^(Dr|Mrs?|Ms)\.? ?'
    names = [re.sub(titles_suffixes, '', name) for name in names]

    non_names = r'[^A-Za-z ]|LinkedIn Member'
    names = [re.sub(non_names, '', name) for name in names]

    multiple_spaces = r' +'
    names = [re.sub(multiple_spaces, ' ', name).strip() for name in names]

    names = [name.lower() for name in names]

    while '' in names:
        names.remove('')

    names = list(set(names))
    names.sort()
    return names


def parse_name_parts(name):
    """Split name into (first, middle, last, f, m, l)."""
    parts = name.split(' ')
    first = parts[0]
    f = first[0] if first else ''
    if len(parts) >= 3:
        last = parts[-1]
        middle = ' '.join(parts[1:-1])
        m = parts[1][0] if parts[1] else ''
        l = last[0] if last else ''
    elif len(parts) == 2:
        last = parts[1]
        middle = ''
        m = ''
        l = last[0] if last else ''
    else:
        last = middle = m = l = ''
    return first, middle, last, f, m, l


ALL_PATTERNS = [
    "{first}.{last}",
    "{f}.{last}",
    "{f}{last}",
    "{first}{last}",
    "{last}.{first}",
    "{last}{f}",
    "{last}{first}",
    "{first}_{last}",
    "{f}_{last}",
    "{first}{l}",
    "{first}.{m}{last}",
    "{f}{m}{last}",
]


def convert_to_usernames(names, fstring, alias_map=None, domain=None):
    usernames = []

    patterns = ALL_PATTERNS if fstring == '--all' else [fstring]

    for name in names:
        first, middle, last, f, m, l = parse_name_parts(name)

        if not last:
            continue

        candidate_firsts = [(first, f, m)]

        if alias_map and name in alias_map:
            for alias in alias_map[name]:
                alias_f = alias[0] if alias else ''
                candidate_firsts.append((alias, alias_f, m))

        for cf, cf_init, cm in candidate_firsts:
            tvals = {
                'first': cf,
                'f': cf_init,
                'last': last,
                'l': l,
                'middle': middle,
                'm': cm,
            }
            for pat in patterns:
                try:
                    result = pat.format(**tvals)
                    if domain:
                        result = result + '@' + domain
                    usernames.append(result)
                except KeyError:
                    pass

    return usernames


usage = """
generate-usernames.py
=====================

Generates usernames or email addresses from a list of names.

Input: CSV or text file with names in first column.

Template tokens:
    {first}   : First name
    {last}    : Last name
    {f}       : First initial
    {l}       : Last initial
    {middle}  : Middle name (empty if absent)
    {m}       : Middle initial (empty if absent)

Usage:
    python3 generate-usernames.py <Template> <Name File(s)> [options]
    python3 generate-usernames.py --all <Name File(s)> [options]

Options:
    --aliases <file>   CSV: "Full Name,Alias1,Alias2,..." per line
    --domain <domain>  Append @domain to every username

Examples:
    python3 generate-usernames.py "{f}{last}@acme.com" employees.csv
    python3 generate-usernames.py --all employees.csv --domain acme.com
    python3 generate-usernames.py "{f}{m}{last}" employees.csv --aliases aliases.csv
"""

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('template', nargs='?', default=None)
parser.add_argument('name_files', nargs='*')
parser.add_argument('--aliases', default=None)
parser.add_argument('--domain', default=None)
parser.add_argument('-h', '--help', action='store_true')

args = parser.parse_args()

if args.help or not args.template or not args.name_files:
    print(usage)
    sys.exit()

alias_map = load_aliases(args.aliases)

names = []
for filename in args.name_files:
    names += extract_names(filename)

names = clean_and_sort_names(names)

usernames = list(set(convert_to_usernames(names, args.template, alias_map, args.domain)))
usernames.sort()

print("\n".join(usernames))
