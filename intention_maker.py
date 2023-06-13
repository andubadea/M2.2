import osmnx as ox
import numpy as np
import networkx as nx
import random
import time
import copy
import os

from multiprocessing import Pool

    
class IntentionMaker:
    def __init__(self) -> None:
        # Design variables
        self.traffic_demand_levels = [30, 45, 60] # aircraft per minute
        self.repetitions_per_demand_level = 5
        self.min_mission_distance = 1000 #metres
        self.max_mission_distance = 6000 #metres
        self.intention_timespan = 90 # minutes
        self.min_distance_between_origins = 300 #metres
        self.num_origins = 200
        self.seed = 0
        
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.intention_path = self.path + '/Intentions'
        self.G = ox.load_graphml(f'{self.path}/streets.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.G) # Load the nodes and edges from the graph
        
    def make_intentions(self) -> None:
        """Function that creates the intentions and saves them in files in function of the
        parameters given in the init function.
        """
        # First, make an intention directory if there is none.
        os.makedirs(self.intention_path, exist_ok=True)
        # Get origins and destinations
        origins, destinations = self.create_origins_destinations()
        # Then, we for loop over demand levels and repetitions
        for demand in self.traffic_demand_levels:
            for repetition in range(self.repetitions_per_demand_level):
                # Get the intention data
                intention_data = self.create_intention(demand, origins, destinations)
                # Create the file and write to it
                with open(self.intention_path + f'/Flight_intention_{demand}_{repetition+1}.csv', 'w') as f:
                    for line in intention_data:
                        f.write(';'.join(line) + '\n')
        return
        
        
    def kwikdist(self, lata: float, lona: float, latb:float, lonb:float) -> float:
        """Gives quick and dirty qdr[deg] and dist [m]
        from lat/lon. (note: does not work well close to poles)"""

        re      = 6371000.  # radius earth [m]
        dlat    = np.radians(latb - lata)
        dlon    = np.radians(((lonb - lona)+180)%360-180)
        cavelat = np.cos(np.radians(lata + latb) * 0.5)

        dangle  = np.sqrt(dlat * dlat + dlon * dlon * cavelat * cavelat)
        dist    = re * dangle
        return dist
    
    def set_seed(self, seed: int) -> None:
        """Creates 

        Args:
            seed (int): Seed as an integer.
        """
        self.seed = seed
        random.seed(seed)

    def create_intention(self, demand: float, origins: list, destinations: list) -> list:
        """Creates a single flight intention file.

        Args:
            demand (float): Number of aircraft per minute.
            origins (list): List of origin nodes to use.
            destinations (list): List of destination nodes to use.
            
        Returns:
            intention (tuple): A tuple with each entry representing a flight intention
        """
        # Some values that are set the same for all flights
        known_time = '00:00:00'
        ac_model = 'MP30'
        priority = '1'
        # We basically want to go minute by minute and try to fit the required amount of traffic,
        # spawning them at different nodes.
        # We start at timestamp 0
        timestamp = 0 #Seconds
        # Increment for ACID
        acidx = 1
        # Check prev_used_nodes
        prev_used_nodes = []
        # Flight data
        flight_intention_data = []
        while timestamp < self.intention_timespan * 60:
            # Distribute the demand equally over this minute
            time_range = np.linspace(0, 59, demand).round().astype(int) + timestamp
            # Get the available nodes
            available_nodes = [node for node in origins if node not in prev_used_nodes]
            # Get a random sample from these nodes
            spawn_nodes = random.sample(available_nodes, demand)
            # Loop through these nodes and spawn aircraft these aircraft within a minute
            for i, spawn_node in enumerate(spawn_nodes):
                # Get the coordinates of the nodes
                spawn_node_lat = self.G.nodes[spawn_node]['y']
                spawn_node_lon = self.G.nodes[spawn_node]['x']
                
                # Let's try choosing a destination until the mission length requrement is met
                while True:
                    destination_node = random.choice(destinations)
                    destination_node_lat = self.G.nodes[destination_node]['y']
                    destination_node_lon = self.G.nodes[destination_node]['x']
                    dist_between_nodes = self.kwikdist(spawn_node_lat, spawn_node_lon, 
                                                       destination_node_lat, destination_node_lon)
                    
                    if self.min_mission_distance < dist_between_nodes <self.max_mission_distance:
                        # We're good
                        break
                    
                # We now have a destination. Can now append the flight intention data array with this flight
                spawn_time_seconds = time_range[i]
                acid = f'D{acidx}'
                origin = f'({spawn_node_lon},{spawn_node_lat})'
                destination = f'({destination_node_lon},{destination_node_lat})'
                spawn_time_hhmmss = time.strftime('%H:%M:%S', time.gmtime(spawn_time_seconds))
                
                flight_intention_data.append([acid, ac_model, spawn_time_hhmmss, spawn_node, destination_node, priority])
                # Increment acid by 1
                acidx += 1
            
            # Increment time range
            timestamp += 60
            # Overwrite the previously used nodes
            prev_used_nodes = copy.copy(spawn_nodes)
            
        # At the end, return the data
        return flight_intention_data
                        
    def create_origins_destinations(self) -> tuple:
        """Selects suitable origins and destinations from the nodes of a Graph.

        Returns:
            tuple: Contains two lists, origin nodes and destination nodes
        """
        # Let's make some origin and destinations from this graph
        origin_nodes = []
        attempts = 0
        # Maximum 100 attempts to select a node, and maximum 200 origin nodes
        while attempts < 100 and len(origin_nodes)<self.num_origins:
            # Select a node
            node = random.choice(list(self.G.nodes))
            # Extract its coordinates
            node_lat = self.G.nodes[node]['y']
            node_lon = self.G.nodes[node]['x']
            node_too_close = False
            # Check if the other nodes in the list are too close
            for existing_node in origin_nodes:
                # Extract their coordinates
                existing_node_lat = self.G.nodes[existing_node]['y']
                existing_node_lon = self.G.nodes[existing_node]['x']
                # Compute the distance
                dist = self.kwikdist(node_lat, node_lon, existing_node_lat, existing_node_lon)
                # Check if distance is small
                if dist < self.min_distance_between_origins:
                    # Node too close
                    node_too_close = True
                    break
            # Check if any node was too close
            if node_too_close:
                attempts += 1
            else:
                origin_nodes.append(node)
                attempts = 0
                
        # Compile the list of destination nodes
        destination_nodes = [x for x in self.G.nodes if x not in origin_nodes]
        return (origin_nodes, destination_nodes)
    
def main():
    # make an intention maker instance
    maker = IntentionMaker()
    # Create the intentions
    maker.make_intentions()
    return

if __name__ == "__main__":
    main()