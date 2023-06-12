import osmnx as ox
import numpy as np
import networkx as nx
import random
import os
import pickle

from dataclasses import dataclass
from multiprocessing import Pool

    
class IntentionMaker:
    def __init__(self) -> None:
        # Design variables
        self.traffic_demand_levels = [30, 45, 60] # aircraft per minute
        self.repetitions_per_demand_level = 5
        self.minimum_mission_length = 1000 #metres
        self.maximum_mission_length = 6000 #metres
        self.intention_timespan = 90 # minutes
        self.distance_between_origins = 300 #metres
        self.seed = 0
        
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        G = ox.load_graphml(f'{self.path}/streets.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(G) # Load the nodes and edges from the graph
        
    def kwikqdrdist(self, lata: float, lona: float, latb:float, lonb:float) -> tuple(float, float):
        """Gives quick and dirty qdr[deg] and dist [m]
        from lat/lon. (note: does not work well close to poles)"""

        re      = 6371000.  # radius earth [m]
        dlat    = np.radians(latb - lata)
        dlon    = np.radians(((lonb - lona)+180)%360-180)
        cavelat = np.cos(np.radians(lata + latb) * 0.5)

        dangle  = np.sqrt(dlat * dlat + dlon * dlon * cavelat * cavelat)
        dist    = re * dangle

        qdr     = np.degrees(np.arctan2(dlon * cavelat, dlat)) % 360

        return qdr, dist
    
    def set_seed(self, seed: int) -> None:
        """Creates 

        Args:
            seed (int): Seed as an integer.
        """
        self.seed = seed
        random.seed(seed)

    def create_intention(self, demand: float, origins: list, destinations: list) -> tuple:
        """Creates a single flight intention file.

        Args:
            demand (float): Number of aircraft per minute.
            origins (list): List of origin nodes to use.
            destinations (list): List of destination nodes to use.
            
        Returns:
            intention (tuple): A tuple with each entry representing a flight intention
        """
        # We basically want to go minute by minute and try to fit the required amount of traffic,
        # spawning them at different nodes.
        # We start at timestamp 0
        timestamp = 0 #Seconds
        # Check prev_used_nodes
        prev_used_nodes = []
        
        while timestamp < self.intention_timespan * 60:
            available_nodes = [node for node in origins if node not in prev_used_nodes]
            # Get a random sample from these nodes
            spawn_nodes = random.sample(available_nodes, demand)
            # Loop through these nodes and spawn aircraft these aircraft within a minute
            for spawn_node in spawn_nodes:
                # Get the node coordinates
                node_lat = self.G.nodes[spawn_node]['y']
                node_lon = self.G.nodes[spawn_node]['x']
                # TODO: Continue
            
    
    def create_origins_destinations(self, G: nx.MultiDiGraph) -> tuple:
        """Selects suitable origins and destinations from the nodes of a Graph.

        Args:
            G (nx.MultiDiGraph): Graph of street network.

        Returns:
            tuple: Contains two lists, origin nodes and destination nodes
        """
        # Let's make some origin and destinations from this graph
        origin_nodes = []
        attempts = 0
        # Maximum 100 attempts to select a node, and maximum 200 origin nodes
        while attempts < 100 and len(origin_nodes)<200:
            # Select a node
            node = random.choice(list(G.nodes))
            # Extract its coordinates
            node_lat = G.nodes[node]['y']
            node_lon = G.nodes[node]['x']
            #node_too_close = False
            # Check if the other nodes in the list are too close
            for existing_node in origin_nodes:
                # Extract their coordinates
                existing_node_lat = G.nodes[existing_node]['y']
                existing_node_lon = G.nodes[existing_node]['x']
                # Compute the distance
                _, dist = self.kwikqdrdist(node_lat, node_lon, existing_node_lat, existing_node_lon)
                # Check if distance is small
                if dist < 300:
                    # Node too close
                    node_too_close = True
                    break
            # Check if any node was too close
            if not node_too_close:
                attempts += 1
            else:
                origin_nodes.append(node)
                attempts = 0
                
        # Compile the list of destination nodes
        destination_nodes = [x for x in G.nodes if x not in origin_nodes]
        return (origin_nodes, destination_nodes)