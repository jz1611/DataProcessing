'''
    This script was used to read, clip, and aggregate data from https://www.sciencebase.gov/catalog/item/5b96c2f9e4b0702d0e826f6d
    and https://www.sciencebase.gov/catalog/item/59d3c73de4b05fe04cc3d1d1
    These files are in GeoTIFF format.
'''

# Import libraries
import rioxarray # Used for reading in rasters
import geopandas as gpd # Spatial analysis
import pandas as pd # Create and export DataFrames
import os # File reading

# Original dictionary from https://www.sciencebase.gov/catalog/item/5b96c2f9e4b0702d0e826f6d
# Used to apply classes to values

# lc_dict = {
#     1: 'Water',
#     2: 'Developed',
#     3: 'Mechanically Disturbed National Forests',
#     4: 'Mechanically Disturbed Other Public Lands',
#     5: 'Mechanically Disturbed Private',
#     6: 'Mining',
#     7: 'Barren',
#     8: 'Deciduous Forest',
#     9: 'Evergreen Forest',
#     10: 'Mixed Forest',
#     11: 'Grassland',
#     12: 'Shrubland',
#     13: 'Cropland',
#     14: 'Hay/Pasture Land',
#     15: 'Herbaceous Wetland',
#     16: 'Woody Wetland',
#     17: 'Perennial Ice/Snow'
# }

# User defined new classification dictionary
# Barren, Water, Developed, Everything Else
    
lc_reclass = {
    1: 'Water',
    2: 'Developed',
    3: 'Other',
    4: 'Other',
    5: 'Other',
    6: 'Other',
    7: 'Barren',
    8: 'Other',
    9: 'Other',
    10: 'Other',
    11: 'Other',
    12: 'Other',
    13: 'Other',
    14: 'Other',
    15: 'Other',
    16: 'Other',
    17: 'Other'
}

# Raster cell size from MetaData
cell_size = 250 # 250 meters

# Define clipping file and extent - Shapefile was Dissolved and reprojected in ArcGIS Pro ahead of time to match data set
sf_path = './Data/Dissolve_Project.shp' # Shapefile for clip
clip_sf = gpd.read_file(sf_path)
minx = clip_sf.bounds['minx'].values[0]
maxx = clip_sf.bounds['maxx'].values[0]
miny = clip_sf.bounds['miny'].values[0]
maxy = clip_sf.bounds['maxy'].values[0]

# Directory where data files are located
data_dir = './Data/Historical Baseline'

# Initialize DataFrame for final results
final = pd.DataFrame()

# Loop through all files in data directory
for filename in os.listdir(data_dir):
    # Only work with GeoTIFF files
    if filename.endswith('.tif'):
        filepath = os.path.join(data_dir, filename)
        
        # Open .tif with xarray as DataArray
        with rioxarray.open_rasterio(filepath) as rda:
            # Reduce DataArray
            reduced_da = rda[0].sel(x=slice(minx, maxx)).sel(y=slice(maxy, miny))
            # Convert DataArray to pandas DataFrame; x, y become index
            rdf = reduced_da.to_dataframe(name='value').reset_index(level=['x', 'y']).drop(columns=['band', 'spatial_ref'])
            # Conver DataFrame to GeoDataFrame; x,y become geometry; Projection is assigned CRS from DataArray
            rgdf = gpd.GeoDataFrame(rdf[['value']], geometry=gpd.points_from_xy(rdf.x, rdf.y), crs=reduced_da.spatial_ref.attrs["crs_wkt"])
            # Clip GeoDataFrame to shapefile
            rgdf_clip = gpd.clip(rgdf, clip_sf).copy()
            # Add land cover column to DataFrame based on cell value refereced to dictionary
            rgdf_clip['LC'] = [lc_reclass[val] for val in rgdf_clip['value'].tolist()]
            # Initialize new DataFrame
            data = pd.DataFrame({
                'count': rgdf_clip['LC'].value_counts().values,
                'LC': rgdf_clip['LC'].value_counts().index 
            })
            # Calculate areas and coverages and assign values to DataFrame
            areas = [cells * cell_size * cell_size for cells in data['count'].tolist()]
            coverages = [count / data['count'].sum() * 100 for count in data['count'].tolist()]
            data['Area_m2'] = areas
            data['Coverage'] = coverages
            date = filepath[-8:-4]
            data['Year'] = date
            # Add data to results DataFrame, drop unnecessary columns and set new index
            result = data.drop(columns=['Area_m2', 'count']).pivot(index='Year', columns='LC')
            final = pd.concat([final, result])

# Write final DataFrame to CSV
final.to_csv('./{}_results.csv'.format(os.path.split(data_dir)[1]), mode='w', index=True, header=True)