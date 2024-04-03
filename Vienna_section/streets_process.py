import geopandas as gpd
import momepy
from shapely.geometry import LineString
import osmnx as ox
import numpy as np
import networkx as nx
import pickle

# Load graphml
G = ox.load_graphml('streets.graphml')

# # Get the nodes, edges
nodes, edges = ox.graph_to_gdfs(G)
print(edges.columns)
edges['stroke'] = edges['stroke_group']

edges.to_file('street_groups.gpkg', driver='GPKG', include_fields = 'stroke_group')

stroke_dict = dict()
for u,v,_ in edges.index.to_list():
    stroke_dict[(u,v)] = edges.loc[(u,v,0), 'stroke']
    
with open(f'street_numbers.pkl', 'wb') as f:
    pickle.dump(stroke_dict, f, protocol=pickle.HIGHEST_PROTOCOL)