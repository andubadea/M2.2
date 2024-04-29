# Simple script to create a batch file
import os
filename5 = 'Vienna/M2.2/batch5.scn'
filename6 = 'Vienna/M2.2/batch6.scn'
filename7 = 'Vienna/M2.2/batch7.scn'
    
all_scens = [x for x in os.listdir('Vienna/M2.2') if ('batch' not in x) and ('DS' not in x)]
to_include = all_scens

# Split into two
len_batch = int(len(all_scens)/4)
batch5_scens = to_include[:len_batch]
batch6_scens = to_include[len_batch:len_batch*2]
#batch7_scens = to_include[len_batch*2:]
batch5_scens = to_include[len_batch*2:len_batch*3]
batch6_scens = to_include[len_batch*3:]


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
        
# with open(filename7, 'w') as f:
#     for scenario in batch7_scens:
#         scen_name = scenario.replace('.scn','')
        
#         to_write = f'00:00:00.00>SCEN {scen_name}\n' + \
#                     f'00:00:00.00>PCALL M2.2/{scenario}\n' + \
#                     '00:00:00.00>FF\n\n'
                    
#         f.write(to_write)
