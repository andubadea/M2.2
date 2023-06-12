import osmnx as ox
import numpy as np
import networkx as nx
from dataclasses import dataclass
from multiprocessing import Pool
import random
import os
    
class IntentionMaker:
    def __init__(self) -> None:
        # Design variables
        self.traffic_demand_levels = [30, 45, 60] # aircraft per minute
        self.repetitions_per_demand_level = 5
        self.minimum_mission_length = 1000 #metres
        self.maximum_mission_length = 6000 #metres
        self.seed = 0
        
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
    
    def set_seed(self, seed):
        self.seed = seed
        random.seed(seed)

    def create_intention(self, demand: float, mindist: float, maxdist: float):
        pass