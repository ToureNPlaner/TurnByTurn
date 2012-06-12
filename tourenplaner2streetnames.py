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

streets = []
laststreet = None
for subway in jsoncontent['way']:
    for i in range(0, len(subway)-1,1):
        url = sys.argv[1]+"?srclat=%f&srclon=%f&destlat=%f&destlon=%f" % (float("0."+str(subway[i]['lt']))*100, float("0."+str(subway[i]['ln']))*10, float("0."+str(subway[i+1]['lt']))*100, float("0."+str(subway[i+1]['ln']))*10)
        #print(url)
        r = urllib.request.urlopen(url)
        response = json.loads(r.read().decode("utf-8"))
        #print(repr(response))
        if not 'errmsg' in response:
            streetname = sorted(response['streets'], key=lambda x: x['confidence'])
            #print(repr(streetname))
            streetsid = "".join(sorted([s['name'] for s in streetname if s['name']!= None]))
            if not streetsid == laststreet and len(streetsid) > 1:
                streets.append(streetname)
                laststreet = streetsid
        else:
            if response['errid'] != 1:
                print("Error! (Message: \"" + response['errmsg']+"\")")

print("Your way:")
for street in streets:
    #print (repr(street))
    print(" ||| ".join([streetname['name'] + " (confidence: "+str(streetname['confidence']) + ")" + " coordinates: ("+str(streetname['srclat'])+","+str(streetname['srclon'])+"),("+str(streetname['destlat'])+","+str(streetname['destlon'])+")" for streetname in street]))