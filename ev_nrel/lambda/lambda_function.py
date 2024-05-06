# Lambda function for importing alternate fuel stations from NREL
# Author: Eshan
# Status: WIP

import pandas as pd
import requests
import time
import boto3
import pyarrow.parquet as pq


# Initialize the clients for S3 and DynamoDB
from botocore.client import Config
s3 = boto3.client('s3', region_name= "us-east-1",config=Config(signature_version='s3v4'))
s3_resource = boto3.resource('s3')

# Define S3 bucket name for project
bucket_name = 'final-project-nrel-stations'

# define folder name inside s3 bucket
folder_name = 'station-parquet-files'

# Check if s3 bucket exists; if not, create 
if 'Buckets' in s3.list_buckets():
    for bucket in s3.list_buckets()['Buckets']:
        if bucket['Name'] == 'final-project-nrel-stations':
            print('S3 bucket exists')
            break
    else:
        s3.create_bucket(Bucket=bucket_name)

# Define lambda function
def lambda_handler(event,context):

    # Define start time
    start_time = time.time()

    # Extract relevant attributes from the event
    api_key = event['api_key']
    state=event['state']

    url = f"https://developer.nrel.gov/api/alt-fuel-stations/v1.json?api_key={api_key}&state={state}"
    response = requests.get(url)
    data = response.json()
    
    # Count the number of fuel stations returned
    print(f"Number of fuel stations in {state}: {data['total_results']}")
    
    # Extract the list of fuel stations
    stations = data['fuel_stations']
    stations_df = pd.DataFrame(stations)

    # Upload stations dataframe to S3 bucket as parquet with state initials
    try:
        stations_df.to_parquet(f"/tmp/{state}_stations.parquet")
        s3.upload_file(f"/tmp/{state}_stations.parquet", bucket_name, f"{folder_name}/{state}_stations.parquet")
        print(f'parquet file uploaded for state {state} to S3')
    except Exception as e:
        print(e)
        print('Error uploading file to S3')    

    # Define end time
    end_time = time.time()

    # Print the time taken to process the data upto 2 decimal places
    print(f"Time taken to get EV data for {state}: {end_time - start_time:.2f} seconds")