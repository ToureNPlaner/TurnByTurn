#!/usr/bin/env python3

import sys
import json
import urllib.request
import urllib.parse

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
#jsoncontent = json.loads(jsonfile.read())
jsoncontent = json.loads(jsonfile.read())['way']
jsonfile.close()

tosend = [ [ (c['lt'], c['ln']) for c in subway ] for subway in jsoncontent ]

url = sys.argv[1]

r = urllib.request.urlopen(url, data = urllib.parse.urlencode({"nodes": json.dumps(tosend)}).encode())

response = json.loads(r.read().decode("utf-8"))
#print(json.dumps(response,indent = 2))

waystreets = response['streets']
noway = response['failed']

if mode == 'gpx':
    print("""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" creator="byHand" version="1.1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">""")
    for street in waystreets:
        print("    <rte>")
        for c in street['coordinates']:
            deviation=str(round(c['deviation'],1))
            #print('        <rtept lat="'+str(c['lat'])+'" lon="'+str(c['lon'])+'"><name>'+street['name']+'</name><desc>'+deviation+'</desc></rtept>')
            print('        <rtept lat="'+str(c['lt'])+'" lon="'+str(c['ln'])+'"><name>'+deviation+' ('
            +street['name']+')</name></rtept>')
        print("    </rte>")
    for now in noway:
        for index,nw in enumerate(now):
            print("    <wpt lat=\""+str(nw['srclat'])+"\" lon=\""+str(nw['srclon'])+"\"><name>"+str(index)+"</name></wpt>")
            print("    <wpt lat=\""+str(nw['destlat'])+"\" lon=\""+str(nw['destlon'])+"\"><name>"+str(index)+"</name></wpt>")
    print("</gpx>")
else:
    print("Your way (<average deviation> <name>):")
    for streetpart in waystreets:
        deviationsum = sum([d['deviation'] for d in streetpart['coordinates']])
        deviation = round(deviationsum/len(streetpart['coordinates']),1)
        #coordinates = [(c['lat'], c['lon']) for c in street['coordinates']]
        print(str(deviation), streetpart['name'])
        #print(repr(coordinates))