import geopandas as gpd
from shapely.geometry import LineString
import shapely
import momepy
import osmnx as ox
import networkx as nx
import numpy as np

# # Load the graph
#G = ox.load_graphml('Vienna/streets_new.graphml')

# # Edges and nodes
# nodes, edges = ox.graph_to_gdfs(G)

# # Get the biggest node index
# new_node_idx = max(nodes.index.to_list()) + 1

graph = gpd.read_file('Vienna/exploded.gpkg')
graph['length'] = graph.geometry.length
# Function to round a coordinate to a specified number of decimal places
def round_coordinates(row, num_decimal_places):
    return shapely.transform(row, lambda x: np.round(x,decimals=2))
     
 
# Specify the number of decimal places you want to round to
num_decimal_places = 2
 
# Apply the rounding function to X and Y coordinates in the geometry
graph['geometry'] = graph['geometry'].apply(lambda row: round_coordinates(row, num_decimal_places))

new_graph = momepy.gdf_to_nx(graph, length = 'length', directed = True)

nodes, edges = momepy.nx_to_gdf(new_graph, nodeID='osmid')

edges['u'] = edges['node_start']
edges['v'] = edges['node_end']
edges['key'] = 0
edges.set_index(['u', 'v', 'key'], inplace = True)
nodes.set_index('osmid', inplace = True)
edges.to_crs(epsg=4326, inplace = True)
nodes.to_crs(epsg=4326, inplace = True)
nodes['x'] = nodes.geometry.x
nodes['y'] = nodes.geometry.y
G_new = ox.graph_from_gdfs(nodes, edges)

print(nx.is_strongly_connected(G_new))

city = 'Vienna'
ox.save_graphml(G_new, city + '/streets_new_new.graphml')
ox.save_graph_geopackage(G_new, city + '/streets_new_new.gpkg', directed = True)