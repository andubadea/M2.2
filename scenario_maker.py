import shutil
from multiprocessing import Pool
import itertools
import tqdm
import os
import re

class ScenarioMaker:
    def __init__(self) -> None:
        # City related parameters
        self.city = 'Vienna' # City name
        self.path = f'{self.city}' # Folder path
        self.scenario_path = self.path + '/Base Scenarios/'
        self.output_path = self.path + '/M2.2/'
        # Aircraft related 
        self.speed = 30
        self.layer_height = 30 #ft
        self.num_cpu = 16
        # Independent variables
        self.demand = [60, 90, 120]
        self.tactical = ['NoCR', 'SB']
        #self.strategic = ['RALT', '1D', '2D', '4D', '4DRTA']
        self.strategic = ['RALT','4D', '4DRTA']
        self.delay_mag = [0, 10, 30, 60]
        self.delay_prob = [0, 10, 30, 50]
        self.wind_mag = [0, 2, 4, 6, 8]
        self.wind_dir = [0, 90, 180, 270]
        self.repetition = [1,2,3,4,5]
        return
    
    def create_experiment_scenarios(self):
        # First list is with 0 wind and delay
        input_arr_1 = list(itertools.product(*[self.demand, 
                                       self.tactical, 
                                       self.strategic, 
                                       [0], 
                                       [0], 
                                       [0], 
                                       [0], 
                                       self.repetition]))
        
        # Now fix the demand and do the delay with 0 wind
        input_arr_2 = list(itertools.product(*[[90], 
                                       self.tactical, 
                                       self.strategic, 
                                       self.delay_mag, 
                                       self.delay_prob, 
                                       [0], 
                                       [0], 
                                       self.repetition]))
        
        # And now the delay
        input_arr_3 = list(itertools.product(*[[90], 
                                       self.tactical, 
                                       self.strategic, 
                                       [0], 
                                       [0], 
                                       self.wind_mag, 
                                       self.wind_dir, 
                                       self.repetition]))
        
        input_arr = input_arr_1 + input_arr_2 + input_arr_3
        
        # Make a pool and create scenarios
        with Pool(self.num_cpu) as p:
            _ = list(tqdm.tqdm(p.imap(self.create_scenario_file, input_arr), total = len(input_arr)))
        
        
    def create_scenario_file(self, args):
        # Unpack
        demand, tactical, strategic, delay_mag, delay_prob, wind_mag, wind_dir, repetition = args
        # If strategic is Random Alt, we load a standard scenario
        if strategic == 'RALT':
            base_scen = self.scenario_path + f'Standard/Flight_intention_{demand}_{repetition}.scn'
        # Else, we need to load a 1, 2 or 4 dof one
        elif strategic in ['1D', '2D', '4D']:
            base_scen = self.scenario_path + f'{strategic}/Flight_intention_{demand}_{repetition}.scn'
        # If RTA, we load the 4DoF
        elif strategic == '4DRTA':
            base_scen = self.scenario_path + f'4D/Flight_intention_{demand}_{repetition}.scn'
        else:
            # weird
            print(f'Strategic {strategic} is not implemented.')
            return False
            
        # We build the starting commands in function of the options
        scen_text = ''
        # scen_text += '00:00:00>PAN 48.20864707791969, 16.369901379005423\n'
        # scen_text += '00:00:00>ZOOM 20\n'
        scen_text += f'00:00:00>SEED {repetition}\n'
        scen_text += '00:00:00>ASAS ON\n'
        if tactical == 'SB':
            scen_text += '00:00:00>RESO M22CR\n'
        scen_text += '00:00:00>CDMETHOD M22CD\n'
        scen_text += '00:00:00>IMPL WINDSIM M22WIND\n'
        scen_text += f'00:00:00>SETM22WIND {wind_mag} {wind_dir}\n'
        scen_text += f'00:00:00>SETM22DELAY {delay_mag} {delay_prob}\n'
        scen_text += '00:00:00>STARTLOGS\n'
        if strategic == '4DRTA':
            scen_text += '00:00:00>ENABLERTA\n'
        scen_text += '00:00:00>SCHEDULE 02:00:00 DELETEALL\n'
        scen_text += '00:00:00>SCHEDULE 02:00:01 HOLD\n'
        scen_text += '00:00:00.00>FF\n\n'
        
        # Open base scen
        with open(base_scen) as f:
            base_scen_text = f.read()
            
        # Open final scenario file
        out_scen_name = f'M22_{demand}_{tactical}_{strategic}_{delay_mag}_{delay_prob}_{wind_dir}_{wind_mag}_{repetition}.scn'
        with open(self.output_path + out_scen_name, 'w') as f:
            f.write(scen_text)
            f.write(base_scen_text)
        return True
        
    @staticmethod
    def natural_sort(l): 
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(l, key=alphanum_key)
    

def main():
    maker = ScenarioMaker()
    # Create strategic scenarios
    maker.create_experiment_scenarios()
    return

if __name__ == "__main__":
    main()