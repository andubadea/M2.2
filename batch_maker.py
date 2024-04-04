# Simple script to create a batch file
import os
filename5 = 'Vienna/M2.2/m22batch5.scn'
filename6 = 'Vienna/M2.2/m22batch6.scn'

existing = [x for x in os.listdir('tmp') if 'REGLOG' in x]

existing_set = set()

for filename in existing:
    # Check if reglog is complete
    with open(f'tmp/{filename}', 'r') as f:
        lines = f.readlines()
        if '7200' in lines[-2]:
            split_file = filename.split('_')
            scen_name = '_'.join(split_file[1:10]) + '.scn'
            existing_set.add(scen_name)
            continue
        else:
            # Delete it
            os.remove(f'tmp/{filename}')
            os.remove(f"tmp/{filename.replace('REGLOG', 'LOSLOG')}")
            os.remove(f"tmp/{filename.replace('REGLOG', 'FLSTLOG')}")
            os.remove(f"tmp/{filename.replace('REGLOG', 'CONFLOG')}")
    
all_scens = [x for x in os.listdir('Vienna/M2.2') if ('m22batch' not in x) and ('DS' not in x)]
    
to_include = [scenario for scenario in all_scens if (scenario not in existing_set) and ('_2D_' not in scenario) and ('_240_' not in scenario)]

# Split into two
len5 = int(len(to_include)/2)
batch5_scens = to_include[:len5]
batch6_scens = to_include[len5:]

print(len5)



with open(filename5, 'w') as f:
    for scenario in batch5_scens:
        scen_name = scenario.replace('.scn','')
        
        to_write = f'00:00:00.00>SCEN {scen_name}\n' + \
                    f'00:00:00.00>PCALL M2.2/{scenario}\n' + \
                    '00:00:00.00>FF\n\n'
                    
        f.write(to_write)
        
with open(filename6, 'w') as f:
    for scenario in batch6_scens:
        scen_name = scenario.replace('.scn','')
        
        to_write = f'00:00:00.00>SCEN {scen_name}\n' + \
                    f'00:00:00.00>PCALL M2.2/{scenario}\n' + \
                    '00:00:00.00>FF\n\n'
                    
        f.write(to_write)
