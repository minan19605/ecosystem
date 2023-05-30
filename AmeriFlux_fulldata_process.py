import os
import glob
import numpy as np
import pandas as pd
#import json
import datetime
from zipfile import ZipFile

def create_day(row):
    _str = row['TIMESTAMP_START']
    return _str[:-4]

# calculate humidity
ALTI = 362  # This is a fixed value
def calculate_H(row):
    if row['RH'] < 0:
        humidity = ConvertRH2Humidty(row['TA_F'],row['RH2'],ALTI)
    else:
        humidity = ConvertRH2Humidty(row['TA_F'],row['RH'],ALTI)

    return humidity


def VPD2RH(Ta,VPD):
    #
    #ea = 0.611*np.exp(17.502*Td/(Td+240.97))
    es = 0.611*np.exp(17.502*Ta/(Ta+240.97))*10
    ea = es-VPD
    RH = ea*100/es
    RH[RH<0] = 0
    RH[RH>100] = 100    
    return RH

def ConvertRH2Humidty(Ta,RH,ALTI):
    #Ta, air temperature, C
    #Rh, relatively humidty, %
    #ALTI,altitude,m
    DWPTH=0.61*np.exp(5360.0*(3.661E-03-1.0/(273.15+Ta)))*max(0.0,min(100.0,RH))*0.01 #humidity
    TKA=Ta+273.15
    VPS=0.61*np.exp(5360.0*(3.661E-03-1.0/TKA))*np.exp(-ALTI/7272.0)
    VPK=min(DWPTH,VPS)
    return VPK
    
ZNOON = 12.5
# RAND: SW_IN_F, J: hour,I:DOY
def ConvertSWDW(RADN,ALAT,ZNOON,J,I):
    # RAND: SW_IN_F
    # J: hour
    # I:DOY

    TWILGT=0.06976
    #
    RADN = RADN*0.0036
    TYSIN = 0
    for N in range(1,5):
        YAZI=3.1416*(2*N-1)/4.0
        YAGL=3.1416/4.0
        YSIN=np.sin(YAGL)
        TYSIN=TYSIN+YSIN

    # Note below code are duplicate for DECDAY and below lines
    if ALAT > 0.0:
        XI=173
    else:
        XI=356
    DECDAY=XI+100
    DECLIN=np.sin((DECDAY*0.9863)*1.7453E-02)*(-23.47)
    AZI=np.sin(ALAT*1.7453E-02)*np.sin(DECLIN*1.7453E-02)
    DEC=np.cos(ALAT*1.7453E-02)*np.cos(DECLIN*1.7453E-02)
    
    XI=I
    if I==366:
        XI=365.5
    DECDAY=XI+100
    DECLIN=np.sin((DECDAY*0.9863)*1.7453E-02)*(-23.47)
    AZI=np.sin(ALAT*1.7453E-02)*np.sin(DECLIN*1.7453E-02)
    DEC=np.cos(ALAT*1.7453E-02)*np.cos(DECLIN*1.7453E-02)    
    
    #
    SSIN=max(0.0,AZI+DEC*np.cos(0.2618*(ZNOON-(J-0.5))))
    #
    if RADN <=0:
        SSIN = 0
    if SSIN <= TWILGT*-1:
        RADN = 0
        
    if SSIN > 0:
        RADX=4.896*max(0.0,SSIN)    
        RADN = min(RADX,RADN)
        #DIRECT VS DIFFUSE RADIATION IN SOLAR OR SKY BEAMS
        RADZ=min(RADN,0.5*(RADX-RADN))
        RADS=(RADN-RADZ)/SSIN
        RADS=min(4.167,RADS)    
        RADY=RADZ/TYSIN        
        
        TRAD = RADS*SSIN+RADY*TYSIN
    else:
        TRAD = 0
    
    return TRAD

def ConvertWindSpeed(row):
    #WS, wind speed, m/s
    WS = row['WS_F']
    WINDH=WS*3600.0 #m/h
    UA = max(3600,WINDH)*0.001 #km/h
    return UA

def calculate_RAND_HH(row, ALAT):
    SW_IN_F = row['SW_IN_F']
    
    start_time = row['TIMESTAMP_START']
    year = int(start_time[:4])
    month = int(start_time[4:6])
    day_of_month = int(start_time[6:8])
    hour = int(start_time[8:10]) + 1   # hour is from 1 - 24
    day_of_year = datetime.datetime(int(year), int(month), int(day_of_month)).timetuple().tm_yday
    return ConvertSWDW(SW_IN_F,ALAT,ZNOON,hour,day_of_year)

# From daily data to generate QC parameter
_qc_param = ['TIMESTAMP','TA_F_QC','SW_IN_F_QC','VPD_F_QC','PA_F_QC','P_F_QC','WS_F_QC','NEE_VUT_REF_QC']
def process_daily_file(data, site_id, output_dir):
    # data: pandas Dataframe
    qc_data = data[_qc_param]
    file_name = output_dir + site_id + '_QC_values.csv'
    qc_data.to_csv(file_name, float_format='%.5f', index=False)
    print("Create daily QC file : ", file_name)


