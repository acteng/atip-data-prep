import geopandas as gpd
import pandas as pd
import numpy as np
import subprocess
import datetime
import os

#Code from https://github.com/dabreegster/popgetter/tree/main
def _last_update(file_path):
    """
    Returns the date and time of the last update to the file at `file_path`.
    """
    if not os.path.exists(file_path):
        return None
    last_update = os.path.getmtime(file_path)
    return datetime.datetime.fromtimestamp(last_update)


#Code from https://github.com/dabreegster/popgetter/tree/main
def download_from_arcgis_online(serviceItemId, output_file, layer = 0,force=False):
    """
    Downloads data from ArcGIS Online and saves it to a file (`output_file`). This function can only download data that is available to anonymous users.
    The data will only be downloaded if the output file does not exist, or if the data on ArcGIS Online has been updated since the output file was last updated. Use `force=True` will cause the data to be re-downloaded if it an uptodate file exists locally.
    """
    try:
        from arcgis.gis import GIS
    except ImportError:
        print("Unable to import `arcgis`. Please install the `arcgis` package, using the command `pip install requirements-non-foss.txt.")
        return
    
    # Anonymous access to ArcGIS Online
    gis = GIS()

    # Get the `Item`, then, `FeatureLayer` then 'FeatureSet`:
    agol_item = gis.content.get(serviceItemId)
    print(f"Got item: {agol_item}")
    print(f"item metadata: {agol_item.metadata}")

    agol_layer = agol_item.layers[layer]

    # Get the last edit datetime for the layer
    # print(f"Got layer: {agol_layer.properties}")
    lyr_props = agol_layer.properties
    # Epoch time in milliseconds - convert to datetime
    lyr_last_edit = lyr_props.get("editingInfo", {}).get("lastEditDate", None)
    if lyr_last_edit:
        lyr_last_edit = datetime.datetime.fromtimestamp(lyr_last_edit/1000)

    print(f"last_edit: {lyr_last_edit}")

    # If the output file exists, check the last edit time
    output_last_edit = _last_update(output_file)

    if not force and output_last_edit and lyr_last_edit and output_last_edit > lyr_last_edit:
        print(f"Output file is up-to-date: {output_file}")
        return
    
    print(f"Output file is out-of-date: {output_file}")

    agol_feature_set = agol_layer.query()
    print(f"Got feature set: {len(agol_feature_set)}")
    
    # Write to geojson file
    with open(output_file, "w") as f:
        f.write(agol_feature_set.to_geojson)

    print("Done")

#Code from https://github.com/dabreegster/popgetter/tree/main
def download_vehicle_ownership(census_url, working_dir):
    print("Retrieving Vehicle Ownership Census Data")
    result = subprocess.check_call(["wget", "-N", census_url], cwd=working_dir)
    print(f"result = {result}")

#%% Layers

