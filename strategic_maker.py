import osmnx as ox
import numpy as np
import networkx as nx
from shapely.ops import linemerge
from shapely.geometry import Point
from multiprocessing import Pool
import tqdm
import random
import os
import re

class StrategicScenarioMaker:
    def __init__(self) -> None:
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.scenario_path = self.path + '/Scenarios/Strategic'
        self.intention_path = self.path + '/Intentions'
        self.strategic_path = self.path + '/Strategic'
        self.G = ox.load_graphml(f'{self.path}/streets_new.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.G) # Load the nodes and edges from the graph
        # Aircraft related 
        self.speed = 30
        self.layer_height = 30 #ft
        self.num_cpu = 32
        return
    
    def create_scenario_from_strategic(self):
        """Takes all the strategically optimised intention files and converts them to
        scenario files."""
        # Get all the files
        strategic_files = [x for x in os.listdir(self.strategic_path) if '120_2.out' in x]
        
        for filename in strategic_files:
            with open(self.strategic_path + '/' + filename, 'r') as f:
                lines = f.readlines()
            
            # Multiprocessed line processing is fast
            print(f'Processing {filename}')
            with Pool(self.num_cpu) as p:
                scen_lines = list(tqdm.tqdm(p.imap(self.get_scenario_text_from_intention_line, lines), total = len(lines)))
                
            # Save em to file
            with open(self.strategic_path + '/' + filename.replace('.out', '.scn'), 'w') as f:
                sorted_lines = self.natural_sort(scen_lines)
                f.write(''.join(sorted_lines))
                    
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
    
    def get_scenario_text_from_intention_line(self, intention_line):
        """This function takes an intention line and converts it to a scenario line. This will depent on
        what information the intention line gives, and whether it includes an RTA or not.
        There are basically 2 cases we need to consider: RTA is given and RTA is not given."""
        
        # Intention line comes as a string in the following format
        # ACID, ALT[FT], DEP-TIME [HH:MM:SS], LAT, LON, RTA ....
        # First waypoint is also the spawn point
        # Let's first parse the thing.
        intention_line = intention_line.replace('\n','')
        line_split = intention_line.split(',')
        # Extract information
        acid = line_split[0]
        alt = int(line_split[1]) * self.layer_height
        dep_time = line_split[2]
        origin_lat = round(float(line_split[3]), 8)
        origin_lon = round(float(line_split[4]), 8)
        # We also want the next waypoint coords
        nxtwp_lat = float(line_split[6])
        nxtwp_lon = float(line_split[7])
        hdg = self.kwikqdr(float(line_split[3]), float(line_split[4]), nxtwp_lat, nxtwp_lon)
        # We can now initialise the CRE text
        scen_text = f'{dep_time}>M22CRE {acid},M600,{line_split[3]},{line_split[4]},{hdg},{alt},{self.speed}'
        # The RTA of the first waypoint, which is also the origin, doesn't matter.
        # Now, let's separate the route from the beginning
        route = line_split[6:]
        # Let's reshape this guy to a thing multiple of 6
        route_arr = np.reshape(route, (int(len(route)/3), 3))
        # Find all nodes in the route and their index
        nodes = []
        # Get the first node from the origin
        nodes.append((self.nodes[(self.nodes['geometry'] == Point(origin_lon, origin_lat))].index[0], -1))
        for i, waypoint_arr in enumerate(route_arr):
            wpt_point = Point(round(float(waypoint_arr[1]), 8), round(float(waypoint_arr[0]), 8))
            if wpt_point in self.nodes['geometry']:
                # We have a node, get its osmid
                nodes.append((self.nodes[(self.nodes['geometry'] == wpt_point)].index[0], i))

        # Now we have a list of nodes and where they are, so we can create the street number for each entry
        # The first waypoint is the one right after the origin, just for reference. Origin is index -1
        node_idx = 0
        u = nodes[node_idx][0]
        v = nodes[node_idx+1][0]
        # Add the origin as the first waypoint
        scen_text += f',{float(line_split[3])},{float(line_split[4])},,,,FLYTURN,{self.edges.loc[(u, v, 0), "stroke"]}'
        for wpidx, waypoint_arr in enumerate(route_arr):
            # Get the data from the waypoint_arr
            lat = float(waypoint_arr[0])
            lon = float(waypoint_arr[1])
            rta = waypoint_arr[2]
            if rta == '00:00:00':
                rta = ''
            # Check if we need to update the current edge. This only happens
            # if the wpidx is greater than the node index in edge_idx
            if nodes[node_idx+1][1] < wpidx:
                # Update the edge
                node_idx += 1
                u = nodes[node_idx][0]
                v = nodes[node_idx+1][0]
            
            # Now get the street number
            street_number = self.edges.loc[(u, v, 0), 'stroke']
            
            # Now append the waypoint information to the scen_text
            # First and last waypoint always a turn
            if wpidx == len(route_arr)-1:
                # Last waypoint, add a \n
                scen_text += f',{lat},{lon},,,{rta},FLYTURN,{street_number}\n'
            else:
                # We need to find the angle to determine whether it is a turn or not
                # Get the needed stuff
                if wpidx == 0:
                    lat_prev, lon_prev = float(line_split[3]), float(line_split[4])
                else:
                    lat_prev, lon_prev = float(route_arr[wpidx-1][0]),float(route_arr[wpidx-1][1])
                lat_next, lon_next = float(route_arr[wpidx+1][0]),float(route_arr[wpidx+1][1])
                
                # Get the angle
                d1=self.kwikqdr(lat_prev,lon_prev,lat,lon)
                d2=self.kwikqdr(lat,lon,lat_next,lon_next)
                angle=abs(d2-d1)

                if angle>180:
                    angle=360-angle
                    
                # This is a turn if angle is greater than 25
                if angle > 25:
                    scen_text += f',{lat},{lon},,,{rta},FLYTURN,{street_number}'
                else:
                    scen_text += f',{lat},{lon},,,{rta},FLYBY,{street_number}'

        return scen_text
    
    @staticmethod
    def natural_sort(l): 
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(l, key=alphanum_key)
    

def main():
    maker = StrategicScenarioMaker()
    # Create strategic scenarios
    maker.create_scenario_from_strategic()
    return

if __name__ == "__main__":
    main()