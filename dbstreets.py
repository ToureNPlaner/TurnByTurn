#!/usr/bin/env python3
import psycopg2, bottle, json
from bottle import route, request, response
#from functools import lru_cache
from threading import Thread
from multiprocessing import cpu_count

NN_NUM = 7
THREAD_COUNT = cpu_count() - 1 # let one cpu core free for whatever
COORD_DIV=10.0**7
connections = [psycopg2.connect("dbname=gis user=osm") for i in range(0,THREAD_COUNT)]

def run_query(query, queryresult, conn):
    cur = conn.cursor()
    cur.execute("\nUNION ALL\n".join(query))
    queryresult.extend(cur.fetchall())
    cur.close()

#@lru_cache(maxsize=1024)
def db_streets(coordinatelist):

    # 0: identifier
    # 1: osm nodeid
    # 2: lat
    # 3: lon
    # 4: osm way_id
    # 5: way name
    # 6: way ref (alternative to name)
    # 7: osm node ids in way
    # 8: sequence number of node in way
    # 9: way tags
    # 10: meter distance of osm point to given point

    queries = ["(SELECT "+str(index)+", highway_nodes.id, ST_Y(highway_nodes.geom), ST_X(highway_nodes.geom), highway_ways.id, highway_ways.tags -> 'name', highway_ways.tags -> 'ref', highway_ways.nodes, highway_way_nodes.sequence_id, highway_ways.tags, ST_Distance('POINT("+str(c[1])+" "+str(c[0])+")',highway_nodes.geom::geography)     FROM highway_nodes JOIN highway_way_nodes ON highway_nodes.id = highway_way_nodes.node_id JOIN highway_ways ON highway_way_nodes.way_id = highway_ways.id ORDER BY highway_nodes.geom <#> ST_GeomFromEWKT('SRID=4326;POINT("+str(c[1])+" "+str(c[0])+")') LIMIT "+str(NN_NUM)+ ")" for index,c in enumerate(coordinatelist)]

    qryres = list()
    if len(queries) > 50:
        chunksize = (int) (len(queries) / THREAD_COUNT)
        querylist = [queries[x:x+chunksize] for x in range(0, len(queries), chunksize)]
        
        threads = [Thread(target=run_query, args=(qry, qryres, connections[i-1])) for i,qry in enumerate(querylist)]
        [t.start() for t in threads]
        [t.join() for t in threads]
    else:
        run_query(queries, qryres, connections[0])
    
    qryres = sorted(qryres, key = lambda x: x[0])
    #print("qry result\n:" + str(qryres))

    noway=[]
    waystreets = []
    for index in range(0,len(coordinatelist) - 1):
        # qryres is sorted after the index of the input coordinatelist and we always get NN_NUM results from the database
        currentresultsrc = qryres[index * NN_NUM : (index + 1) * NN_NUM]
        currentresultdest = qryres[(index + 1) * NN_NUM : (index + 2) * NN_NUM]
        
        # first, filter each two node pairs and take those with an edge between them
        # then, sort after the deviation from the given coordinates
        streetparts = [(src,dest) for src in currentresultsrc for dest in currentresultdest if src[1] != dest[1] and src[4] == dest[4]]
    
        if not streetparts:
            noway.append({
                'srclat' : coordinatelist[index][0],
                'srclon' : coordinatelist[index][1],
                'destlat' : coordinatelist[index+1][0],
                'destlon' : coordinatelist[index+1][1]
            })

            # for fluent navigation we still need that coordinates, just add them to the last found street
            if len(waystreets) > 0:
                waystreets.append([
                    {    "customindex" : index,
                        "wayid" : waystreets[-1][0]['wayid'],
                        "name" : waystreets[-1][0]['name'],
                        #"tags" : waystreets[-1][0]['tags'],
                        #"nodes" : waystreets[-1][0]['nodes'],
                        "sourcenode" : -1,
                        "destnode" : -1,
                        "srcdeviation" : -1,
                        "destdeviation" : -1,
                        'srclat' : coordinatelist[index][0],
                        'srclon' : coordinatelist[index][1],
                        'destlat' : coordinatelist[index+1][0],
                        'destlon' : coordinatelist[index+1][1]
                    }])
            
        else :
            waystreets.append([
                {    "customindex" : index,
                    "wayid" : found_way[0][4],
                    "name" : found_way[0][5] if found_way[0][5] else found_way[0][6] if found_way[0][6] else "??",
                    #"tags" : found_way[0][9],
                    #"nodes" : found_way[0][7],
                    "sourcenode" : found_way[0][1],
                    "destnode" : found_way[1][1],
                    "srcdeviation" : found_way[0][10],
                    "destdeviation" : found_way[1][10],
                    "srclat" : found_way[0][2],
                    "srclon" : found_way[0][3],
                    "destlat" : found_way[1][2],
                    "destlon" : found_way[1][3]
                } for found_way in streetparts])
    return waystreets,noway

