from os.path import exists
import argparse
import csv
import re
import sys


def extract_name(line):
    """Returns name from first column of a CSV line."""
    return line.split(',')[0].replace('"', '')


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


def clean_name(name):
    """Remove titles, suffixes, non-alpha chars."""
    titles_suffixes = r'\([^)]+\)?|, ?[a-z]?[A-Z.]+|^(Dr|Mrs?|Ms)\.? ?'
    name = re.sub(titles_suffixes, '', name)

    non_names = r'[^A-Za-z ]|LinkedIn Member'
    name = re.sub(non_names, '', name)

    multiple_spaces = r' +'
    name = re.sub(multiple_spaces, ' ', name).strip()

    return name.lower()


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


def convert_to_username(name, fstring, alias_map=None):
    """Returns list of usernames for a name (including aliases)."""
    if name == '':
        return ['']

    first, middle, last, f, m, l = parse_name_parts(name)

    candidate_firsts = [(first, f, m)]

    if alias_map and name in alias_map:
        for alias in alias_map[name]:
            alias_f = alias[0] if alias else ''
            candidate_firsts.append((alias, alias_f, m))

    results = []
    for cf, cf_init, cm in candidate_firsts:
        tvals = {
            'first': cf,
            'f': cf_init,
            'last': last,
            'l': l,
            'middle': middle,
            'm': cm,
        }
        try:
            results.append(fstring.format(**tvals))
        except KeyError:
            pass

    return results if results else ['']


usage = """
generate-usernames-csv.py
=========================

Given a CSV where the first column contains names, generates usernames and
prepends them as a new first column. One output row per username (aliases
produce additional rows).

Template tokens:
    {first}   : First name
    {last}    : Last name
    {f}       : First initial
    {l}       : Last initial
    {middle}  : Middle name (empty if absent)
    {m}       : Middle initial (empty if absent)

Usage:
    python3 generate-usernames-csv.py <Template> <Input CSV> [options]

Options:
    --aliases <file>   CSV: "Full Name,Alias1,Alias2,..." per line

Example:
    python3 generate-usernames-csv.py "{f}{last}@acme.com" employees.csv > out.csv
    python3 generate-usernames-csv.py "{f}{m}{last}" employees.csv --aliases aliases.csv
"""

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('template', nargs='?', default=None)
parser.add_argument('name_files', nargs='*')
parser.add_argument('--aliases', default=None)
parser.add_argument('-h', '--help', action='store_true')

args = parser.parse_args()

if args.help or not args.template or not args.name_files:
    print(usage)
    sys.exit()

alias_map = load_aliases(args.aliases)

lines = []
for name_file in args.name_files:
    with open(name_file, 'r') as _f:
        lines += [l.rstrip() for l in _f.readlines()]

for line in lines:
    name = clean_name(extract_name(line))
    usernames = convert_to_username(name, args.template, alias_map)
    for username in usernames:
        print("%s,%s" % (username, line))
