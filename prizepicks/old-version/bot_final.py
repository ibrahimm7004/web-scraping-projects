import discord
from discord.ext import commands, tasks
import pandas as pd
import time
import os

# Set up intents
intents = discord.Intents.default()  # Enable default intents
intents.message_content = True  # Enable message content intent explicitly

# Create a bot instance with the required intents
client = commands.Bot(command_prefix='!', intents=intents)

# Global variable to keep track of the last processed timestamp
last_processed_time = None


@client.event
async def on_ready():
    print("The bot is now ready for use!")
    print("-----------------------------")
    # Start monitoring for updates
    monitor_updates.start()


@tasks.loop(seconds=10)  # Check every 10 seconds
async def monitor_updates():
    """Check for updates in the CSV file and send all new rows if updated."""
    global last_processed_time

    try:
        # Check the modification time of the CSV file
        file_path = 'player_data.csv'
        if not os.path.exists(file_path):
            print("File player_data.csv does not exist. Skipping update check.")
            return

        # Read the data
        df = pd.read_csv(file_path)

        if df.empty:
            print("No data found in CSV.")
            return

        # Ensure 'attributes.updated_at' column is in datetime format
        if 'attributes.updated_at' in df.columns:
            df['attributes.updated_at'] = pd.to_datetime(
                df['attributes.updated_at'], errors='coerce')

        # Filter rows with updated_at newer than last_processed_time
        if last_processed_time is not None:
            new_rows = df[df['attributes.updated_at'] > last_processed_time]
        else:
            new_rows = df  # If no processed time, consider all rows as new

        # If no new rows, skip processing
        if new_rows.empty:
            print("No new rows detected.")
            return

        # Update the last processed time
        last_processed_time = df['attributes.updated_at'].max()

        # Send each new row as a message
        for _, row in new_rows.iterrows():
            name = row['attributes.name']
            team = row['attributes.team']
            position = row['attributes.position']
            score = row['attributes.line_score']
            stat = row['attributes.stat_type']
            start_time = row['attributes.start_time']

            # Create a message
            message = (
                f"New Player Update:\n"
                f"- Name: {name}\n"
                f"- Team: {team}\n"
                f"- Position: {position}\n"
                f"- Score: {score}\n"
                f"- Stat: {stat}\n"
                f"- Start Time: {start_time}"
            )
            print("Sending new player update to Discord...")

            # Send the message to the first available text channel
            for guild in client.guilds:
                for channel in guild.text_channels:
                    print(f"Checking channel: {channel.name}")
                    if channel.name == "general":  # Replace with your channel name
                        await channel.send(message)
                        print(f"Message sent to channel: {channel.name}")
                        break

    except Exception as e:
        print(f"Error monitoring updates: {e}")


client.run('example-token-id')
