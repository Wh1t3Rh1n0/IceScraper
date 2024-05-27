from os.path import exists
import csv
import re
import sys


def extract_name(line):
    """
    Returns the name found in the first column of a given CSV file.
    """
    name = line.split(',')[0].replace('"','')

    return name


def clean_name(name):
    """Remove strings such as titles that are not part of the name."""

    titles_suffixes = r'\([^)]+\)?|, ?[a-z]?[A-Z.]+|^(Dr|Mrs?|Ms)\.? ?'
    name = re.sub(titles_suffixes, '', name)

    non_names = r'[^A-Za-z ]|LinkedIn Member'
    name = re.sub(non_names, '', name)

    multiple_spaces = r' +'
    name = re.sub(multiple_spaces, ' ', name).strip()

    name = name.lower()

    return name
    
    
def convert_to_username(name, fstring):

    if name == '':
        return ''

    first = name.split(' ')[0]
    f = first[0]
    if ' ' in name:
        last = name.split(' ')[1]
        l = last[0]
    else:
        last, l = '', ''
        
    template_values = { 'first': first,
                        'f': f,
                        'last': last,
                        'l': l
                      }
        
    return (fstring.format(**template_values))



usage = """
generate-usernames-csv.py
=========================

Given a CSV input file, where the first column contains individuals' first and
last names, this script generates usernames/email addresses from the names and
adds them to the existing CSV file as a new first column.

The input file can also be regular a text file with one name on each line,
since that is technically the same as a single column CSV file. ;)

The following fields may be used in the username template:
    - {first}   : First name
    - {last}    : Last name
    - {f}       : First initial
    - {l}       : Last initial

Output is printed to stdout, so just redirect to a file to save the output.

Usage: python3 generate-usernames-csv.py <Template> <Input CSV File>

Example: 

    python3 generate-usernames.py "{f}{last}@acme.com" employees.csv > output.csv
"""

if len(sys.argv) < 3 or '-h' in sys.argv or '--help' in sys.argv:
    print(usage)
    exit()


name_files = sys.argv[2:]
fstring = sys.argv[1]

lines = []

for name_file in name_files:
    with open(name_file, 'r') as _f:
        lines += [l.rstrip() for l in _f.readlines()] 
    
for line in lines:
    name = extract_name(line)
    username = convert_to_username(clean_name(name), fstring)
    print("%s,%s" % (username, line))