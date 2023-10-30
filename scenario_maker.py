import osmnx as ox
import numpy as np
import networkx as nx
from shapely.ops import linemerge
import random
import time
import copy
import os

class ScenarioMaker:
    def __init__(self) -> None:
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.scenario_path = self.path + '/Scenarios'
        self.intention_path = self.path + '/Intentions'
        self.strategic_path = self.path + '/Strategic'
        self.G = ox.load_graphml(f'{self.path}/streets.graphml') # Load the street graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.G) # Load the nodes and edges from the graph
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
    
    def get_baseline_scenario_line(self, acid: str, spawn_time: str, spawn_node: int, dest_node: int) -> str:
        # Get possible spawning altitudes
        altitudes = np.arange(self.layer_height, self.max_altitude, self.layer_height)
        # Pick a random one
        alt = random.choice(altitudes)
        # Create the path for these two nodes
        route = nx.shortest_path(self.G, spawn_node, dest_node, weight = 'length')
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
    
    def get_scenario_line_from_intention_line(self):
        return