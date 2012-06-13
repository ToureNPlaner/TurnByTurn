#!/usr/bin/env python3

import sys
import json
import urllib.request

if len(sys.argv) != 3:
    print(sys.argv[0] + " (url) (filename of json response)")
    exit(1)

jsonfile = open(sys.argv[2])
jsoncontent = json.loads(jsonfile.read())
jsonfile.close()

#streets =
#[
    #{
        #'name' : 'asdstraße',
        #'confidence' : [1,3,5],
        #'coordinates' : [((48.1, 9.3), (48.2, 9.4)),((48.3, 9.4), (48.4, 9.5))]
    #},
    #{
        #...
    #}
#]

streets = []
for subway in jsoncontent['way']:
    for i in range(0, len(subway)-1,1):
        #TODO: nicer int to float coordinates
        url = sys.argv[1]+"?srclat=%f&srclon=%f&destlat=%f&destlon=%f" % (float("0."+str(subway[i]['lt']))*100, float("0."+str(subway[i]['ln']))*10, float("0."+str(subway[i+1]['lt']))*100, float("0."+str(subway[i+1]['ln']))*10)
        r = urllib.request.urlopen(url)
        response = json.loads(r.read().decode("utf-8"))
        #print("response from the server: " + repr(response))
        if not 'errmsg' in response:
            # we take the street with the smallest = best confidence
            streetname = min(response['streets'], key=lambda x: x['confidence'])
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
                streets[-1]['confidence'].append(streetname['confidence'])
                streets[-1]['coordinates'].append(((streetname['srclat'],streetname['srclon']),(streetname['destlat'],streetname['destlon'])))
            else:
                streets.append({
                        'name' : name,
                        'confidence' : [streetname['confidence']],
                        'coordinates' : [((streetname['srclat'],streetname['srclon']),(streetname['destlat'],streetname['destlon']))]
                    })
        else:
            #if you don't want to print errors that the was just not found
            #if response['errid'] != 1:
            print("Error "+str(response['errid'])+"! (Message: \"" + response['errmsg']+"\")")

print("Your way:")
for street in streets:
    confidence = str(round(sum(street['confidence'])/len(street['confidence']),1))
    coordinates = str(repr(street['coordinates']))
    print(confidence, street['name'])
    #print(coordinates)