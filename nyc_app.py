import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import os
import geopandas as gpd
from shapely.geometry import Polygon


# Load the data
data_path = '/Users/jaskiratkaur/Documents/HPC/elec-transit-y/data/ev_stations_v1.csv'
ev_data = pd.read_csv(data_path, low_memory=False)

# Load NYC Taxi data for pickups and drop-offs
data_do = pd.read_csv('/Users/jaskiratkaur/Documents/HPC/elec-transit-y/data/nyc_taxi_rides_2019_aggByDOandHour.csv')
data_pu = pd.read_csv('/Users/jaskiratkaur/Documents/HPC/elec-transit-y/data/nyc_taxi_rides_2019_aggByPUandHour.csv')

# Load taxi zone shapefile
base_dir = os.getcwd()
taxi_zone_shapefile_path = os.path.join(base_dir, 'data', 'zone_shape_files', 'taxi_zones.shp')
taxi_zones_gdf = gpd.read_file(taxi_zone_shapefile_path)

# Ensure the taxi zone GeoDataFrame has a consistent CRS
taxi_zones_gdf = taxi_zones_gdf.to_crs("EPSG:4326")

# Filter for New York City only
nyc_cities = ['New York', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
ev_data_nyc = ev_data[ev_data['city'].isin(nyc_cities)]

# Load the census tract shapefile
shapefile_path = os.path.join(base_dir, 'data', 'nyct2020_24b', 'nyct2020.shp')
gdf = gpd.read_file(shapefile_path)

# Clean up the GeoDataFrame (remove gibberish rows manually inspected in the CSV)
gdf = gdf[gdf['BoroName'].isin(['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'])]

# Ensure CTLabel and BoroCode are strings
gdf['CTLabel'] = gdf['CTLabel'].astype(str)
gdf['BoroCode'] = gdf['BoroCode'].astype(str)

# Format CTLabel to have two decimal places
gdf['CTLabel'] = gdf['CTLabel'].apply(lambda x: f"{float(x):.2f}")

# Create a "Key" column in gdf
gdf['Key'] = gdf['CTLabel'] + '-' + gdf['BoroCode']

# Change the area to km^2 instead of m^2
gdf['Shape_Area'] = gdf['Shape_Area'] / 10**6

# Read the NYC population csv
pop_df = pd.read_csv(os.path.join(base_dir, 'data', 'nyc_census_tract_population.csv'))

# Split the NAME column to 3 columns based on the comma separator
pop_df[['CTLabel', 'County', 'StateName']] = pop_df['NAME'].str.split(',', expand=True)
pop_df['County'] = pop_df['County'].str.strip()

# Create the county to borough mapping dictionary
county_borough_mapping = {
    "New York County": "Manhattan",
    "Kings County": "Brooklyn",
    "Bronx County": "Bronx",
    "Richmond County": "Staten Island",
    "Queens County": "Queens"
}

# Map the County to Borough
pop_df['Borough'] = pop_df['County'].map(county_borough_mapping)

# Check if 'Borough' column is created successfully
if 'Borough' in pop_df.columns:
    # BoroCode mapping
    borough_code_mapping = {
        "Manhattan": "1",
        "Brooklyn": "3",
        "Bronx": "2",
        "Queens": "4",
        "Staten Island": "5"
    }

    # Map Borough to BoroCode
    pop_df['BoroCode'] = pop_df['Borough'].map(borough_code_mapping)
else:
    raise KeyError("'Borough' column not found. Check the mapping step for errors.")

# Extract the numeric values from CTLabel using regex
pop_df['CTLabelNumeric'] = pop_df['CTLabel'].str.extract(r'(\d+\.\d+|\d+)')
pop_df['CTLabelNumeric'] = pd.to_numeric(pop_df['CTLabelNumeric'])
pop_df['CTLabelNumeric'] = pop_df['CTLabelNumeric'].apply(lambda x: f"{x:.2f}")

# Create a "Key" column in pop_df
pop_df['Key'] = pop_df['CTLabelNumeric'] + '-' + pop_df['BoroCode']

# Merge the GeoDataFrame and population DataFrame on the "Key" column
merged_gdf = gdf.merge(pop_df, on='Key', how='inner')

# Calculate population density and add it as a column
merged_gdf['Population_Density'] = merged_gdf['P1_001N'] / merged_gdf['Shape_Area']

# Function to create the population density map
def create_population_density_map():
    map_center = [40.7128, -74.0060]  # Center of NYC
    ev_map = folium.Map(location=map_center, zoom_start=10, tiles='cartodbpositron')

    # Add a white polygon to mask the whole world
    world_polygon = Polygon([[-180, 90], [-180, -90], [180, -90], [180, 90]])
    nyc_polygon = merged_gdf.unary_union

    # Set the CRS for both polygons
    world_gdf = gpd.GeoSeries([world_polygon], crs="EPSG:4326")
    nyc_gdf = gpd.GeoSeries([nyc_polygon], crs="EPSG:4326")

    # Create the mask GeoJson
    mask_gdf = gpd.GeoSeries([world_polygon, nyc_polygon], crs="EPSG:4326")
    mask = folium.GeoJson(data=mask_gdf.__geo_interface__, style_function=lambda x: {'fillColor': 'white', 'color': 'white', 'fillOpacity': 1})
    mask.add_to(ev_map)

    # Add the census tracts colored by population density
    folium.Choropleth(
        geo_data=merged_gdf,
        data=merged_gdf,
        columns=['GEOID', 'Population_Density'],
        key_on='feature.properties.GEOID',
        fill_color='OrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Population Density (per km²)',
        highlight=True
    ).add_to(ev_map)

    # Add EV charging stations
    marker_cluster = MarkerCluster().add_to(ev_map)
    for idx, row in ev_data_nyc.iterrows():
        popup_text = f"""
        <b>Station Name:</b> {row['station_name']}<br>
        <b>Street Address:</b> {row['street_address']}<br>
        <b>City:</b> {row['city']}<br>
        <b>State:</b> {row['state']}<br>
        <b>ZIP Code:</b> {row['zip']}<br>
        <b>Fuel Type:</b> {row['fuel_type_code']}<br>
        <b>Access Code:</b> {row['access_code']}
        """
        iframe = folium.IFrame(html=popup_text, width=300, height=200)
        popup = folium.Popup(iframe, max_width=500)
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup
        ).add_to(marker_cluster)

    return ev_map

