#!/usr/bin/env python3

import sys
import json
import httplib2
import time

if len(sys.argv) not in  [3,4]:
    print(sys.argv[0] + " (url) (filename of json response) [normal|gpx|json|benchmark (time in seconds)]")
    exit(1)

if len(sys.argv) == 3:
    mode = 'normal'
elif sys.argv[3] in ['normal','gpx','json','benchmark']:
    mode = sys.argv[3]
else:
    print("correct mode please")
    exit (1)

jsoncontent = json.load(open(sys.argv[2]))['way']
tosend = [ [ (c['lt'], c['ln']) for c in subway ] for subway in jsoncontent ]
url = sys.argv[1]

start = time.time()
http = httplib2.Http(disable_ssl_certificate_validation=True)
headers = {'Content-Type':'application/json', "Accept":"application/json"}
respstat, resp = http.request(uri=url, method='POST', body=json.dumps(tosend), headers=headers)
end = time.time()

response = json.loads(str(resp, "UTF-8"))
waystreets = response['streets']
noway = response['failed']

if mode == 'benchmark':
    print(str(end - start))
elif mode == 'gpx':
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
elif mode == 'normal':
    print("Your way (<average deviation> <name>):")
    for streetpart in waystreets:
        deviationsum = sum([d['deviation'] for d in streetpart['coordinates']])
        deviation = round(deviationsum/len(streetpart['coordinates']),1)
        #coordinates = [(c['lat'], c['lon']) for c in street['coordinates']]
        print(str(deviation), streetpart['name'])
        #print(repr(coordinates))
elif mode == 'json':
    print(json.dumps(ensure_ascii=False,  obj = response))