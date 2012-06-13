#!/usr/bin/env python3
import psycopg2, bottle, json, functools
from bottle import route, install, template, request

conn = psycopg2.connect("dbname=gis user=osm")
LIMIT = 4

@functools.lru_cache(maxsize=4096)
def db_streets(srclat,srclon,destlat,destlon):
    cur = conn.cursor() #multithreaded on one cursor probably doesn't work, so each thread doing a database connection gets a new one
    
    # we don't know if our coordinates are nearest to the correct osm node. Better search for #LIMIT nearest nodes for src and dest each and search for ways between all combinations
    # fetching #LIMIT at a time is still pretty cheap thanks to the awesomeness of postgis and an index on geom
    cur.execute("""SELECT DISTINCT src.id,dest.id,ST_Y(src.geom),ST_X(src.geom),ST_Y(dest.geom),ST_X(dest.geom) FROM
        (SELECT nodes.id,nodes.geom FROM nodes JOIN way_nodes ON nodes.id = way_nodes.node_id JOIN ways ON way_nodes.way_id = ways.id WHERE ways.tags::hstore ? 'highway' ORDER BY geom <-> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}) AS src,
        (SELECT nodes.id,nodes.geom FROM nodes JOIN way_nodes ON nodes.id = way_nodes.node_id JOIN ways ON way_nodes.way_id = ways.id WHERE ways.tags::hstore ? 'highway' ORDER BY geom <-> ST_GeomFromEWKT('SRID=4326;POINT({:-f} {:-f})') LIMIT {:d}) AS dest
        WHERE (src.id != dest.id);""".format(srclon,srclat,LIMIT,destlon,destlat,LIMIT))
    candidatepairs = cur.fetchall()
    #print("candidatepairs " + repr(candidatepairs))

    # sort after deviation from the given coordinates
    for index,candidatepair in enumerate(sorted(candidatepairs,key=lambda c: abs(srclat-c[2]) + abs(srclon-c[3]) + abs(destlat-c[4]) + abs(destlon-c[5]))):
        # a = b is already filtered out by first query
        cur.execute("""SELECT DISTINCT a.id,a.tags,a.nodes,a.tags::hstore -> 'name',a.node_id AS srcnode, b.node_id AS destnode
            FROM (ways JOIN way_nodes ON ways.id = way_nodes.way_id) AS a, way_nodes AS b
            WHERE %s = a.node_id AND %s = b.node_id AND a.way_id = b.way_id""" % (candidatepair[0], candidatepair[1]))
        results = cur.fetchall()
        ret = []
        if results:
            #print("Candidate chosen: " + repr(candidatepair))
            cur.close()
            for idx,result in enumerate(results):
                ret.append ({
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

    if not results:
        return({'errmsg' : 'no street found between coordinates (%f,%f) and (%f,%f)' % (srclat,srclon,destlat,destlon), 'errid' : 1})
    #print("Street(s) found: " + repr(results))
    #print(repr(results))
    #streets = {} #[{ 'wayid' : ret['wayid'], 'name' : ret['name'], 'tags' : ret['tags'], 'nodes' : ret['nodes'], 'sourcenode' : ret['sourcenode'], 'destnode'} for result in results]
    return(json.dumps(ensure_ascii=False,  obj = {'streets' : results}))# if result[0] != None]}))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
conn.close()