# Function to create the pickup and dropoff map
def create_pickup_dropoff_map(data, data_type):
    map_center = [40.7128, -74.0060]  # Center of NYC
    ev_map = folium.Map(location=map_center, zoom_start=11, tiles='cartodbpositron')

    # Add the taxi zones colored by the selected data type
    folium.Choropleth(
        geo_data=taxi_zones_gdf,
        data=data,
        columns=['LocationID', data_type],
        key_on='feature.properties.LocationID',
        fill_color='OrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=f'{data_type} Count',
        highlight=True
    ).add_to(ev_map)

    # Add EV charging stations
    marker_cluster = MarkerCluster().add_to(ev_map)
    for idx, row in ev_data_nyc.iterrows():
        popup_text = f"""
        <b>Station Name:</b> {row['station_name']}<br>
        <b>Street Address:</b> {row['street_address']}<br>
        <b>City:</b> {row['city']}<br>
        <b>State:</b> {row['state']}<br>
        <b>ZIP Code:</b> {row['zip']}<br>
        <b>Fuel Type:</b> {row['fuel_type_code']}<br>
        <b>Access Code:</b> {row['access_code']}
        """
        iframe = folium.IFrame(html=popup_text, width=300, height=200)
        popup = folium.Popup(iframe, max_width=500)
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup
        ).add_to(marker_cluster)

    return ev_map

# Function to update the pickup and dropoff map based on selected data type and hour
def update_pickup_dropoff_map(data_type, hour):
    if data_type == 'pickup_count':
        data = data_pu[data_pu['hour_of_day'] == hour]
        data = data.rename(columns={'PULocationID': 'LocationID'})
    elif data_type == 'dropoff_count':
        data = data_do[data_do['hour_of_day'] == hour]
        data = data.rename(columns={'DOLocationID': 'LocationID'})
    
    ev_map = create_pickup_dropoff_map(data, data_type)
    ev_map.save('pickup_dropoff_map.html')

