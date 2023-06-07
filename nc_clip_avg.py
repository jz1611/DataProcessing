'''
    This script was made specifically for reading NetCDF files from https://cida.usgs.gov/thredds/catalog/CA-BCM-2014/data/future/catalog.html
    It can be modified for other NetCDF files or sources with minimum adjustments.
    Data is in single month increments.
'''

# Import libraries
import xarray as xr # Manage netCDF files
import numpy as np # Hand NumPy array math
import geopandas as gpd # Spatial analysis
import time # Calculate processing times
import pandas as pd # Create and export DataFrames
import os # File/directory checking and creation

total_start_time = time.time() # Timer for entire script

# Create results folder in current directory if one does not exist
if not os.path.exists("./results"):
    os.mkdir("./results")

# Define other variables
data_dir = './data' # Source directory for data files
start_date = '2020-10-01'
end_date = '2050-09-01'
sf_path = './Watersheds/WestForks_DeepCreekModified_Subbasins_v3_NoLakes_CA_Albers.shp' # Shapefile for clip
clip_sf = gpd.read_file(sf_path) # Shapefile for clipping

# Define bounds to reduce NetCDF file, 270 adds single cell buffer (270m cell size)
xmin = clip_sf.bounds.min()['minx'] - 270
ymin = clip_sf.bounds.min()['miny'] - 270
xmax = clip_sf.bounds.max()['maxx'] + 270
ymax = clip_sf.bounds.max()['maxy'] + 270

# Loop through all source files and determine unique variable names - this may be unique to specific NetCDF files being used
for filename in os.listdir(data_dir):
    print('Beginning {} processing...'.format(filename))
    file_start_time = time.time()
    nc_path = os.path.join(data_dir, filename)
    ds = xr.open_dataset(nc_path)
    for varname, da in ds.data_vars.items():
        if da.name != 'albers_conical_equal_area':
            target_variable = da.name

    # Reduce NetCDF to spatial bounds and convert to GeoDataFrame
    print("Converting NetCDF to DataFrame...")
    area_focus_ds = ds.sel(x=slice(xmin, xmax)).sel(y=slice(ymin, ymax))
    df = area_focus_ds[target_variable].to_dataframe().reset_index()
    gdf = gpd.GeoDataFrame(df[['time', target_variable]], geometry=gpd.points_from_xy(df.x, df.y))

    # Create results DataFrame that will be written to file
    results = pd.DataFrame(data={'date': [], 'watershed': [], '{}'.format(target_variable): []})

    # Loop through each polygon in shapefile
    for i in range(0, len(clip_sf)):
        ws_name = clip_sf.Segment[i] # "Segment" is specific to this file; "Name" in others...
        print('Clipping GDF to watershed {}...'.format(ws_name))
        # Get polygon geometry and clip GDF
        polygon = clip_sf.geometry.iloc[i]
        gdf_clip = gpd.clip(gdf, polygon).sort_values('time')
        date_mask = (gdf_clip['time'] >= start_date) & (gdf_clip['time'] <= end_date)
        gdf_clip = gdf_clip.loc[date_mask]
        # Loop through each date for Clip and calculate average, store average in DataFrame
        print('Calculating averages...')
        for date in gdf_clip.time.unique():
            df = gdf_clip.loc[gdf_clip['time'] == date]
            avg = np.nanmean(df[target_variable])
            results.loc[len(results.index)] = [date, ws_name, avg]

    # Pivot DataFrame to desired rows/columns
    final = results.pivot(index='date', columns='watershed')

    # Write DataFrame to CSV file
    print('Writing to file...')
    if not os.path.exists("./results/{}_results.csv".format(target_variable)):
        final.to_csv('./results/{}_results.csv'.format(target_variable), mode='w', index=True, header=True)
        
    print("\tCompleted {file}: {time:.2f} s".format(file=filename, time=(time.time() - file_start_time)))
        
print("\tTotal runtime: {time:.2f} s".format(time=(time.time() - total_start_time)))