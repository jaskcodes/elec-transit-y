import dash
from dash import dcc, html, Output, Input
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import base64
import json
from geopy.distance import geodesic
import numpy as np
import matplotlib.pyplot as plt
import mpld3

# Load the data
data_path = '/Users/jaskiratkaur/Documents/HPC/elec-transit-y/data/ev_stations_v1.csv'
ev_data = pd.read_csv(data_path, low_memory=False)

# Process the data
ev_data['open_date'] = pd.to_datetime(ev_data['open_date'], errors='coerce')
ev_data['year'] = ev_data['open_date'].dt.year
ev_data = ev_data.dropna(subset=['year'])
ev_data['year'] = ev_data['year'].astype(int)

# Create scatter plot
data_for_plotting = ev_data.groupby(['year', 'state']).size().reset_index(name='count')
scatter_fig = px.scatter(data_for_plotting, x='year', y='count', color='state',
                         title='Growth of EV Charging Stations Over Time by State')

# Create bar chart for fuel type distribution
fuel_type_df = ev_data['fuel_type_code'].value_counts().reset_index()
fuel_type_df.columns = ['fuel_type_code', 'count']
fuel_type_fig = px.bar(fuel_type_df, x='fuel_type_code', y='count',
                       labels={'fuel_type_code': 'Fuel Type', 'count': 'Count'},
                       title='Fuel Type Distribution')

# Create pie chart for access code distribution
access_code_df = ev_data['access_code'].value_counts().reset_index()
access_code_df.columns = ['access_code', 'count']
access_code_fig = px.pie(access_code_df, names='access_code', values='count',
                         labels={'access_code': 'Access Code', 'count': 'Count'},
                         title='Access Code Distribution')

# Create bar chart for number of stations by state
state_df = ev_data['state'].value_counts().reset_index()
state_df.columns = ['state', 'count']
state_fig = px.bar(state_df, x='state', y='count',
                   labels={'state': 'State', 'count': 'Number of Stations'},
                   title='Number of Stations by State')

# Create map
latitudes = ev_data['latitude']
longitudes = ev_data['longitude']
mean_lat, mean_lon = latitudes.mean(), longitudes.mean()
ev_map = folium.Map(location=[mean_lat, mean_lon], zoom_start=5)
marker_cluster = MarkerCluster().add_to(ev_map)

# Add charging station locations to the map with popups
for idx, row in ev_data.iterrows():
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

# Add LatLngPopup to display latitude and longitude on click
ev_map.add_child(folium.LatLngPopup())

# Save the map as an HTML file
ev_map.save('ev_map.html')

# Read the map HTML and encode it as a base64 string
with open('ev_map.html', 'r') as file:
    ev_map_html = file.read()

encoded_map = base64.b64encode(ev_map_html.encode()).decode()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[
    'https://fonts.googleapis.com/css2?family=Raleway:wght@400;700&display=swap',
    '/assets/styles.css'
])

# Define the app layout
app.layout = html.Div(className='container', children=[
    html.H1('Electric Vehicle Charging Stations Dashboard'),

    html.Div(className='row', children=[
        html.Div(className='column', children=[
            html.H2('Growth of EV Charging Stations Over Time by State'),
            dcc.Graph(figure=scatter_fig)
        ]),
        html.Div(className='column', children=[
            html.H2('Fuel Type Distribution'),
            dcc.Graph(figure=fuel_type_fig)
        ])
    ]),

    html.Div(className='row', children=[
        html.Div(className='column', children=[
            html.H2('Access Code Distribution'),
            dcc.Graph(figure=access_code_fig)
        ]),
        html.Div(className='column', children=[
            html.H2('Number of Stations by State'),
            dcc.Graph(figure=state_fig)
        ])
    ]),

    html.H2('EV Charging Stations Map'),
    html.Iframe(id='map', srcDoc=base64.b64decode(encoded_map).decode(), width='100%', height='600'),

    dcc.Input(id='map_click_data', type='hidden', value=''),
    html.Div(id='output', style={'margin-top': '20px'}),

    # Graph output placeholder
    html.Div(id='graph-output', style={'width': '100%', 'height': '600px'}),  # Adding this line

])