# Generate initial maps
create_population_density_map().save('population_density_map.html')
update_pickup_dropoff_map('pickup_count', 0)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[
    'https://fonts.googleapis.com/css2?family=Raleway:wght@400;700&display=swap',
    '/assets/styles.css'
])

# Define the app layout
app.layout = html.Div(className='container', children=[
    html.H1('NYC EV Charging Stations and Data Maps', style={'textAlign': 'center'}),
    html.Div(className='row', children=[
        html.Div(className='map-container', children=[
            dcc.Tabs([
                dcc.Tab(label='Population Density', children=[
                    html.Iframe(id='population-density-map', srcDoc=open('population_density_map.html', 'r').read(), width='100%', height='800', style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto'})
                ]),
                dcc.Tab(label='Pickups and Dropoffs', children=[
                    dcc.Dropdown(
                        id='data-type-dropdown',
                        options=[
                            {'label': 'Number of Pickups', 'value': 'pickup_count'},
                            {'label': 'Number of Drop Offs', 'value': 'dropoff_count'}
                        ],
                        value='pickup_count'
                    ),
                    dcc.Slider(
                        id='hour-slider',
                        min=0,
                        max=23,
                        step=1,
                        value=0,
                        marks={i: str(i) for i in range(24)}
                    ),
                    dcc.Interval(
                        id='interval-component',
                        interval=1*1000,  # in milliseconds
                        n_intervals=0,
                        disabled=True
                    ),
                    html.Button('Play', id='play-button', n_clicks=0),
                    html.Button('Pause', id='pause-button', n_clicks=0),
                    html.Iframe(id='pickup-dropoff-map', srcDoc=open('pickup_dropoff_map.html', 'r').read(), width='100%', height='800', style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto'})
                ])
            ])
        ], style={'width': '70%', 'display': 'inline-block', 'vertical-align': 'top'}),
        html.Div(className='text-container', children=[
            html.Div(id='text-content', children=[
                html.P("This map is used to identify the existing EV charging stations in different census tracts of NYC based on the population density and to provide insights on the spread of the EV charging stations across different parts of NYC.")
            ], style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center', 'height': '100%'})
        ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding-left': '20px'})
    ])
])

@app.callback(
    Output('interval-component', 'disabled'),
    [Input('play-button', 'n_clicks'), Input('pause-button', 'n_clicks')]
)
def toggle_interval(play_clicks, pause_clicks):
    return pause_clicks > play_clicks

@app.callback(
    [Output('hour-slider', 'value'), Output('pickup-dropoff-map', 'srcDoc'), Output('text-content', 'children')],
    [Input('data-type-dropdown', 'value'), Input('hour-slider', 'value'), Input('interval-component', 'n_intervals')],
    [State('play-button', 'n_clicks'), State('pause-button', 'n_clicks')]
)
def update_output(data_type, hour, n_intervals, play_clicks, pause_clicks):
    if play_clicks > pause_clicks:
        hour = n_intervals % 24
    update_pickup_dropoff_map(data_type, hour)
    text_content = ""
    if data_type == 'pickup_count':
        text_content = "We used NYC Taxi data from 2019 as a proxy for traffic patterns, illustrating the number of trips throughout the day and overlaying EV charging stations to highlight areas of need. Black zones indicate no trips during specific times of the day, with Staten Island having more black zones, possibly due to residents primarily commuting by car and taking a ferry to other parts of NYC. To animate the graph and view trip density throughout the day, click 'Play'. To focus on a specific time of day, click 'Pause'."
    else:
        text_content = "This map is used to identify the existing EV charging stations in different census tracts of NYC based on the population density and to provide insights on the spread of the EV charging stations across different parts of NYC."
    return hour, open('pickup_dropoff_map.html', 'r').read(), html.P(text_content, style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center', 'height': '100%'})

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
