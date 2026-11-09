###   ###   #####     ###    ###   ####    ###   ####   #####  ####
 #   #   #  #        #      #   #  #   #  #   #  #   #  #      #   #
 #   #      ###       ###   #      ####   #####  ####   ###    ####
 #   #   #  #            #  #   #  #   #  #   #  #      #      #   #
###   ###   #####     ###    ###   #   #  #   #  #      #####  #   #

####################################################################                                                       

# Specify the path to your output folder here, or leave empty for the default.
output_dir = r''


### End of user-defined settings ##############################################


import os
import re


def _make_linkedin_sdui_helpers():
    """
    Build the LinkedIn server-driven-UI helpers.

    Python Scripter runs this script with exec(code, globals_, locals_), so
    names defined at the top level (imports, functions) land in locals_ and are
    NOT visible from inside functions. Everything the helpers need is therefore
    defined inside this factory and reached through closures.
    """
    import re
    import json
    import urllib

    degree_re = re.compile(r'^\W*(1st|2nd|3rd\+?)$', re.UNICODE)
    abbreviated_re = re.compile(r'^(.*\S)\s+(\w)\.?$', re.UNICODE)

    def expand_last_name(name, vanity):
        """
        LinkedIn abbreviates the last name of out-of-network people
        ("Angelina X."), but the profile vanity name often still contains it
        ("angelina-xu"). If the displayed name ends in a single initial, the
        vanity name starts with the displayed first name, and the next vanity
        token starts with that initial (and has no digits, i.e. is not a
        random ID suffix), use that token as the last name.
        Returns the (possibly expanded) name.
        """
        m = abbreviated_re.match(name)
        if not m or not vanity:
            return name
        first, initial = m.group(1), m.group(2).lower()

        try:
            vanity = urllib.unquote(vanity.encode('utf-8')).decode('utf-8')
        except (UnicodeError, AttributeError):
            pass
        tokens = [t for t in vanity.lower().split('-') if t]
        first_tokens = re.sub(r'[^\w\s]', ' ', first.lower(), flags=re.UNICODE).split()
        if not tokens or not first_tokens:
            return name

        n = len(first_tokens)
        joined_first = u''.join(first_tokens)
        if tokens[:n] == first_tokens and len(tokens) > n:
            candidate = tokens[n]                       # angelina-xu
        elif tokens[0].startswith(joined_first):
            candidate = tokens[0][len(joined_first):]   # angelinaxu
        else:
            return name

        if len(candidate) < 2 or not candidate.startswith(initial) or re.search(r'\d', candidate):
            return name
        return first + u' ' + candidate[0].upper() + candidate[1:]

    def response_body_text(raw):
        """Return a response body (Java byte[] / jython array) as a unicode string."""
        try:
            data = raw.tostring()
        except AttributeError:
            data = ''.join(chr(b & 0xff) for b in raw)
        return data.decode('utf-8', 'replace')

    def rsc_text(node):
        """Collect the visible text strings from a React Server Components element tree."""
        out = []
        if isinstance(node, basestring):
            if node.startswith('$$'):
                out.append(node[1:])    # escaped literal "$"
            elif not node.startswith('$'):
                out.append(node)        # skip references such as "$Le1" / "$undefined"
        elif isinstance(node, list):
            if len(node) == 4 and node[0] == '$' and isinstance(node[3], dict):
                # React element: ["$", type, key, props]
                props = node[3]
                if 'children' in props:
                    out += rsc_text(props['children'])
                if isinstance(props.get('textProps'), dict):
                    out += rsc_text(props['textProps'].get('children'))
            else:
                for child in node:
                    out += rsc_text(child)
        return out

    def clean(s):
        return re.sub(r'\s+', ' ', s, flags=re.UNICODE).strip()

    def csv_row(fields):
        return u','.join(u'"%s"' % f.replace(u'"', u'""') for f in fields)

    def parse_people(body):
        """
        Parse a LinkedIn "People" tab response from the server-driven UI
        (/flagship-web/..., application/octet-stream React Server Components stream).

        Each person card is split across rows of the stream:
          - a "name" row (viewName pages-people-profile-card-name) holding the
            profile URL and the display name, and
          - a parent card row that references the name row ("$L<id>") and holds
            the connection degree ("· 3rd") and the headline/title.
        Returns a list of (name, title, degree, profile_url) tuples.
        """
        raw_rows = {}
        for line in body.split('\n'):
            m = re.match(r'^([0-9a-f]+):(.*)$', line)
            if m:
                raw_rows[m.group(1)] = m.group(2)

        # Map each row id to the row that references it.
        parent_of = {}
        for row_id, raw in raw_rows.items():
            for ref in re.findall(r'"\$L([0-9a-f]+)"', raw):
                parent_of.setdefault(ref, row_id)

        def load(row_id):
            raw = raw_rows.get(row_id, '')
            if not raw[:1] in ('[', '{'):
                return None
            try:
                return json.loads(raw)
            except ValueError:
                return None

        people = []
        for row_id, raw in raw_rows.items():
            if '"pages-people-profile-card-name"' not in raw:
                continue

            name = clean(u''.join(rsc_text(load(row_id))))
            if not name:
                continue

            url = re.search(r'"url":"(/in/[^"]+)"', raw)
            profile_url = 'https://www.linkedin.com' + url.group(1) if url else ''

            vanity = re.search(r'"vanityName":"([^"]+)"', raw)
            if not vanity:
                vanity = re.search(r'/in/([^/"]+)', profile_url)
            if vanity:
                name = expand_last_name(name, vanity.group(1))

            degree, titles = '', []
            parent_id = parent_of.get(row_id)
            if parent_id is not None:
                for text in rsc_text(load(parent_id)):
                    text = clean(text)
                    if not text or text == name:
                        continue
                    d = degree_re.match(text)
                    if d:
                        degree = d.group(1)
                    else:
                        titles.append(text)

            people.append((int(row_id, 16), (name, u' | '.join(titles), degree, profile_url)))

        # Keep the on-page order (row ids are hex and increase down the page).
        people.sort()
        return [p[1] for p in people]

    return response_body_text, parse_people, csv_row


