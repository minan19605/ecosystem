import os
import glob
import pickle

src_dir = './output/'
qcv_dir = '/01_qc_visual/qcv_files/'

for sub_dir_list in os.walk(src_dir):
    break

_tmp = sub_dir_list[1].copy()
_tmp.sort()
with open('site_list.pkl', 'wb') as f:  # open a text file
    pickle.dump(_tmp, f)

msi_txt = 'python runoneflux.py all "../ameri_flux/output/" {site_name} "{site_name}" {qcv_start_year} {qcv_end_year} \
-l fluxnet_pipeline_{site_name}.log --mcr ~/bin/MATLAB/MATLAB_Runtime/v94/ --recint hh \
--era-fy 1980 --era-ly 2021'

site_cmds = dict()

for sub_dir in _tmp:
    site_name = sub_dir
    
    full_qcv_dir = src_dir + site_name + qcv_dir
    qcv_file_list = glob.glob(full_qcv_dir + '*.csv')
    years = []
    for qcv_file in qcv_file_list:
        qcv_name = os.path.basename(qcv_file)
        year = qcv_name.split('.')[0][-4:]
        years.append(int(year))
        
    years.sort()
    last_year = years[-1]
    if last_year > 2021:
        last_year = 2021
    
    first_year = years[0]
    #cmd_line = cmd_txt.format(site_name=site_name, qcv_start_year = first_year, qcv_end_year=last_year)
    cmd_line = msi_txt.format(site_name=site_name, qcv_start_year = first_year, qcv_end_year=last_year)
    site_cmds[site_name] = cmd_line

print("Done!")

with open('site_cmd_list.pkl', 'wb') as f:  # open a text file
    pickle.dump(site_cmds, f) 