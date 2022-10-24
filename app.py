import streamlit as st
import geopandas as gpd
import find_lai as f
import matplotlib.pyplot as plt
import pandas as pd
import os
from zipfile import ZipFile



st.set_page_config(page_icon="🌿", page_title="Nitrogen Tool")
st.title("Nitrogen Tool")
st.write(f'Estimate Your Field Need of Nitrogen By uploading your Geojson')


uploaded_file = st.file_uploader("", type='geojson', key="1")

agree = st.checkbox('Use Demo Geojson')
if agree:
    st.write('Great!')

if (uploaded_file is not None) or (agree):
    if agree:
        gdf = gpd.read_file('MATO.geojson')
    else:
        file_container = st.expander("Check your uploaded .geojson")
        gdf = gpd.read_file(uploaded_file)
        uploaded_file.seek(0)
        file_container.write(gdf)

else:

    st.stop()


lai = f.get_lai(gdf, '2022-02-06', save=True)[0]
gdf_lai = f.get_gdf('9c35ea71639b7bae5c53649a5624846c/response.tiff', gdf)
gdf_lai, km = f.get_clustered(gdf_lai)
gdf_lai = gdf_lai.copy(deep=True)

nitrogen_precent_urea   = 0.46
nitrogen_precent_dap    = 0.18
col1, col2, col3, col4= st.columns((1,1,1,1))

with col1:
    target_yield    = st.number_input("Enter Target Yield: (q/ha)"  , value=98.84)
with col2:
    expected_yield  = st.number_input("Enter Expected Yield: (q/ha)", value=74.13)
with col3:
    urea_usage  = st.number_input(f"Enter Urea ({nitrogen_precent_urea*100}% Nitrogen) Usage: (kg/acre)  " , value=100)
with col4:
    dap_usage    = st.number_input(f"Enter Dap ({nitrogen_precent_dap*100}% Nitrogen)  Usage: (kg/acre)"  , value=25)
col5, col6, col7= st.columns((1,1,1))
with col5:
    nitrogen_soil_mineralisation  = st.number_input(f"Enter Nitrogen Mineralisation in Soil: (kg/ha)"  , value=10)
with col6:
    biomass_cofficient      = st.number_input("Crop Specific Cofficient to convert LAI into biomass"    , value=7)
with col7:
    nitrogen_absorption_coefficient  = st.number_input("Crop Specific Nitrogen Absorption Coefficient"  , value=17)
nitrogen_usage_kg_per_acre = (urea_usage * nitrogen_precent_urea) + (dap_usage * nitrogen_precent_dap)
nitrogen_usage_kg_per_ha   = nitrogen_usage_kg_per_acre * 2.471
nitrogen_per_ton_for_expected_yield = nitrogen_usage_kg_per_ha / expected_yield 
nitrogen_need_per_ha_for_target_yield = target_yield * nitrogen_per_ton_for_expected_yield 
lai_clusters = km.cluster_centers_
lai_to_nitrogen_absortion_map = {}
for lai_val in lai_clusters:
    lai_val = lai_val.item()
    nitrogen_absorbed = lai_val * biomass_cofficient * nitrogen_absorption_coefficient
    lai_to_nitrogen_absortion_map[lai_val] = nitrogen_absorbed
lai_to_nitrogen_df = pd.DataFrame(lai_to_nitrogen_absortion_map.items(), columns=['LAI', 'NitrogenAbsorbed'])
nitrogen_recommendations = []
for n_absor in lai_to_nitrogen_df['NitrogenAbsorbed']:
    nitrogen_required = nitrogen_need_per_ha_for_target_yield
    nitrogen_supplied = n_absor+nitrogen_soil_mineralisation
    nitrogen_need_to_get_required = nitrogen_required - nitrogen_supplied
    nitrogen_recommendations.append(nitrogen_need_to_get_required)
lai_to_nitrogen_df['Additional Nitrogen Recommendations'] = nitrogen_recommendations
m={}
for i,r in lai_to_nitrogen_df.iterrows():
    lai_current = r['LAI']
    rec_current = r['Additional Nitrogen Recommendations']
    m[lai_current] = rec_current
gdf_lai['NitrogenRecommendation'] = [m[i] for i in gdf_lai['LAI_Clusters']]


st.info(f'The Nitrogen Usage is {nitrogen_usage_kg_per_ha:.2f} (kg per ha)')
st.info(f'The Nitrogen Used for for the Expected yield is {nitrogen_per_ton_for_expected_yield:.2f} (KG of Nitrogen Per One Ton of Sugarecane)')
st.info(f'The Nitrogen Need for the Target yield is {nitrogen_need_per_ha_for_target_yield:.2f} (KG of Nitrogen Per One ha)')
fig, ax = plt.subplots(1, 1 , figsize=(5,5))
gdf_lai.plot(column='LAI', ax=ax, legend=True)
st.pyplot(fig)

fig, ax = plt.subplots(1, 1)
gdf_lai.plot(column='NitrogenRecommendation', ax=ax, legend=True,  cmap='RdBu')
st.pyplot(fig)


shapefilename = "gdf_lai"
extension = 'shp'
gdf_lai.to_file(f'{shapefilename}.{extension}')
path = './'
files = []
for i in os.listdir(path):
    if os.path.isfile(os.path.join(path,i)):
        if i[0:len(shapefilename)] == shapefilename:
            files.append(i)


zipFileName = 'Nitrogen.zip'
zipObj = ZipFile(zipFileName, 'w')
for file in files:
    zipObj.write(file)
zipObj.close()

with open(zipFileName, 'rb') as f:
    st.download_button('Download as ShapeFile', f,file_name=zipFileName)