if not messageIsRequest:

    if output_dir == '':
        if 'USERPROFILE' in os.environ.keys():
            output_dir = os.environ['USERPROFILE'] + os.sep + 'Desktop'
        else:
            output_dir = os.environ['HOME']

    linkedin_output_file = output_dir + os.sep + "scraper-linkedin_unauth.csv"
    zoominfo_output_file = output_dir + os.sep + "scraper-zoominfo.csv"
    authed_LI_output_file = output_dir + os.sep + "scraper-linkedin_auth.csv"

    response = messageInfo.getResponse()
    analyzedResponse = helpers.analyzeResponse(response)
    headers = analyzedResponse.getHeaders()
    url = str(messageInfo.url)

    # Scrape people from LinkedIn's server-driven UI (People tab of a company page).
    # LinkedIn no longer uses the voyager GraphQL API here: the People tab is now
    # returned as a React Server Components stream from /flagship-web/... with
    # Content-Type application/octet-stream, so it is matched on the body instead.
    if "linkedin" in str(messageInfo.host).lower() and "/flagship-web/" in url:
        response_body_text, parse_people, csv_row = _make_linkedin_sdui_helpers()
        body = response_body_text(response[analyzedResponse.getBodyOffset():])
        if 'pages-people-profile-card-name' in body:
            with open(authed_LI_output_file, 'a') as _f:
                for person in parse_people(body):
                    output_data = csv_row(person).encode('utf-8')
                    _f.write(output_data + "\n")
                    print output_data

    contenttype_texthtml = re.compile('(Content-Type.*)(text|html)', re.IGNORECASE)
    contenttype_json = re.compile('(Content-Type.*)(json)', re.IGNORECASE)
        
    for header in headers:
    
        content_is_texthtml = contenttype_texthtml.match(header)
        if content_is_texthtml: break
        
        content_is_json = contenttype_json.match(header)
        if content_is_json: break
    
    
    # Parse responses if Content-Type is text or html
    if content_is_texthtml:

        response = messageInfo.getResponse()
        analyzedResponse = helpers.analyzeResponse(response)

        # Scrape LinkedIn contacts from Google
        if "google.com" in str(messageInfo.host).lower() and "linkedin" in str(messageInfo.url).lower():
        
            txt = helpers.bytesToString(response[analyzedResponse.getBodyOffset():]).encode('ascii','ignore')
        
            txt = re.sub('\&quot;?','"',txt)
            txt = re.sub('\&nbsp;?',' ',txt)
            txt = re.sub('\&amp;?',' ',txt)
            txt = re.sub('\&#39;?',"'",txt)

            pattern = re.compile(
                r'<h3[^>]*class="[^"]*"[^>]*id="[^"]*"[^>]*>(.*?)<\/h3>',
                re.DOTALL | re.IGNORECASE
            )
            x = [re.sub(r'\s+', ' ', match.strip()) for match in pattern.findall(txt)]

            f = open(linkedin_output_file, 'a')

            for hit in x:
                decoded = hit
                # print decoded
                split = decoded.split(' - ')
                name = split[0]
                title = ""
                company = ""
                if len(split) > 1: title = split[1]
                if len(split) > 2: company = split[2]

                output = '"' + name + '","' + title + '","' + company + '"'
                print output

                if type(output) == type(u''):
                    output = str(output.encode())

                f.write(output + "\n")

            f.close()


        # Scrape contacts from ZoomInfo
        elif "zoominfo.com" in str(messageInfo.host).lower() and 'pic' in str(messageInfo.url).lower():

            print "Zoom detected..."

            txt = helpers.bytesToString(response[analyzedResponse.getBodyOffset():]).encode('ascii','ignore')
        
            txt = txt.replace('\r','').replace('\n','')
            txt = re.sub('\&quot;?','"',txt)
            txt = re.sub('\&nbsp;?',' ',txt)
            txt = re.sub('\&amp;?',' ',txt)
            txt = re.sub('\&#39;?',"'",txt)

            txt = re.sub('\[\{', "\n", txt)
            txt = re.sub('\}\]', "\n", txt)
            txt = re.sub('\&q;', "", txt)

            f = open(zoominfo_output_file, 'a')

            debug_zoom=0

            for hit in re.findall('"columnName":"Contact Name".*', txt):
                if debug_zoom: print "-----"
                if debug_zoom: print hit
                output = '"'

                name = re.findall('fullName":[^:]+,"displayName', hit)
                if debug_zoom: print name
                if len(name) > 0: output += name[0].split('fullName":"')[1].split('","displayName')[0]

                output += '","'
                if debug_zoom: print output

                company = re.findall('companyName":[^:]+,"companyId', hit)
                if len(company) > 0: output += company[0].split('companyName":"')[1].split('","companyId')[0]

                output += '","'
                if debug_zoom: print output

                title = re.findall('"Job Title"[^}]+"text":"[^"]+', hit)
                if debug_zoom: print title
                if len(title) > 0: output += title[0].split('"')[-1]

                output += '","'
                if debug_zoom: print output

                country = re.findall('country":\{"name":"[^"]+","link', hit)
                if debug_zoom: print country
                if len(country) > 0: output += country[0].split('"name":"')[1].split('","link')[0]

                output += '","'
                if debug_zoom: print output

                state = re.findall(',"state":\{"name":[^:]+,"link', hit)
                if debug_zoom: print state
                if len(state) > 0: output += state[0].split('"name":"')[1].split('","link')[0]

                output += '","'
                if debug_zoom: print output

                city = re.findall(',"city":\{"name":[^:]+,"link', hit)
                if debug_zoom: print city
                if len(city) > 0: output += city[0].split('"name":"')[1].split('","link')[0]
                
                output += '"'
                print output

                if type(output) == type(u''):
                    output = str(output.encode())

                f.write(output + "\n")

            f.close()
    

    # Parse responses if Content-Type contains "json"
    elif content_is_json:

        response = messageInfo.getResponse()
        analyzedResponse = helpers.analyzeResponse(response)

        # Scrape people from LinkedIn
        if ( "linkedin" in str(messageInfo.host).lower() and "graphql" in str(messageInfo.url) and 
             ("ALUMNI" in str(messageInfo.url) or "ENTITY_SEARCH_HOME_HISTORY" in str(messageInfo.url)) ):

            import json
            
            response_body = helpers.bytesToString(response[analyzedResponse.getBodyOffset():]).encode('ascii','ignore')

            json_data = json.loads(response_body)
            
            # name = d['included']['title']['text']
            for item in json_data['included']:
                if type(item) == type(dict()):
                    if 'title' in item.keys():
                        if 'text' in item['title'].keys():
                            # name
                            name = item['title']['text']
                            
                            # title
                            title = item['primarySubtitle']['text']
                            
                            # location
                            location = item['secondarySubtitle']['text']
                           
                            # profile URL
                            profile_url = item['navigationUrl']

                            output_data = '"%s","%s","%s", "%s"' % (name, title, location, profile_url)

                            if type(output_data) == type(u''):
                                output_data = str(output_data.encode())


                            with open(authed_LI_output_file, 'a') as _f:
                                _f.write(output_data + "\n")
                                
                            print output_data

  