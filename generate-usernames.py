from os.path import exists
import csv
import re
import sys


def extract_names(filename):
    """
    Returns the list of names found in the first column of a given CSV file.
    """

    names = []

    if exists(filename):
        with open(filename, newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in csvreader:
                names.append(row[0])

    names = [name.strip() for name in names]

    return names

def clean_and_sort_names(names):
    """Remove strings such as titles that are not part of the name."""

    titles_suffixes = r'\([^)]+\)?|, ?[a-z]?[A-Z.]+|^(Dr|Mrs?|Ms)\.? ?'
    names = [re.sub(titles_suffixes,'',name) for name in names]

    non_names = r'[^A-Za-z ]|LinkedIn Member'
    names = [re.sub(non_names,'',name) for name in names]

    multiple_spaces = r' +'
    names = [re.sub(multiple_spaces,' ',name).strip() for name in names]

    names = [name.lower() for name in names]

    while '' in names: names.remove('')
                    
    names = list(set(names))
    names.sort()

    return names
    
def convert_to_usernames(names, fstring):
    usernames = []
    
    for name in names:
        #print("Name: '" + name + "'")
        first = name.split(' ')[0]
        f = first[0]
        if ' ' in name:
            last = name.split(' ')[1]
            l = last[0]
        else:
            last, l = None, None
            continue
            
        template_values = { 'first': first,
                            'f': f,
                            'last': last,
                            'l': l
                          }
            
        usernames.append(fstring.format(**template_values))

    return usernames


usage = """
generate-usernames.py
=====================

Generates a list of usernames or email addresses from a list of first and last
names.

The input file may be either a text file with one name on each line or a CSV
file that contains the names in the first column.

The following fields may be used in the username template:
    - {first}   : First name
    - {last}    : Last name
    - {f}       : First initial
    - {l}       : Last initial

Output is printed to stdout, so just redirect to a file to save the output.

Usage: python3 generate-usernames.py <Template> <First and Last Name File(s)>

Example: 

    python3 generate-usernames.py "{f}{last}@acme.com" employees.csv > output.txt
"""

if len(sys.argv) < 3 or '-h' in sys.argv or '--help' in sys.argv:
    print(usage)
    exit()

name_files = sys.argv[2:]
fstring = sys.argv[1]

names = []

for filename in name_files:
    names += extract_names(filename)

names = clean_and_sort_names(names)

usernames = list(set(convert_to_usernames(names, fstring)))
usernames.sort()

print("\n".join(usernames))
    