#!/usr/bin/env python3
import psycopg2, bottle, json
from bottle import route, request, response
from functools import lru_cache

conn = psycopg2.connect("dbname=gis user=osm")
NN_NUM = 7
COORD_DIV=10.0**7

#@lru_cache(maxsize=1024)
def db_streets(cur,coordinatelist):

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

    QRY = "\nUNION ALL\n".join(["(SELECT "+str(index)+", node_id,ST_Y(geom),ST_X(geom),way_id,way_tags -> 'name',way_tags -> 'ref',way_nodes,sequence_id,way_tags,ST_Distance('POINT("+str(c[1])+" "+str(c[0])+")',geom::geography) FROM highway_nodes ORDER BY geom <#> ST_GeomFromEWKT('SRID=4326;POINT("+str(c[1])+" "+str(c[0])+")') LIMIT "+str(NN_NUM)+ ")" for index,c in enumerate(coordinatelist)])

    #print("qry:\n" + QRY)
    cur.execute(QRY)
    qryres = sorted(cur.fetchall(), key = lambda x: x[0])
    #print("qry result\n:" + str(qryres))
    #[print("qryresult "+str(qr[0])+":\nnodeid: "+str(qr[1])+"\nlat: " +str(qr[2])+"\nlon: " +str(qr[3])+"\nwayid: "+str(qr[4])+"\nname: "+str(qr[5])+"\nref: "+str(qr[6])+"\nwaynodes: "+str(qr[7])+"\nseqid: "+str(qr[8])+"\ntags: "+str(qr[9])+"\ndist: "+str(qr[10])+ "\n\n") for qr in sorted(qryres, key=lambda x: x[0])]

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

                
                #waystreets.append({
                    #'name' : street['name'],
                    #'coordinates' : [
                        #{'lt': waystreets[-1]['coordinates'][-1]['lt'],
                            #'ln':  waystreets[-1]['coordinates'][-1]['ln'],
                            #'deviation': waystreets[-1]['coordinates'][-1]['deviation'] + street['srcdeviation']} if len(waystreets) > 0
                            #else {'lt': street['srclat'], 'ln': street['srclon'], 'deviation': street['srcdeviation']},
                        #{'lt': street['destlat'], 'ln': street['destlon'], 'deviation': street['destdeviation']}
                    #]
                #})



@route('/')
def hello():
    return "Usage: http://" + request.remote_route[-1] + "/streetname/?srclat=X&srclon=X&destlat=X&destlon=X"

@route('/streetname/',method='POST')
def findways():
    #[print("key: " + str(key) + "\ndata: " + repr(request.forms[key]\n\n)) for key in request.forms.keys()]
    content = json.loads(request.forms.nodes)
    print("/streetname/ called with \"nodes\": " + str(content)[:300])
    cur = conn.cursor() #multithreaded on one cursor probably doesn't work, so each thread doing a database connection gets a new one

    waystreets = []
    noway = []

    for subway in content:
        coordinatelist = tuple( [ (c[0]/COORD_DIV, c[1]/COORD_DIV) for c in subway ] )
        print ("coordinatelist: " + repr(coordinatelist)[:300])
        ws, nw = db_streets(cur,coordinatelist)
        waystreets.append(ws)
        noway.append(nw)

    # waystreets = list of subways
    # subway = list of possible parts
    # possible parts = list of alternative edges

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
                            {'lt': wayedges[-1]['coordinates'][-1]['lt'],
                                'ln':  wayedges[-1]['coordinates'][-1]['ln'],
                                'deviation': wayedges[-1]['coordinates'][-1]['deviation'] + edge['srcdeviation']} if len(wayedges) > 0
                                else {'lt': edge['srclat'], 'ln': edge['srclon'], 'deviation': edge['srcdeviation']},
                            {'lt': edge['destlat'], 'ln': edge['destlon'], 'deviation': edge['destdeviation']}
                        ]
                    })
    cur.close()
    result = {'streets' : wayedges, 'failed' : noway}
    print("response: " + repr(result)[:300])
    response.content_type = 'application/json; charset=utf8'
    return(json.dumps(ensure_ascii=False,  obj = result))

bottle.debug(True)
bottle.run(host='', port=8080, reloader=True,server='tornado')
conn.close()
