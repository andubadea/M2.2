import geopandas as gpd
import momepy
import osmnx as ox

# Select city
city = 'Vienna'

# Load graphml
G = ox.load_graphml(city + '/streets.graphml')

# Get the nodes, edges
nodes, edges = ox.graph_to_gdfs(G)

# Run coins
continuity = momepy.COINS(edges, angle_threshold=90)
continuity.stroke_gdf().to_file(city + '/street_groups.gpkg', driver='GPKG')
edges['stroke'] = continuity.stroke_attribute()

# Repackage
G_coined = ox.graph_from_gdfs(nodes, edges)

# Save
ox.save_graphml(G_coined, city + '/streets_coined.graphml')
ox.save_graph_geopackage(G_coined, city + '/streets_coined.gpkg')