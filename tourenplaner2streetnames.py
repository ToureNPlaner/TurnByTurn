#!/usr/bin/env python3

import sys
import json
import urllib.request

if len(sys.argv) not in  [3,4]:
    print(sys.argv[0] + " (url) (filename of json response) [normal|gpx]")
    exit(1)

if len(sys.argv) == 3:
    mode = 'normal'
elif sys.argv[3] in ['normal','gpx']:
    mode = sys.argv[3]
else:
    print("correct mode please")
    exit (1)
jsonfile = open(sys.argv[2])
jsoncontent = json.loads(jsonfile.read())
jsonfile.close()

streets = []
for subway in jsoncontent['way']:
    for i in range(0, len(subway)-1,1):
        #TODO: nicer int to float coordinates
        url = sys.argv[1]+"?srclat=%f&srclon=%f&destlat=%f&destlon=%f" % (float("0."+str(subway[i]['lt']))*100, float("0."+str(subway[i]['ln']))*10, float("0."+str(subway[i+1]['lt']))*100, float("0."+str(subway[i+1]['ln']))*10)
        r = urllib.request.urlopen(url)
        response = json.loads(r.read().decode("utf-8"))
        #print("response from the server: " + repr(response))
        if not 'errmsg' in response:
            # we take the street with smallest deviation from the given coordinates
            streetname = min(response['streets'], key=lambda x: x['srcdeviation'] + x['destdeviation'])
            #print("received streets: " + repr(response['streets']))
            #print("received street with best confidence: " + repr(streetname))

            # we want the street even if it has no name, because we don't know the reason it has no name
            if streetname ['name'] == None:
                name = "[unnamed]"
            else:
                name = streetname['name']

            # if the street is actually a part of the street in the last step we add this part to the street
            if  len(streets) > 0 and name == streets[-1]['name']:
                # add new coordinates and confidence to our street (some_list[-1] => last element in python)
                #only add the destination since the source SHOULD be the same as the destination of the last point in this street
                streets[-1]['coordinates'].append(
                    {'lat': streetname['destlat'],
                     'lon':streetname['destlon'],
                     'deviation': streetname['destdeviation']
                    })
            else:
                streets.append({
                        'name' : name,
                        'coordinates' : [
                            {'lat': streetname['srclat'],
                             'lon': streetname['srclon'],
                              'deviation': streetname['srcdeviation']},
                            {'lat': streetname['destlat'],
                             'lon': streetname['destlon'],
                              'deviation': streetname['destdeviation']}]
                    })
        else:
            #error messages would break xml
            if mode != 'gpx':
            #if response['errid'] != 1:
                # TODO: why?
                print("Error "+str(response['errid'])+"! (Message: \"" + response['errmsg']+"\")")

if mode == 'gpx':
    print("""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" creator="byHand" version="1.1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">""")
    for street in streets:
        print("    <rte>")
        for c in street['coordinates']:
            deviation=str(round(c['deviation'],1))
            #print('        <rtept lat="'+str(c['lat'])+'" lon="'+str(c['lon'])+'"><name>'+street['name']+'</name><desc>'+deviation+'</desc></rtept>')
            print('        <rtept lat="'+str(c['lat'])+'" lon="'+str(c['lon'])+'"><name>'+deviation+' ('
            +street['name']+')</name></rtept>')
        print("    </rte>")
    print("</gpx>")
else:
    print("Your way (<average deviation> <name>):")
    for street in streets:
        deviationsum = sum([d['deviation'] for d in street['coordinates']])
        deviation = round(deviationsum/len(street['coordinates']),1)
        #coordinates = [(c['lat'], c['lon']) for c in street['coordinates']]
        print(str(deviation), street['name'])
        #print(repr(coordinates))