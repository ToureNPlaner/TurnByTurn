#!/usr/bin/env python2

import json
import osm
import osm.compiler
import osm.factory
import osm.sink

conf = json.load(open("config.json"))
osm_file = conf['osm_file']
pickled_node_file = conf["pickled_node_file"]
pickled_way_file = conf["pickled_way_file"]

class WayStoreOSMSink():
    what = "ways"

    def __init__(self):
        self.wayindex = 0
        self.wayids = []
        self.waytags = []
        self.waynodes = []

        self.nodeids = []
        self.relations = []

        self.discarded = 0

    def processWay(self, id, tags, nodes):
        if "highway" in tags:
            self.wayids.append(id)
            self.waytags.append(tags)
            self.waynodes.append(nodes)
            self.wayindex += 1
        else:
            self.discarded += 1

    #def processRelation(self, rel):
    #    pass
    def processMember(self, member):
        pass


class NodeStoreOSMSink():
    what = "nodes"

    def __init__(self, waynodes):
        self.nodeindex = 0
        self.nodeids = []
        self.nodetags = []
        #[(lat, lon), (lat, lon), ...]
        self.coordinates = []
        self.waynodes = waynodes

        self.wayids = []
        self.relations = []

        self.discarded = 0

    def processNode(self, id, tags, lat, lon):
        if id in self.waynodes:
            self.nodeids.append(id)
            self.nodetags.append(tags)
            self.coordinates.append((lat, lon))
            self.nodeindex += 1
        else:
            self.discarded += 1

    #def processRelation(self, rel):
    #    pass
    def processMember(self, member):
        pass

#def delete_nodes(store):
#    to_keep_nodes = set()
#    for w in store.ways:
#        for node in store.ways[w].nodes:
#            to_keep_nodes.add(node)
#    print("%s nodes, %s nodes to keep" % (len(store.nodes), len(to_keep_nodes)))
#    to_delete_nodes = set(store.nodes.keys()) - to_keep_nodes
#    for td in to_delete_nodes:
#        del store.nodes[td]
#    print("%s nodes" % len(store.nodes))

def parsefile(store, fn):
    with open(fn, "rb") as fpbf:
        parser = osm.compiler.OSMCompiler(fpbf, store, osm.factory.OSMFactory(), True)
        print("parsing \"%s\" from %s" % (store.what, osm_file))
        parser.parse()
        print("parsed! %s nodes, %s ways, %s relations, %s discarded" % (
            len(store.nodeids), len(store.wayids), len(store.relations), store.discarded))

def picklefile(fn, obj):
    import cPickle
    with open(fn, 'wb') as output:
        cPickle.dump(obj, output)


waystore = WayStoreOSMSink()
parsefile(waystore, osm_file)
picklefile(pickled_way_file,
           {
               "wayids": waystore.wayids,
               "waytags": waystore.waytags,
               "waynodes": waystore.waynodes
           })

way_nodes = set()
for nodesset in waystore.waynodes:
    for node in nodesset:
        way_nodes.add(node)

del waystore

# must parse ways first to know which nodes are not in ways we have
nodestore = NodeStoreOSMSink(way_nodes)
parsefile(nodestore, osm_file)
del way_nodes
picklefile(pickled_node_file,
           {
               "nodeids": nodestore.nodeids,
               "nodetags": nodestore.nodetags,
               "nodecoordinates": nodestore.coordinates,
           })