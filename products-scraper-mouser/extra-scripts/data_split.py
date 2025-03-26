import os
import pandas as pd

# Define file paths
source_file = r'Mouser_source_20240910.tsv'
destination_dir = r'data'

# Create the destination directory if it doesn't exist
if not os.path.exists(destination_dir):
    os.makedirs(destination_dir)

# Load the data from the TSV file
data = pd.read_csv(source_file, sep='\t')

# Get total number of rows
total_rows = len(data)

# Number of rows per chunk
chunk_size = 1000

# Split data into chunks of 1000 rows each and save to new TSV files
for i in range(0, total_rows, chunk_size):
    # Select the current chunk
    chunk = data[i:i + chunk_size]

    # Define the file name for the current chunk
    chunk_file = os.path.join(
        destination_dir, f'mouser_chunk_{i // chunk_size + 1}.tsv')

    # Save the current chunk to a new TSV file
    chunk.to_csv(chunk_file, sep='\t', index=False)

print("Data split into chunks and saved to the destination directory.")