def getCarOwnershipLayer(WORKING_DIR,output_areas_serviceItemID,output_areas_geojson_path,carOwnerFile,output_file):
    
    """
    Reads in OA geometries data and car ownership, created bandings at OA level and outputs as geoJson.
    """
    
    print('----------')
    print('Getting data')
        
    #Get Car Ownership Census Data
    
    #Below code not working - cannot find file (althugh URL work in a web browser)
    #To work around download file from below url and save in WORKING_DIR
    
    # CENSUS_URL = "https://static.ons.gov.uk/datasets/a20437fb-ae7f-439b-bc91-de261335038b/TS045-2021-3-filtered-2023-03-13T16:49:47Z.csv"
    # download_vehicle_ownership(CENSUS_URL, WORKING_DIR)
    
    #Read data in
    #OAs shapefile as geopandas dataframe
    oas = gpd.read_file(output_areas_geojson_path)
    print('OA Geometry Read In')
    
    
    #Car ownership data
    carsRaw = pd.read_csv('{}/{}'.format(WORKING_DIR,carOwnerFile))
    print('Car Ownership Read In')
    
    #Cars
    
    #Empty dataframe to capture data
    cars = pd.DataFrame(columns = ['0 Cars', '1 Car', '2 Car', '3+ Cars', 'Total'], index = carsRaw['Output Areas Code'].value_counts().index)
    
    #Split data from cars ownership across different columns
    cars['0 Cars'] = carsRaw[carsRaw['Car or van availability (5 categories) Code'] == 0][['Output Areas Code','Observation']].set_index('Output Areas Code')
    cars['1 Car'] = carsRaw[carsRaw['Car or van availability (5 categories) Code'] == 1][['Output Areas Code','Observation']].set_index('Output Areas Code')
    cars['2 Car'] = carsRaw[carsRaw['Car or van availability (5 categories) Code'] == 2][['Output Areas Code','Observation']].set_index('Output Areas Code')
    cars['3+ Cars'] = carsRaw[carsRaw['Car or van availability (5 categories) Code'] == 3][['Output Areas Code','Observation']].set_index('Output Areas Code')
    #Total number of cars per OA
    cars['Total'] = carsRaw.groupby('Output Areas Code').sum()['Observation']
    #Percentage of households with a car
    cars['Pcnt HH With Car'] = 1 - (cars['0 Cars'] / cars['Total'])
    #Weighted average cars per hh
    cars['Avg Cars per HH'] = (cars['1 Car'] + (cars['2 Car'] * 2) + (cars['3+ Cars'] * 3)) / cars['Total']
    
    print('Bandings formed')
    
    #Banding Percent HH with Car
    
    conditionsPcHH = [
    (cars['Pcnt HH With Car'] <= 0.4),
    (cars['Pcnt HH With Car'] <= 0.6),
    (cars['Pcnt HH With Car'] <= 0.7),
    (cars['Pcnt HH With Car'] <= 0.8),
    (cars['Pcnt HH With Car'] <= 0.85),
    (cars['Pcnt HH With Car'] <= 0.9),
    (cars['Pcnt HH With Car'] <= 0.95),
    (cars['Pcnt HH With Car'] <= 1)]
    
    choicesPcHH = [1,2,3,4,5,6,7,8]
    cars['Pcnt HH With Car Bands'] = np.select(conditionsPcHH, choicesPcHH, default=99)
    print(cars['Pcnt HH With Car Bands'].value_counts())
    
    # Banding weighted average cars per HH
    conditionsNumCars = [
    (cars['Avg Cars per HH'] <= 0.5),
    (cars['Avg Cars per HH'] <= 0.75),
    (cars['Avg Cars per HH'] <= 1),
    (cars['Avg Cars per HH'] <= 1.25),
    (cars['Avg Cars per HH'] <= 1.5),
    (cars['Avg Cars per HH'] <= 1.75)]
    
    choicesNumCars = [1,2,3,4,5,6]
    cars['Avg Cars per HH Bands'] = np.select(conditionsNumCars, choicesNumCars, default=7)
    print(cars['Avg Cars per HH Bands'].value_counts())
    
    # Output data
    print('Outputting Data')
    output_data = oas[['OA21CD','geometry']].merge(cars, left_on = 'OA21CD', right_index = True)
    output_data.to_file('{}/{}'.format(WORKING_DIR,output_file), driver="GeoJSON")
    print('Car Ownership Layer Output')
    print('----------')


def getPopDensityLayer(oa_pop_path,output_areas_geojson_path,pop_dens_output_file):

    """
    Reads in OA geometries data and population distribution, calculates population densite and splits into deciles, then outputs as geoJson.
    """    

    #Instruction to get data:
    #From https://www.nomisweb.co.uk/sources/census_2021_bulk download TS001.csv and extract into working directory
    
    #Read in OA Population File
    oa_pop= pd.read_csv(oa_pop_path)
    print('----------')
    print('Population data read in')
    
    #Read in OA Geometry
    oas = gpd.read_file(output_areas_geojson_path)
    print('OA geometry data read in')
    
    #Merge geometry and population data on OA identifier
    oas = oas.merge(oa_pop, left_on = 'OA21CD', right_on = 'geography')
    #Create Population Density Field
    oas['pop_density'] = (oas['Residence type: Total; measures: Value'] / oas['Shape__Area']) * 1000
    #Split into deciles
    oas['pop_density_deciles'] = pd.qcut(oas['pop_density'], q=10, labels=False, duplicates='drop')
    
    print(oas['pop_density_deciles'].value_counts())
    
    #Output File
    print('Outputting data')
    oas.to_file('{}/{}'.format(WORKING_DIR,pop_dens_output_file), driver="GeoJSON")
    print('Data output')
    print('----------')