# JavaScript to capture click events and send data to Dash
app.clientside_callback(
    """
    function(srcDoc) {
        var mapFrame = document.getElementById('map').contentWindow;
        mapFrame.document.querySelectorAll('.leaflet-container').forEach((container) => {
            container.addEventListener('click', function(e) {
                var lat = e.latlng.lat;
                var lon = e.latlng.lng;
                document.getElementById('map_click_data').value = JSON.stringify({lat: lat, lon: lon});
                document.getElementById('map_click_data').dispatchEvent(new Event('input'));
            });
        });
        return srcDoc;
    }
    """,
    Output('map', 'srcDoc'),
    [Input('map', 'srcDoc')]
)

def generate_graphs(lat, lon, ev_data, radius=0.5):  # radius in kilometers
    # Filter data for nearby stations
    selected_data = ev_data[ev_data.apply(lambda row: geodesic((lat, lon), (row['latitude'], row['longitude'])).km <= radius, axis=1)]
    coordinates = np.column_stack((selected_data['longitude'], selected_data['latitude']))
    
    # Create graphs
    knn_graph = weights.KNN.from_array(coordinates, k=3).to_networkx()
    dist_graph = weights.DistanceBand.from_array(coordinates, threshold=50).to_networkx()

    # Generate plots
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    positions = dict(zip(knn_graph.nodes, coordinates))
    nx.draw(knn_graph, positions, ax=ax[0], node_color='blue', node_size=50, with_labels=True)
    nx.draw(dist_graph, positions, ax=ax[1], node_color='red', node_size=50, with_labels=True)
    ax[0].set_title('3-Nearest Neighbor Graph')
    ax[1].set_title('50-meter Distance Band Graph')

    # Convert plot to HTML
    plt.tight_layout()
    graph_html = mpld3.fig_to_html(fig)
    return graph_html

# Function to get stations within a given radius
def get_stations_in_radius(lat, lon, radius):
    stations = []
    for idx, row in ev_data.iterrows():
        station_lat = row['latitude']
        station_lon = row['longitude']
        distance = geodesic((lat, lon), (station_lat, station_lon)).miles
        if distance <= radius:
            stations.append({
                'name': row['station_name'],
                'street_address': row['street_address'],
                'city': row['city'],
                'state': row['state'],
                'zip': row['zip'],
                'latitude': row['latitude'],
                'longitude': row['longitude']
            })
    return stations

# Function to update the map with stations in the radius
def update_stations_in_radius(lat, lon, radius):
    stations = get_stations_in_radius(lat, lon, radius)
    updated_map = folium.Map(location=[lat, lon], zoom_start=5)
    marker_cluster = MarkerCluster().add_to(updated_map)
    for station in stations:
        popup_text = f"""
        <b>Station Name:</b> {station['name']}<br>
        <b>Street Address:</b> {station['street_address']}<br>
        <b>City:</b> {station['city']}<br>
        <b>State:</b> {station['state']}<br>
        <b>ZIP Code:</b> {station['zip']}
        """
        iframe = folium.IFrame(html=popup_text, width=300, height=200)
        popup = folium.Popup(iframe, max_width=500)
        folium.Marker(
            location=[station['latitude'], station['longitude']],
            popup=popup
        ).add_to(marker_cluster)
    return updated_map

@app.callback(
    Output('graph-output', 'children'),
    [Input('map_click_data', 'value')]
)
def update_graphs(click_data):
    if click_data:
        click_data = json.loads(click_data)
        lat = click_data['lat']
        lon = click_data['lon']
        print(f"Received click at latitude: {lat}, longitude: {lon}")  # Debugging line
        graph_html = generate_graphs(lat, lon, ev_data)
        updated_map = update_stations_in_radius(lat, lon, radius=0.5)
        updated_map.save('updated_ev_map.html')
        with open('updated_ev_map.html', 'r') as file:
            updated_ev_map_html = file.read()
        encoded_updated_map = base64.b64encode(updated_ev_map_html.encode()).decode()
        return html.Div([
            html.Iframe(srcDoc=graph_html, width='100%', height='600'),
            html.Iframe(srcDoc=base64.b64decode(encoded_updated_map).decode(), width='100%', height='600')
        ])
    return 'Click on the map to generate graphs.'

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
