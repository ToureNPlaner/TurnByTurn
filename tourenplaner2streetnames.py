#!/usr/bin/env python3

import sys
import json
import httplib2
import time
import math
import os

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

#http://www.johndcook.com/python_longitude_latitude.html
def distance_on_unit_sphere(lat1, long1, lat2, long2):
    degrees_to_radians = math.pi/180.0
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) +
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )
    return arc * 6371000 # radius in meter

jsoncontent = json.load(open(sys.argv[2]))['way']
tosend = [ [ (c['lt'], c['ln']) for c in subway ] for subway in jsoncontent ]
url = sys.argv[1]

start = time.time()
http = httplib2.Http(disable_ssl_certificate_validation=True)
headers = {'Content-Type':'application/json', "Accept":"application/json"}
respstat, resp = http.request(uri=url, method='POST', body=json.dumps(tosend), headers=headers)
end = time.time()

response = json.loads(str(resp, "UTF-8"))
if 'error' in response.keys():
    print("\tfilename: " + sys.argv[2] + "\n\terror: " + response['error'])
    exit(0)

waystreets = response['streets']
noway = response['failed']

benchmarkfile = 'benchmark.csv'
if mode == 'benchmark':
    print(str(end - start))
    if os.path.isfile(benchmarkfile):
        f = open(benchmarkfile, 'a')
    else:
        f = open(benchmarkfile, 'w')
        f.write("route length;number of coordinates;time\n")
    dist = 0
    coordinates = 0
    for street in waystreets:
        for index,c in enumerate(street['coordinates']):
            if index == len(street['coordinates']) - 2:
                break
            coordinates += 1
            dist += distance_on_unit_sphere(c['lt'],c['ln'], street['coordinates'][index + 1]['lt'], street['coordinates'][index + 1]['ln'])
    f.write(str(round(dist)) + ";" + str(coordinates) + ";" + str(end-start) + "\n")
    f.close()

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