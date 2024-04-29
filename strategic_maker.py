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
        self.city = './Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.scenario_4D_path = self.path + '/Base_Scenarios/4D/'
        self.scenario_2D_path = self.path + '/Base_Scenarios/2D/'
        self.scenario_1D_path = self.path + '/Base_Scenarios/1D/'
        self.scenario_std_path = self.path + '/Base_Scenarios/Standard/'
        self.strategic_4D_path = self.path + '/Strategic/4D/'
        self.strategic_2D_path = self.path + '/Strategic/2D/'
        self.strategic_1D_path = self.path + '/Strategic/1D/'
        self.G = ox.load_graphml(f'{self.path}/streets.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.G) # Load the nodes and edges from the graph
        # Aircraft related 
        self.speed = 30
        self.layer_height = 50 #ft
        self.max_altitude = 500
        self.num_cpu = 2
        return
    
    def create_all_scenarios_from_strategic(self):
        strategic_files = [self.strategic_4D_path + x for x in os.listdir(self.strategic_4D_path) if ('.out' in x)]
        #strategic_files =[self.strategic_2D_path + x for x in os.listdir(self.strategic_2D_path) if ('.out' in x)]
        #strategic_files +=[self.strategic_1D_path + x for x in os.listdir(self.strategic_1D_path) if ('.out' in x)]
        
        with Pool(self.num_cpu) as p:
            _ = list(tqdm.tqdm(p.imap(self.create_one_scenario, strategic_files), total = len(strategic_files)))
        
    def create_one_scenario(self, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()
            
        scen_lines = []
        for line in lines:
            scen_lines.append(self.get_scenario_text_from_intention_line(line))
        
        output_name = filename.replace('Strategic', 'Base_Scenarios').replace('.out','.scn')

        with open(output_name, 'w') as f:
            sorted_lines = self.natural_sort(scen_lines)
            f.write(''.join(sorted_lines))
                
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
        origin_node = int(line_split[3])
        origin_lon, origin_lat = self.nodes.at[origin_node,'geometry'].x, self.nodes.at[origin_node,'geometry'].y
        # We also want the next waypoint coords
        nxt_node = int(line_split[5])
        nxtwp_lon, nxtwp_lat = self.nodes.at[nxt_node,'geometry'].x, self.nodes.at[nxt_node,'geometry'].y
        street_number = self.edges.at[(origin_node, nxt_node, 0), 'stroke']
        hdg = self.kwikqdr(origin_lat, origin_lon, nxtwp_lat, nxtwp_lon)
        # We can now initialise the CRE text
        scen_text = f'{dep_time}>M22CRE {acid},M600,{origin_lat},{origin_lon},{hdg},{alt},{self.speed}'
        # The RTA of the first waypoint, which is also the origin, doesn't matter.
        # Now, let's separate the route from the beginning
        route = line_split[3:]
        # Let's reshape this guy to a thing multiple of 2
        route_arr = np.reshape(route, (int(len(route)/2), 2))
        # now add the waypoints
        for i, wpdata in enumerate(route_arr):
            # Get the data from the waypoint_arr
            current_node = int(wpdata[0])
            lon, lat = self.nodes.at[current_node,'geometry'].x, self.nodes.at[current_node,'geometry'].y
            
            rta = wpdata[1]
            if rta == '00:00:00':
                rta = ''
                
            if i == 0:
                # origin, not a turn
                scen_text += f',{lat},{lon},,,{rta},FLYBY,{street_number}'
                continue
                
            # Now get the street number
            v = current_node
            u = int(route_arr[:,0][i-1])
            street_number = self.edges.at[(u, v, 0), 'stroke']
            
            # Now append the waypoint information to the scen_text
            # First and last waypoint always a turn
            if i == len(route_arr)-1:
                # Last waypoint, add a \n
                scen_text += f',{lat},{lon},,,{rta},FLYTURN,{street_number}\n'
            else:
                # We need to find the angle to determine whether it is a turn or not
                # Get the needed stuff
                prev_node = int(route_arr[:,0][i-1])
                next_node = int(route_arr[:,0][i+1])
                lon_prev, lat_prev = self.nodes.at[prev_node,'geometry'].x, self.nodes.at[prev_node,'geometry'].y
                lon_next, lat_next = self.nodes.at[next_node,'geometry'].x, self.nodes.at[next_node,'geometry'].y
                
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
    maker.create_all_scenarios_from_strategic()
    return

if __name__ == "__main__":
    main()