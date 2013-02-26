#!/usr/bin/env python3
import psycopg2,sys,time

if len(sys.argv) < 3:
    print("nn_test.py random_coordinatefile(line = 'int_lon int_lat') csvfile [pp|normal]")
    exit(1)

pps_create = """PREPARE nns1(text,int) AS
SELECT id,geom
FROM highway_nodes
ORDER BY geom <-> ST_GeomFromEWKT($1)
LIMIT $2;"""

if len(sys.argv) == 4:
    pp = sys.argv[3] == "pp"
else:
    pp = "normal"

conn = psycopg2.connect("dbname=gis user=osm")
cur = conn.cursor()
nodes_table = "highway_nodes"

if pp:
    cur.execute(pps_create)

statistic = open(sys.argv[2], 'w')
statistic.write("number of nearest neighbours,shortest,longest,total\n")
for NN in range(1,21):
    shortesttime = 1000000
    longesttime = 0
    acctime = 0
    f = open(sys.argv[1])
    while 1:
        cstring = f.readline()
        if not cstring: break
        c = cstring.split(" ")
        lon = (float(c[0])) / 10**7
        lat = (float(c[1])) / 10**7
        if pp:
            query = "EXECUTE nns1('SRID=4326;POINT(" + str(lon) + " " + str(lat) + ")', " + str(NN) + ");"
        else:
            query = "SELECT id,geom FROM " + nodes_table + " ORDER BY geom <#> ST_GeomFromEWKT('SRID=4326;POINT(" + str(lon) + " " + str(lat) + ")') LIMIT " + str(NN) + ";"
        start = time.time()
        cur.execute(query)
        stop = time.time()
        tdiff = (stop - start)
        if tdiff > longesttime:
            longesttime = tdiff
        if tdiff < shortesttime:
            shortesttime = tdiff
        #print("nn took " + str(stop - start) + " seconds")
        acctime += tdiff
    print ("NN = " + str(NN).zfill(2) + ":")
    print ("\taccumulated time: " + str(round(acctime,4)) + " seconds")
    print ("\tShortest time   : " + str(round(shortesttime, 4)) + " seconds")
    print ("\tLongst time     : " + str(round(longesttime, 4)) + " seconds")
    statistic.write(str(NN) + "," + str(round(shortesttime,4)) + "," + str(round(longesttime,4)) + "," + str(round(acctime,4)) + "\n")
    f.close()
statistic.close()
conn.close()
