import os
import pickle
import argparse

with open('site_list.pkl', 'rb') as f:
    site_list = pickle.load(f)

with open('site_cmd_list.pkl', 'rb') as f:
    site_cmd_list = pickle.load(f)


# main function
if __name__ == '__main__':

    # cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=int)

    args = parser.parse_args()

    id = args.id

    site_name = site_list[id]
    
    #_site_list = ['CA-ER1','CA-Na1','US-DFK','US-Me2',
    #'US-Pnp','US-Rwf','US-UMB', 'US-Ho1','US-Ho3']
    
    #_site_name = _site_list[id]
	
    site_cmd_line = site_cmd_list[site_name]
    print(site_cmd_line)

    os.system(site_cmd_line)
