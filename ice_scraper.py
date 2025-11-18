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
    
    import re
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

  