def process_hour_file(data, site_id, pd_site_param, output_dir):

    # Create day from Time stamp which format is YYYYMMDDHHXX
    data['day'] = data.apply (lambda row: create_day(row) , axis=1)

    #convert those parameter hourly value to a daily mean value
    _sel_pd = data[['day','GPP_NT_VUT_REF', 'GPP_DT_VUT_REF', 'RECO_NT_VUT_REF','RECO_DT_VUT_REF','NEE_VUT_REF']]
    _sel_pd_mean = _sel_pd.groupby(by = ['day']).mean().reset_index()
    day_of_year = _sel_pd_mean.copy()

    # process TA_F daily max and min value from half hour or hourly data
    _sel_pd = data[['day','TA_F']]
    _sel_taf_xx = _sel_pd.groupby(['day']).agg({'TA_F':['max','min']}).reset_index()
    day_of_year['TA_F_max'] = _sel_taf_xx[('TA_F', 'max')].copy()
    day_of_year['TA_F_min'] = _sel_taf_xx[('TA_F', 'min')].copy()

    # Process Humidity from RH, VPD_F and TA_F, then get per day's max and min humidity value
    RH2= VPD2RH(data['TA_F'].values, data['VPD_F'].values)
    data['RH2'] = RH2

    data['Humidity'] = data.apply (lambda row: calculate_H(row) , axis=1)
    _sel_pd = data[['day','Humidity']]
    _sel_H_xx = _sel_pd.groupby(['day']).agg({'Humidity':['max','min']}).reset_index()

    day_of_year['H_max'] = _sel_H_xx[('Humidity', 'max')].copy()
    day_of_year['H_min'] = _sel_H_xx[('Humidity', 'min')].copy()

    # Process SW_IN_F
    ALAT = pd_site_param[pd_site_param['site_id'] == site_id]['Latitude'].values[0] # get site Latitude


    data['RAND_HH'] = data.apply (lambda row: calculate_RAND_HH(row, ALAT) , axis=1)
    _sel_pd = data[['day','RAND_HH']]
    _sel_Rand_xx = _sel_pd.groupby(['day']).agg({'RAND_HH':'sum'}).reset_index()
    day_of_year['RAND'] = _sel_Rand_xx['RAND_HH']

    # Process wind speed
    data['WIND_HH'] = data.apply (lambda row: ConvertWindSpeed(row) , axis=1)
    _sel_pd = data[['day','WIND_HH']]
    _sel_Wind_xx = _sel_pd.groupby(['day']).agg({'WIND_HH':'sum'}).reset_index()
    day_of_year['WIND'] = _sel_Wind_xx['WIND_HH']

    # Process PRECN
    _sel_pd = data[['day','P_F']]
    _sel_P_xx = _sel_pd.groupby(['day']).agg({'P_F':'sum'}).reset_index()
    day_of_year['PRECN'] = _sel_P_xx['P_F']

    # Write to a CSV file for each site
    file_name = output_dir + site_id + '_day_values.csv'
    day_of_year.to_csv(file_name, float_format='%.5f', index=False)
    print("Create daily file: ", file_name)


if __name__ == "__main__":

    # Read site parameters
    site_info_file = 'AmeriFlux_siteinfo.csv'  #'all_sites_param.csv'
    pd_site_param =pd.read_csv(site_info_file)

    _root = './ameriFlux/' #'D:/Flux_net/'
    all_zip = glob.glob(_root + "*FLUXNET2015_FULLSET*.zip")
    
    output_dir = _root + 'daily_data/'

    suffix_len = len('_2009-2011_beta-5')

    # specifying the zip file name
    for file_name in all_zip:
        # opening the zip file in READ mode
        with ZipFile(file_name, 'r') as zip:
            # printing all the contents of the zip file
            #zip.printdir()
            file_list = zip.namelist()
            
            file_prefix = os.path.basename(file_name)[:-4]
            site_id = file_prefix.split('_')[1]

            file_name = output_dir + site_id + '_day_values.csv'
            if os.path.exists(file_name):
                continue

            hh_file = file_prefix[:-suffix_len]+ '_HH'+ file_prefix[-suffix_len:] + '.csv'  # Half Hour file
            hr_file = file_prefix[:-suffix_len]+ '_HR'+ file_prefix[-suffix_len:] + '.csv'  # Hourly file
            dd_file = file_prefix[:-suffix_len]+ '_DD'+ file_prefix[-suffix_len:] + '.csv'  # Daily file
            
            #dd_data = zip.read(dd_file)
            if dd_file in file_list:
                pd_data = pd.read_csv(zip.open(dd_file)) #, dtype={'TIMESTAMP':str}
                pd_data['TIMESTAMP'] = pd_data['TIMESTAMP'].apply(lambda x: x[2:-1])
                process_daily_file(pd_data,site_id, output_dir)
            
            hour_file = ''
            if hh_file in file_list :
                hour_file = hh_file
            elif hr_file in file_list :
                hour_file = hr_file

            if hour_file != '':
                data = pd.read_csv(zip.open(hour_file), dtype={'TIMESTAMP_START':str, 'TIMESTAMP_END':str})
                # Those files missing "RH"
                # FLX_CA-Man_FLUXNET2015_FULLSET_HH_1994-2008_1-4.csv
                # FLX_DE-RuR_FLUXNET2015_FULLSET_HH_2011-2014_1-4.csv
                # FLX_DE-RuS_FLUXNET2015_FULLSET_HH_2011-2014_1-4.csv
                #FLX_MY-PSO_FLUXNET2015_FULLSET_HH_2003-2009_1-4.csv

                if 'RH' not in data.columns:
                    data['RH'] = -9999
                data['TIMESTAMP_START'] = data['TIMESTAMP_START'].apply(lambda x: x[2:-1])
                data['TIMESTAMP_END'] = data['TIMESTAMP_END'].apply(lambda x: x[2:-1])
                process_hour_file(data, site_id, pd_site_param, output_dir)



    print('Done!')