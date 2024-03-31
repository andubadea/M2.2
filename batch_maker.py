# Simple script to create a batch file
import os
filename = 'Vienna/M2.2/m22batch.scn'

with open(filename, 'w') as f:
    for scenario in os.listdir('Vienna/M2.2'):
        if "m22batch" in scenario:
            continue
        scen_name = scenario.replace('.scn','')
        
        to_write = f'00:00:00.00>SCEN {scen_name}\n' + \
                    f'00:00:00.00>PCALL M2.2/{scenario}\n' + \
                    '00:00:00.00>FF\n\n'
                    
        f.write(to_write)
