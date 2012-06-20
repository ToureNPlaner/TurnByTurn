#!/usr/bin/env python3
import psycopg2, bottle, json
from bottle import route, request
from functools import lru_cache

conn = psycopg2.connect("dbname=gis user=osm")
RADIUS = 15

@lru_cache(maxsize=4096)
def db_streets(srclat,srclon,destlat,destlon):
    cur = conn.cursor() #multithreaded on one cursor probably doesn't work, so each thread doing a database connection gets a new one
    
    cur.execute("""SELECT node_id,ST_Y(geog::geometry),ST_X(geog::geometry),way_id,way_tags -> 'name',way_tags -> 'ref',way_nodes,way_tags,sequence_id
        FROM highway_nodes
        WHERE ST_DWithin(geog,'POINT({:-f} {:-f})',{:-f});""".format(srclon,srclat,RADIUS))
    src = cur.fetchall()
    cur.execute("""SELECT node_id,ST_Y(geog::geometry),ST_X(geog::geometry),way_id,way_tags -> 'name',way_tags -> 'ref'
        FROM highway_nodes
        WHERE ST_DWithin(geog,'POINT({:-f} {:-f})',{:-f});""".format(destlon,destlat,RADIUS))
    dest = cur.fetchall()

    #print("src: " + repr(src))
    #print("dest: " + repr(dest))

    # create src-dest pairs and sort after added deviation from the given coordinates
    candidates = sorted([(srcnode,destnode) for srcnode in src for destnode in dest if srcnode[3] == destnode[3]],key=lambda c: abs(srclat-c[0][1]) + abs(srclon-c[0][2])*5 + abs(destlat-c[1][1]) + abs(destlon-c[1][2])*5)
    if len(candidates) > 0:
        ret = { 'found_way' : [] }
        for found_way in candidates:
            ret['found_way'].append ({
                "wayid" : found_way[0][3],
                "name" : found_way[0][4] if found_way[0][4] != None else found_way[0][5],
                "tags" : found_way[0][6],
                "nodes" : found_way[0][7],
                "sourcenode" : found_way[0][0],
                "destnode" : found_way[1][0],
                "deviance" : abs(srclat-found_way[0][1]) + abs(srclon-found_way[0][2])*5 + abs(destlat-found_way[1][1]) + abs(destlon-found_way[1][2])*5,
                "srclat" : found_way[0][1],
                "srclon" : found_way[0][2],
                "destlat" : found_way[1][1],
                "destlon" : found_way[1][2]
            })
            #print("deviance: " + str(abs(srclat-found_way[0][1]) + abs(srclon-found_way[0][2])*5 + abs(destlat-found_way[1][1]) + abs(destlon-found_way[1][2])*5))
        return ret
    else:
        return {'errid': 1, 'src' : len(src), 'dest' : len(dest)}

@route('/')
def hello():
    return "Usage: http://" + request.remote_route[-1] + "/streetname/?srclat=X&srclon=X&destlat=X&destlon=X"

@route('/streetname/')
def findways():
    srclat = float(request.params.get("srclat"))
    srclon = float(request.params.get("srclon"))
    destlat = float(request.params.get("destlat"))
    destlon = float(request.params.get("destlon"))

    results = db_streets(srclat,srclon,destlat,destlon)

    if 'errid' in results:
        return(
            {'errmsg' : 'no street found between coordinates (%f,%f) and (%f,%f), looked at nodes: (src: #%d, dest: #%d)' % (srclat,srclon,destlat,destlon,results['src'],results['dest']),
            'errid' : results['errid']})
    #print("Street(s) found: " + repr(results))
    #print(repr(results))
    #streets = {} #[{ 'wayid' : ret['wayid'], 'name' : ret['name'], 'tags' : ret['tags'], 'nodes' : ret['nodes'], 'sourcenode' : ret['sourcenode'], 'destnode'} for result in results]
    return(json.dumps(ensure_ascii=False,  obj = {'streets' : results['found_way']}))# if result[0] != None]}))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
conn.close()