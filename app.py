import dash
from dash import dcc, html
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import base64

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
    html.Iframe(srcDoc=base64.b64decode(encoded_map).decode(), width='100%', height='600')
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
