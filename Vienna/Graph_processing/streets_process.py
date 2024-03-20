import geopandas as gpd
import momepy
from shapely.geometry import LineString
import osmnx as ox
import numpy as np
import networkx as nx

# Load graphml
# G = ox.load_graphml(city + '/streets.graphml')

# # Get the nodes, edges
# nodes, edges = ox.graph_to_gdfs(G)

# Run coins
# continuity = momepy.COINS(edges, angle_threshold=90)
# continuity.stroke_gdf().to_file(city + '/street_groups.gpkg', driver='GPKG')
# edges['stroke'] = continuity.stroke_attribute()

# Repackage
#G_coined = ox.graph_from_gdfs(nodes, edges)

# Save
# ox.save_graphml(G_coined, city + '/streets_coined.graphml')
# ox.save_graph_geopackage(G_coined, city + '/streets_coined.gpkg')


# Delete small edges
# Load graphml
G = ox.load_graphml('streets_AAA.graphml')
print(nx.is_strongly_connected(G))
ox.distance.add_edge_lengths(G)

# Get the nodes, edges
nodes, edges = ox.graph_to_gdfs(G)
nodes_to_drop = []
edges_to_drop = []
short_edges = edges.index[edges['length'] < 8].tolist()
print(len(short_edges))

def kwikdist(lata: float, lona: float, latb:float, lonb:float) -> float:
        """Gives quick and dirty dist [m]
        from lat/lon. (note: does not work well close to poles)"""

        re      = 6371000.  # radius earth [m]
        dlat    = np.radians(latb - lata)
        dlon    = np.radians(((lonb - lona)+180)%360-180)
        cavelat = np.cos(np.radians(lata + latb) * 0.5)

        dangle  = np.sqrt(dlat * dlat + dlon * dlon * cavelat * cavelat)
        dist    = re * dangle
        return dist
    
already_done = []

for index in short_edges:
    u,v,_ = index
    # We delete try to delete u. Get the edges where u is contained.
    contains_u = [x for x in edges.index.tolist() if (x[0] == u or x[1] == u)]
    skip = False
    for indexasd in contains_u:
        if indexasd[0] in already_done or indexasd[1] in already_done:
            skip = True
                
    if skip:
        continue
    
    if u in already_done or v in already_done:
        continue
    
    already_done.append(u)
    already_done.append(v)
    # Get geometry of u
    geom_u = nodes.loc[u]['geometry']
    geom_v = nodes.loc[v]['geometry']
    
    nodes_to_drop.append(u)
    edges_to_drop.append(index)
    
    # For each of these edges, we need to connect them to v insead of u
    for this_index in contains_u:
        geom = edges.loc[this_index]['geometry']
        if this_index == index:
            # This is the edge we're considering, skip.
            continue
        if u == this_index[0]:
            already_done.append(this_index[1])
            # u is in the front
            new_geom = np.array(geom.xy).T
            new_geom[0] = [geom_v.x, geom_v.y]
            new_geom_line = LineString(new_geom)
            # Create the new entry
            new_entry = edges.loc[this_index].to_dict()
            new_entry['geometry'] = new_geom_line
            # dist = 0
            # for i in range(len(new_geom) - 1):
            #     dist += kwikdist(new_geom[i][1], new_geom[i][0], new_geom[i+1][1], new_geom[i+1][0])
            # new_entry['length'] = dist
            edges.loc[(v,this_index[1],0)] = new_entry
            edges_to_drop.append(this_index)
        elif u == this_index[1]:
            already_done.append(this_index[0])
            # u is in the back
            new_geom = np.array(geom.xy).T
            new_geom[-1] = [geom_v.x, geom_v.y]
            new_geom_line = LineString(new_geom)
            # Create the new entry
            new_entry = edges.loc[this_index].to_dict()
            new_entry['geometry'] = new_geom_line
            # dist = 0
            # for i in range(len(new_geom) - 1):
            #     dist += kwikdist(new_geom[i][1], new_geom[i][0], new_geom[i+1][1], new_geom[i+1][0])
            # new_entry['length'] = dist
            edges.loc[(this_index[0],v,0)] = new_entry
            edges_to_drop.append(this_index)
        else:
            print('wrong')
            
#edges = edges.drop(short_edges)
edges = edges.drop(edges_to_drop)
nodes = nodes.drop(nodes_to_drop)

edges.set_crs(epsg=4326, inplace = True)
nodes.set_crs(epsg=4326, inplace = True)

G_new = ox.graph_from_gdfs(nodes, edges)
print(nx.is_strongly_connected(G_new))
ox.distance.add_edge_lengths(G_new)



ox.save_graphml(G_new, 'streets_AAAA.graphml')
ox.save_graph_geopackage(G_new, 'streets_AAAA.gpkg', directed = True)

# Check origin and dest nodes in intentions for the removed nodes

# for intention_file in os.listdir('Vienna/Intentions'):
#     data = np.genfromtxt(f'Vienna/Intentions/{intention_file}', delimiter=';', dtype=str)
#     for node in nodes_to_drop:
#         if str(node) in data[:,3] or str(node) in data[:,4]:
#             print(intention_file, node)


            
        
        
    