@route('/')
def hello():
    return "Usage: http://" + request.remote_route[-1] + "/streetname/?srclat=X&srclon=X&destlat=X&destlon=X"

@route('/streetname/',method='POST')
def findways():

    #[print("key: " + str(key) + "\ndata: " + repr(request.forms[key]) + "\n\n") for key in request.forms.keys()]
    content = json.loads(request.forms.nodes)
    print("/streetname/ called with \"nodes\": " + str(content)[:300])

    waystreets = []
    noway = []

    for subway in content:
        coordinatelist = tuple( [ (c[0]/COORD_DIV, c[1]/COORD_DIV) for c in subway ] )
        print ("coordinatelist: " + repr(coordinatelist)[:300])
        ws, nw = db_streets(coordinatelist)
        waystreets.append(ws)
        noway.append(nw)

    # waystreets = list of subways
    # subway = list of (list of possible edges for each coordinate pair)
    wayedges = []
    for subway in waystreets:
        for edges in subway:
            sortededges = sorted(edges, key=lambda x: x['srcdeviation'] + x['destdeviation'])

            #TODO: heuristics which edge to choose
            edge = sortededges[0]

            if len(wayedges) > 0 and edge['srcdeviation'] + edge['destdeviation'] > 10:

                # try to use a continuation of the last edge, but only if the coordinates are not close enough
                #lastname =     wayedges[-1]['name']
                #filtered = list(filter(lambda x: x['name'] == lastname, foundedges))
                #if filtered:
                #    edge = filtered[0]

                # just pretend there is a node that is part of the last edge
                # TODO: maybe not
                wayedges[-1]['coordinates'].append({
                    "deviation" : -1,
                    "lt" : coordinatelist[edge['customindex']+1][0],
                    "ln" : coordinatelist[edge['customindex']+1][1]
                })
                continue

            # if the edge is actually a part of the edge in the last step we add this part to the edge
            if  len(wayedges) > 0 and edge['name'] == wayedges[-1]['name']:
                # add new coordinates and confidence to our edge (some_list[-1] => last element in python)
                #only add the destination since the source SHOULD be the same as the destination of the last point in this edge
                wayedges[-1]['coordinates'].append(
                    {'lt': edge['destlat'],
                    'ln':edge['destlon'],
                    'deviation': edge['destdeviation']
                    })
            else:
                wayedges.append({
                        'name' : edge['name'],
                        'coordinates' : [
                            {'lt': wayedges[-1]['coordinates'][-1]['lt'], #stitch the beginning of the edge we add to the end of the last edge so there will be no little gaps in the way
                                'ln':  wayedges[-1]['coordinates'][-1]['ln'],
                                'deviation': wayedges[-1]['coordinates'][-1]['deviation'] + edge['srcdeviation']} if len(wayedges) > 0
                                else {'lt': edge['srclat'], 'ln': edge['srclon'], 'deviation': edge['srcdeviation']},
                            {'lt': edge['destlat'], 'ln': edge['destlon'], 'deviation': edge['destdeviation']}
                        ]
                    })
    result = {'streets' : wayedges, 'failed' : noway}
    print("response: " + repr(result)[:300])
    response.content_type = 'application/json; charset=utf8'
    return(json.dumps(ensure_ascii=False,  obj = result))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
[conn.close() for conn in connections]
