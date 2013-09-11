-- Drop all primary keys and indexes to improve load speed.
-- DROP INDEX idx_relation_members_member_id_and_type;
-- ALTER TABLE relations DROP CONSTRAINT pk_relations;
-- ALTER TABLE relation_members DROP CONSTRAINT pk_relation_members;

ALTER TABLE nodes DROP CONSTRAINT IF EXISTS pk_nodes;
ALTER TABLE ways DROP CONSTRAINT IF EXISTS pk_ways;
ALTER TABLE way_nodes DROP CONSTRAINT IF EXISTS pk_way_nodes;
DROP INDEX IF EXISTS idx_nodes_geom;
DROP INDEX IF EXISTS idx_way_nodes_node_id;

-- Import the table data from the data files using the fast COPY method.
-- \copy users FROM 'users.txt'
-- \copy relations FROM 'relations.txt'
-- \copy relation_members FROM 'relation_members.txt'
\copy nodes (id, tags, geom) FROM PROGRAM 'cut -f 1,6,7 nodes.txt'
\copy ways (id, tags, nodes) FROM PROGRAM 'cut -f 1,6,7 ways.txt'
\copy way_nodes (way_id, node_id, sequence_id) FROM 'way_nodes.txt'

-- Add the primary keys and indexes back again
-- CREATE INDEX idx_relation_members_member_id_and_type ON relation_members USING btree (member_id, member_type);
-- ALTER TABLE ONLY relations ADD CONSTRAINT pk_relations PRIMARY KEY (id);
-- ALTER TABLE ONLY relation_members ADD CONSTRAINT pk_relation_members PRIMARY KEY (relation_id, sequence_id);
ALTER TABLE ONLY nodes ADD CONSTRAINT pk_nodes PRIMARY KEY (id);
ALTER TABLE ONLY ways ADD CONSTRAINT pk_ways PRIMARY KEY (id);
ALTER TABLE ONLY way_nodes ADD CONSTRAINT pk_way_nodes PRIMARY KEY (way_id, sequence_id);

CREATE INDEX idx_nodes_geom ON nodes USING gist (geom);
CREATE INDEX idx_way_nodes_node_id ON way_nodes USING btree (node_id);
CREATE INDEX idx_way_id ON ways USING btree (id);

GRANT ALL on nodes, way_nodes, ways TO osm;

-- could take a long time, benefit is unknown
-- CLUSTER nodes USING idx_nodes_geom;

VACUUM ANALYZE;