def getEmpDensityLayer(businesses_csv_file,lsoa_geojson_path,emp_dens_output_file):

    """
    Reads in LSOA geometries data and business data (with copmany size in employees), calculates employement density at LSOA level and splits into deciles, then outputs as geoJson.
    """    

    print('----------')
        
    businesses = pd.read_csv(businesses_csv_file)
    number_jobs_lsoa = businesses.groupby('LSOA11CD').sum()['size']    
    print('Businesses data read')
    
    lsoas = gpd.read_file(lsoa_geojson_path)
    print('LSOAs data read')
    
    lsoas['area'] = lsoas['geometry'].area / 1000
    lsoas = lsoas.merge(number_jobs_lsoa, left_on = 'LSOA21CD', right_index = True)
    lsoas['emp_density'] = lsoas['size'] / lsoas['area']
    lsoas['emp_density_deciles'] = pd.qcut(lsoas['emp_density'], q=10, labels=False, duplicates='drop')
    print('Employment density calculated')
    print(lsoas['emp_density_deciles'].value_counts())
    
    print('Outputting data')    
    lsoas.to_file('{}/{}'.format(WORKING_DIR,emp_dens_output_file), driver="GeoJSON")
    print('Data output')
    print('----------')

#%% Output Layers

#General Parameters
WORKING_DIR = "data"
output_areas_serviceItemID = "6c6743e1e4b444f6afcab9d9588f5d8f"
output_areas_geojson_path = f"{WORKING_DIR}/oa_from_agol.geojson"
lsoa_geojson_path = f"{WORKING_DIR}/LSOA_Dec_2021_Boundaries_Generalised_Clipped_EW_BGC_2022_5605507071095448309.geojson"

#Car layer Parameters
carOwnerFile = 'TS045-2021-3-filtered-2023-03-13T16 49 47Z.csv'
cars_output_file = 'outputs/car-ownership-layer.geojson'

#IMD Parameters
IMD_serviceItemID = "4ad3e5a10872455eaa67ce4e663d0d01"
IMD_geojson_path = f"{WORKING_DIR}/outputs/imd-2019.geojson"

#Pop Density Parameters
oa_pop_path = "{}/census2021-ts001/census2021-ts001-oa.csv".format(WORKING_DIR)
pop_dens_output_file = 'outputs/pop-density-layer.geojson'

#Emp
businesses_csv_file = "{}/businessRegistry.csv".format(WORKING_DIR)
emp_dens_output_file = 'outputs/emp-density-layer.geojson'

#%% Download OAs File

#Get OA geometries
download_from_arcgis_online(output_areas_serviceItemID, output_areas_geojson_path, force=False)

#%% Get LSOA geometries

#from https://geoportal.statistics.gov.uk/datasets/766da1380a3544c5a7ca9131dfd4acb6/explore download geojson and save to working directory

#%% Car Ownership
getCarOwnershipLayer(WORKING_DIR,output_areas_serviceItemID,output_areas_geojson_path,carOwnerFile,cars_output_file)

#%% IMD
download_from_arcgis_online(IMD_serviceItemID, IMD_geojson_path, force=True)

#%% Population Density
getPopDensityLayer(oa_pop_path,output_areas_geojson_path,pop_dens_output_file)

#%% Employment Density

getEmpDensityLayer(businesses_csv_file,lsoa_geojson_path,emp_dens_output_file)