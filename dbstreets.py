#!/usr/bin/env python3
import psycopg2, bottle, json, functools
from bottle import route, install, template, request

conn = psycopg2.connect("dbname=gis user=osm")
RADIUS = 35

@functools.lru_cache(maxsize=4096)
def db_streets(srclat,srclon,destlat,destlon):
    cur = conn.cursor() #multithreaded on one cursor probably doesn't work, so each thread doing a database connection gets a new one
    
    # we don't know if our coordinates are nearest to the correct osm node. Better search for #LIMIT nearest nodes for src and dest each and search for ways between all combinations
    # fetching #LIMIT at a time is still pretty cheap thanks to the awesomeness of postgis and an index on geom
    #cur.execute("""SELECT DISTINCT src.id,dest.id,ST_Y(src.geom),ST_X(src.geom),ST_Y(dest.geom),ST_X(dest.geom) FROM
        #(SELECT nodes.id,nodes.geom FROM nodes JOIN way_nodes ON nodes.id = way_nodes.node_id JOIN ways ON way_nodes.way_id = ways.id WHERE ways.tags::hstore ? 'highway' ORDER BY geom <-> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}) AS src,
        #(SELECT nodes.id,nodes.geom FROM nodes JOIN way_nodes ON nodes.id = way_nodes.node_id JOIN ways ON way_nodes.way_id = ways.id WHERE ways.tags::hstore ? 'highway' ORDER BY geom <-> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}) AS dest
        #WHERE (src.id != dest.id);""".format(srclon,srclat,LIMIT,destlon,destlat,LIMIT))
    #candidatepairs = cur.fetchall()
    #print("candidatepairs " + repr(candidatepairs))

#src.lat, src.lon,dest.lat,dest.lon 
    cur.execute("""SELECT DISTINCT src.node_id,dest.node_id,ST_Y(src.geog::geometry),ST_X(src.geog::geometry),ST_Y(dest.geog::geometry),ST_X(dest.geog::geometry)
    FROM
    (SELECT node_id,geog FROM highway_nodes WHERE ST_DWithin(geog,'POINT({:-f} {:-f})',{:-f})) AS src,
    (SELECT node_id,geog FROM highway_nodes WHERE ST_DWithin(geog,'POINT({:-f} {:-f})',{:-f})) AS dest
    WHERE (src.node_id != dest.node_id);""".format(srclon,srclat,RADIUS,destlon,destlat,RADIUS))
    candidatepairs = cur.fetchall()
    ret = { 'found_way' : [] }

    # sort after deviation from the given coordinates
    for index,candidatepair in enumerate(sorted(candidatepairs,key=lambda c: abs(srclat-c[2]) + abs(srclon-c[3]) + abs(destlat-c[4]) + abs(destlon-c[5]))):
        # a = b is already filtered out by first query
        #cur.execute("""SELECT DISTINCT a.id,a.tags,a.nodes,a.tags::hstore -> 'name',a.node_id AS srcnode, b.node_id AS destnode
            #FROM (ways JOIN way_nodes ON ways.id = way_nodes.way_id) AS a, way_nodes AS b
            #WHERE %s = a.node_id AND %s = b.node_id AND a.way_id = b.way_id""" % (candidatepair[0], candidatepair[1]))
        cur.execute("""SELECT DISTINCT a.way_id,a.way_tags,a.way_nodes,a.way_tags::hstore -> 'name',a.node_id AS srcnode, b.node_id AS destnode
            FROM (SELECT b.node_id, b.way_id from highway_nodes AS b WHERE %s = b.node_id) AS b JOIN highway_nodes AS a ON b.way_id=a.way_id
            WHERE %s = a.node_id""" % (candidatepair[0], candidatepair[1]))
        results = cur.fetchall()
        if results:
            #print("Candidate chosen: " + repr(candidatepair))
            cur.close()
            for idx,result in enumerate(results):
                ret['found_way'].append ({
                    "wayid" : result[0],
                    "name" : result[3],
                    "tags" : result[1],
                    "nodes" : result[2],
                    "sourcenode" : result[4],
                    "destnode" : result[5],
                    "confidence" : index + idx,
                    "srclat" : candidatepair[2],
                    "srclon" : candidatepair[3],
                    "destlat" : candidatepair[4],
                    "destlon" : candidatepair[5]
                })
            return ret;
    cur.close()
    return {'error' : len(candidatepairs)}

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

    if 'error' in results:
        return({'errmsg' : 'no street found between coordinates (%f,%f) and (%f,%f), tried %d pairs' % (srclat,srclon,destlat,destlon,results['error']), 'errid' : 1})
    #print("Street(s) found: " + repr(results))
    #print(repr(results))
    #streets = {} #[{ 'wayid' : ret['wayid'], 'name' : ret['name'], 'tags' : ret['tags'], 'nodes' : ret['nodes'], 'sourcenode' : ret['sourcenode'], 'destnode'} for result in results]
    return(json.dumps(ensure_ascii=False,  obj = {'streets' : results['found_way']}))# if result[0] != None]}))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
conn.close()

