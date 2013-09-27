import pprint
import math

FACTOR = 10**7
KEYFACTOR = FACTOR / 1000

roundabout = [
    [(0,0)],
    [(-1,-1), (0,-1), (1,-1), (1,0), (-1,0), (-1,1), (0,1), (1,1)]
]

class nnsearcher(object):

#    def __init__(self):

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

    def readfiles(self, file):
        with open(file, 'rb') as to_unpickle:
            import pickle

            data = pickle.load(to_unpickle, encoding="latin1")
            self.nodeids = data["nodeids"]
            self.nodetags = data["nodetags"]
            self.coordinates = data["nodecoordinates"]

            self.wayids = data["wayids"]
            self.waytags = data["waytags"]
            self.waynodes = data["waynodes"]

        print("file loaded")
        print("coords", len(self.coords))
        print("nodes", len(self.nodes))
        print("ways", len(self.ways))

        self.nnmap = {}

        for c in self.coords:
            lat = int(self.coords[c][1] * KEYFACTOR)
            lon = int(self.coords[c][0] * KEYFACTOR)
            key = (lat, lon)
            if key in self.nnmap:
                self.nnmap[key].append(c)
            else:
                self.nnmap[key] = [c]
        print("%s cells" % len(self.nnmap))


    def getNN(self, coordinate, num=1):
        latkey = int(coordinate[0] * KEYFACTOR)
        lonkey =  int(coordinate[1] * KEYFACTOR)
        mindist = 1000000000
        minnode = -1
        for hops in roundabout:
            for adding in hops:
                key = (latkey + adding[0], lonkey + adding[1])
                if not key in self.nnmap:
                    continue

                found = self.nnmap[key]
                for f in self.nnmap[found]:
                    print("Possible node for", coordinate, ": ", f)
                    print("comparing", coordinate[0], coordinate[1], self.coords[f][1], self.coords[f][0])
                    dist = self.distance_on_unit_sphere(coordinate[0], coordinate[1], self.coords[f][1], self.coords[f][0])

    def dumbnn(self, coordinate):
        lat = coordinate[0]
        lon = coordinate[1]
        mindist = 10000
        minnode = -1
        for n in self.coords:
            for c in self.coords[n]:
                dist = self.distance_on_unit_sphere(lat, lon, c[1], c[0])
                if dist < mindist:
                    mindist = dist
                    minnode = c
        if minnode != -1:
            return minnode