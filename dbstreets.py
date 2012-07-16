#!/usr/bin/env python3
import psycopg2, bottle, json
from bottle import route, request
from functools import lru_cache

conn = psycopg2.connect("dbname=bw user=osm")
NN_NUM = 10

@lru_cache(maxsize=1024)
def db_streets(srclat,srclon,destlat,destlon):
    cur = conn.cursor() #multithreaded on one cursor probably doesn't work, so each thread doing a database connection gets a new one
    
    cur.execute("""SELECT node_id,ST_Y(geog::geometry),ST_X(geog::geometry),way_id,way_tags -> 'name',way_tags -> 'ref',way_nodes,way_tags,sequence_id,ST_Distance('POINT({:-f} {:-f})',geog)
        FROM highway_nodes
        ORDER BY geom <#> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}""".format(srclon,srclat,srclon,srclat,NN_NUM))
    src = cur.fetchall()
    cur.execute("""SELECT node_id,ST_Y(geog::geometry),ST_X(geog::geometry),way_id,way_tags -> 'name',way_tags -> 'ref',ST_Distance('POINT({:-f} {:-f})',geog)
        FROM highway_nodes
        ORDER BY geom <#> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}""".format(destlon,destlat,destlon,destlat,NN_NUM))
    dest = cur.fetchall()

    #print("src: " + repr(src))
    #print("dest: " + repr(dest))

    # create src-dest pairs and sort after added deviation from the given coordinates
    candidates = sorted([(srcnode,destnode) for srcnode in src for destnode in dest if srcnode[0] != destnode[0] and srcnode[3] == destnode[3]],key=lambda c: c[0][9] + c[1][6])
    if len(candidates) > 0:
        ret = { 'found_way' : [] }
        for found_way in candidates:
            ret['found_way'].append ({
                "wayid" : found_way[0][3],
                "name" : found_way[0][4] if found_way[0][4] else found_way[0][5],
                "tags" : found_way[0][6],
                "nodes" : found_way[0][7],
                "sourcenode" : found_way[0][0],
                "destnode" : found_way[1][0],
                "srcdeviation" : found_way[0][9],
                "destdeviation" : found_way[1][6],
                "srclat" : found_way[0][1],
                "srclon" : found_way[0][2],
                "destlat" : found_way[1][1],
                "destlon" : found_way[1][2]
            })
            #print("deviation: " + str(abs(srclat-found_way[0][1]) + abs(srclon-found_way[0][2])*5 + abs(destlat-found_way[1][1]) + abs(destlon-found_way[1][2])*5))
        return ret
    else:
        return {'errid': 1, 'srcnum' : len(src), 'destnum' : len(dest)}

@route('/')
def hello():
    return "Usage: http://" + request.remote_route[-1] + "/streetname/?srclat=X&srclon=X&destlat=X&destlon=X"

@route('/streetname/',method='POST')
def findways():
    #print(repr(request.forms.tourenplanerjson))
    content = json.loads(request.forms.tourenplanerjson)

    noway=[]
    waystreets = []
    for subway in content['way']:
        for i in range(0, len(subway)-1,1):
            #TODO: nicer int to float coordinates
            (srclat,srclon,destlat,destlon) = (float("0."+str(subway[i]['lt']))*100, float("0."+str(subway[i]['ln']))*10, float("0."+str(subway[i+1]['lt']))*100, float("0."+str(subway[i+1]['ln']))*10)

            foundstreets = db_streets(srclat,srclon,destlat,destlon)
            if 'errid' in foundstreets:
                noway.append({
                    'srclat' : srclat,
                    'srclon' : srclon,
                    'srcnum' : foundstreets['srcnum'],
                    'destlat' : destlat,
                    'destlon' : destlon,
                    'destnum' : foundstreets['destnum']})
                continue
                #if 'errmsg' in response:
                    #if response['errid'] == 1:
                        #if mode == 'gpx':
                            #noway.append(((response['srclat'],response['srclon']),(response['destlat'],response['destlon'])))
                        #else:
                            #print("Error "+str(response['errid'])+"! (Message: \"" + response['errmsg']+"\")")


            foundstreets = sorted(foundstreets['found_way'], key=lambda x: x['srcdeviation'] + x['destdeviation'])
            street = foundstreets[0]
            name = street['name'] if street['name'] != None else "[?]"
            # if the street is actually a part of the street in the last step we add this part to the street
            if  len(waystreets) > 0 and name == waystreets[-1]['name']:
                # add new coordinates and confidence to our street (some_list[-1] => last element in python)
                #only add the destination since the source SHOULD be the same as the destination of the last point in this street
                waystreets[-1]['coordinates'].append(
                    {'lat': street['destlat'],
                    'lon':street['destlon'],
                    'deviation': street['destdeviation']
                    })
            else:
                waystreets.append({
                        'name' : name,
                        'coordinates' : [
                            {'lat': street['srclat'],
                            'lon': street['srclon'],
                            'deviation': street['srcdeviation']},
                            {'lat': street['destlat'],
                            'lon': street['destlon'],
                            'deviation': street['destdeviation']}]
                    })

    return(json.dumps(ensure_ascii=False,  obj = {'streets' : waystreets, 'failed' : noway}))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
conn.close()