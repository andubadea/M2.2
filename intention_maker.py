import osmnx as ox
import numpy as np
import networkx as nx
from shapely.ops import linemerge
import random
import time
import copy
import os

from multiprocessing import Pool

    
class IntentionMaker:
    def __init__(self) -> None:
        # Design variables
        self.traffic_demand_levels = [30,60,90]#[30, 45, 60] # aircraft per minute
        self.repetitions_per_demand_level = 5
        self.min_mission_distance = 1000 #metres
        self.max_mission_distance = 6000 #metres
        self.intention_timespan = 90 # minutes
        self.min_distance_between_origins = 300 #metres
        self.num_origins = 200
        self.seed = 0
        self.layer_height = 30
        self.max_altitude = 500
        self.speed = 30
        
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.intention_path = self.path + '/Intentions'
        self.scenario_path = self.path + '/Scenarios'
        self.G = ox.load_graphml(f'{self.path}/streets.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.G) # Load the nodes and edges from the graph
        
    def make_intentions(self) -> None:
        """Function that creates the intentions and saves them in files in function of the
        parameters given in the init function.
        """
        # First, make an intention directory if there is none.
        os.makedirs(self.intention_path, exist_ok=True)
        os.makedirs(self.scenario_path, exist_ok=True)
        # Get origins and destinations
        origins, destinations = self.create_origins_destinations()
        # Then, we for loop over demand levels and repetitions
        for demand in self.traffic_demand_levels:
            for repetition in range(self.repetitions_per_demand_level):
                # Get the intention data
                intention_data, scenario_data = self.create_intention(demand, origins, destinations)
                # Create the file and write to it
                with open(self.intention_path + f'/Flight_intention_{demand}_{repetition+1}.txt', 'w') as f:
                    for line in intention_data:
                        f.write(';'.join(line) + '\n')
                        
                with open(self.scenario_path + f'/Flight_intention_{demand}_{repetition+1}.scn', 'w') as f:
                    for line in scenario_data:
                        f.write(line)
        return
        
        
    def kwikdist(self, lata: float, lona: float, latb:float, lonb:float) -> float:
        """Gives quick and dirty dist [m]
        from lat/lon. (note: does not work well close to poles)"""

        re      = 6371000.  # radius earth [m]
        dlat    = np.radians(latb - lata)
        dlon    = np.radians(((lonb - lona)+180)%360-180)
        cavelat = np.cos(np.radians(lata + latb) * 0.5)

        dangle  = np.sqrt(dlat * dlat + dlon * dlon * cavelat * cavelat)
        dist    = re * dangle
        return dist
    
    def kwikqdr(self, lata: float, lona: float, latb: float, lonb: float)-> float:
        """Gives quick and dirty qdr[deg]
        from lat/lon. (note: does not work well close to poles)"""
        dlat    = np.radians(latb - lata)
        dlon    = np.radians(((lonb - lona)+180)%360-180)
        cavelat = np.cos(np.radians(lata + latb) * 0.5)

        qdr     = np.degrees(np.arctan2(dlon * cavelat, dlat)) % 360

        return qdr
    
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
        flight_scenario_data = []
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
                
                flight_intention_data.append([acid, ac_model, spawn_time_hhmmss, str(spawn_node), str(destination_node), priority])
                # Get flight scenario data
                flight_scenario_data.append(self.get_scenario_line(acid, spawn_time_hhmmss, spawn_node, destination_node))
                # Increment acid by 1
                acidx += 1
            
            # Increment time range
            timestamp += 60
            # Overwrite the previously used nodes
            prev_used_nodes = copy.copy(spawn_nodes)
            
        # At the end, return the data
        return flight_intention_data, flight_scenario_data
    
    def get_scenario_line(self, acid: str, spawn_time: str, spawn_node: int, dest_node: int) -> str:
        # Get possible spawning altitudes
        altitudes = np.arange(self.layer_height, self.max_altitude, self.layer_height)
        # Pick a random one
        alt = random.choice(altitudes)
        # Create the path for these two nodes
        route = nx.shortest_path(self.G, spawn_node, dest_node)
        # Extract the path geometry
        geoms = [self.edges.loc[(u, v, 0), 'geometry'] for u, v in zip(route[:-1], route[1:])]
        line = linemerge(geoms)
        
        # Prepare the edges
        point_edges = []
        i = 0
        for geom, u, v in zip(geoms, route[:-1], route[1:]):
            if i == 0:
                # First edge, also take the first waypoint
                for coord in geom.coords:
                    point_edges.append([u,v])
            else:
                first = True
                for coord in geom.coords:
                    if first:
                        first = False
                        continue
                    point_edges.append([u,v])
            i += 1
        # Get initial heading
        hdg = self.kwikqdr(line.xy[1][0], line.xy[0][0], line.xy[1][1], line.xy[0][1])
        # Initialise the scen_text
        scen_text = f'{spawn_time}>CRE {acid},M600,{line.xy[1][0]},{line.xy[0][0]},{hdg},{alt},{self.speed}\n'
        scen_text+= f'{spawn_time}>ADDWPTMODE {acid} TURNBANK 25\n'
        scen_text+= f'{spawn_time}>ADDWPTMODE {acid} TURNRAD 0.00216\n'
                
        # Also prepare the turns
        latlons = list(zip(line.xy[1], line.xy[0]))
        turns = [True] # Always make first wpt a turn
        scen_text += f'{spawn_time}>ADDWAYPOINTS {acid} '
        # Add first waypoint, always a turn
        scen_text += f'{line.xy[1][0]},{line.xy[0][0]},,,FLYTURN'
        i = 1
        for lat_cur, lon_cur in latlons[1:-1]:
            # Get the needed stuff
            lat_prev, lon_prev = latlons[i-1]
            lat_next, lon_next = latlons[i+1]
            
            # Get the angle
            d1=self.kwikqdr(lat_prev,lon_prev,lat_cur,lon_cur)
            d2=self.kwikqdr(lat_cur,lon_cur,lat_next,lon_next)
            angle=abs(d2-d1)

            if angle>180:
                angle=360-angle
                
            # This is a turn if angle is greater than 25
            if angle > 25:
                scen_text += f',{lat_cur},{lon_cur},,,FLYTURN'
            else:
                scen_text += f',{lat_cur},{lon_cur},,,FLYBY'
                
            i+= 1
                
        #Last waypoint is always a turn one.        
        turns.append(True)
        # Add the last waypoint
        scen_text += f',{line.xy[1][-1]},{line.xy[0][-1]},,,FLYTURN\n'
        scen_text += f'{spawn_time}>CRUISESPD {acid} {self.speed}\n'
        scen_text += f'{spawn_time}>ATDIST {acid} {line.xy[1][-1]} {line.xy[0][-1]} 5 DELETE {acid}\n'
        scen_text += f'{spawn_time}>LNAV {acid} ON\n{spawn_time}>VNAV {acid} ON\n\n'
        return scen_text
        
        
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