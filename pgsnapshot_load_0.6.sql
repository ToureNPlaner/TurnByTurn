-- Drop all primary keys and indexes to improve load speed.
ALTER TABLE nodes DROP CONSTRAINT pk_nodes;
ALTER TABLE ways DROP CONSTRAINT pk_ways;
ALTER TABLE way_nodes DROP CONSTRAINT pk_way_nodes;
ALTER TABLE relations DROP CONSTRAINT pk_relations;
ALTER TABLE relation_members DROP CONSTRAINT pk_relation_members;
DROP INDEX idx_nodes_geom;
DROP INDEX idx_way_nodes_node_id;
DROP INDEX idx_relation_members_member_id_and_type;

-- Import the table data from the data files using the fast COPY method.
\copy users FROM 'users.txt'
\copy nodes FROM 'nodes.txt'
\copy ways FROM 'ways.txt'
\copy way_nodes FROM 'way_nodes.txt'
\copy relations FROM 'relations.txt'
\copy relation_members FROM 'relation_members.txt'

-- Add the primary keys and indexes back again
ALTER TABLE ONLY nodes ADD CONSTRAINT pk_nodes PRIMARY KEY (id);
ALTER TABLE ONLY ways ADD CONSTRAINT pk_ways PRIMARY KEY (id);
ALTER TABLE ONLY way_nodes ADD CONSTRAINT pk_way_nodes PRIMARY KEY (way_id, sequence_id);
ALTER TABLE ONLY relations ADD CONSTRAINT pk_relations PRIMARY KEY (id);
ALTER TABLE ONLY relation_members ADD CONSTRAINT pk_relation_members PRIMARY KEY (relation_id, sequence_id);
CREATE INDEX idx_nodes_geom ON nodes USING gist (geom);
CREATE INDEX idx_way_nodes_node_id ON way_nodes USING btree (node_id);
CREATE INDEX idx_relation_members_member_id_and_type ON relation_members USING btree (member_id, member_type);

-- for dbstreets: this will select only the rows and columns relevant to the turn-by-turn navigation into highway_nodes, highway_ways and highway_way_nodes
SELECT DISTINCT ways.id, ways.tags, ways.nodes INTO highway_ways FROM ways WHERE ways.tags::hstore ? 'highway';
CREATE INDEX idx_highway_ways_id ON highway_ways(id);
ALTER TABLE highway_ways ADD PRIMARY KEY(id);

SELECT DISTINCT way_nodes.way_id, way_nodes.node_id, way_nodes.sequence_id INTO highway_way_nodes FROM way_nodes INNER JOIN highway_ways ON way_nodes.way_id = highway_ways.id;
CREATE INDEX idx_highway_way_nodes_node_id ON highway_way_nodes(node_id);
ALTER TABLE highway_way_nodes ADD PRIMARY KEY(node_id);
ALTER TABLE highway_way_nodes ADD FOREIGN KEY(way_id) REFERENCES highway_ways(id);

SELECT DISTINCT nodes.id, nodes.tags, nodes.geom INTO highway_nodes FROM nodes INNER JOIN highway_way_nodes ON nodes.id = highway_way_nodes.node_id;
ALTER TABLE highway_nodes ADD CONSTRAINT id_unique UNIQUE (id);
CREATE INDEX idx_highway_nodes_geom ON highway_nodes USING GIST(geom);
ALTER TABLE highway_way_nodes ADD FOREIGN KEY(node_id) REFERENCES highway_nodes(id);

GRANT ALL on highway_nodes, highway_way_nodes, highway_ways TO osm;
-- could take a long time:
--CLUSTER highway_nodes USING idx_highway_nodes_geom;
-- end stuff for dbstreets

VACUUM ANALYZE;
