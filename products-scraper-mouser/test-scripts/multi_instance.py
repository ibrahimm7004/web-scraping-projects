import gzip
import json
import os
import pandas as pd
import time
import random
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import Pool

# List of proxies
proxies = [
    'http://43.153.208.148:3128',
    'http://223.135.156.183:8080',
    'http://192.99.169.19:8450',
    'http://72.10.160.91:8167',
    'http://15.204.161.192:18080',
    'http://51.83.62.245:8080',
    'http://159.203.104.153:4550',
    'http://43.134.33.254:3128',
    'http://200.174.198.86:8888',
    'http://5.189.184.6:80',
    # Add the remaining proxies here...
]

# Function to configure Chrome driver with a random proxy


def get_driver_with_proxy(proxy):
    chrome_options = Options()
    chrome_options.page_load_strategy = 'none'

    # Set proxy
    chrome_options.add_argument(f'--proxy-server={proxy}')

    driver_path = r'chromedriver.exe'
    driver = webdriver.Chrome(service=Service(
        driver_path), options=chrome_options)
    return driver

# Function to process each part of the DataFrame


def process_df_part(df_part, start_delay):
    # Introduce a delay to avoid simultaneous writes
    time.sleep(start_delay)

    # Get a random proxy for each process/browser
    proxy = random.choice(proxies)

    # Set up Chrome driver and browser with the selected proxy
    driver = get_driver_with_proxy(proxy)

    url = "https://www.mouser.com/"
    driver.get(url)

    # Load cookies
    with open('cookies.json', 'r') as file:
        cookies = json.load(file)

    for cookie in cookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
            del cookie['sameSite']
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error adding cookie: {cookie['name']}, Error: {e}")

    driver.refresh()
    processed_count = 0
    count = 0

    for index, x in df_part['Part Number'].items():
        count += 1
        driver.get(url)

        try:
            # Use WebDriverWait to interact with the search bar as soon as it appears
            search_bar = WebDriverWait(driver, 10, poll_frequency=0.01).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//input[@data-testid="global-search"]'))
            )
            search_bar.clear()
            search_bar.send_keys(x)

            search_button = WebDriverWait(driver, 10, poll_frequency=0.01).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[@data-testid="hdrSrch"]'))
            )
            search_button.click()

            home_page_folder = os.path.join(os.getcwd(), "HomePage")
            if not os.path.exists(home_page_folder):
                os.makedirs(home_page_folder)

            home_html_file_path = os.path.join(
                home_page_folder, f"{x}.html.gz")

            with gzip.open(home_html_file_path, 'wt', encoding='utf-8') as file:
                file.write(driver.page_source)

            try:
                # Check for the presence of the search results table quickly (2-second timeout)
                element = WebDriverWait(driver, 2, poll_frequency=0.01).until(
                    EC.presence_of_element_located((By.ID, "searchResultsTbl"))
                )

                part_number_elements = driver.find_elements(
                    By.XPATH, '//div[@class="mfr-part-num hidden-xs"]//a'
                )

                for part_element in part_number_elements:
                    part_text = part_element.text.strip()

                    if part_text == x:
                        part_url = part_element.get_attribute("href")
                        driver.get(part_url)

                        detail_page_folder = os.path.join(
                            os.getcwd(), "DetailPage")

                        if not os.path.exists(detail_page_folder):
                            os.makedirs(detail_page_folder)

                        detail_html_file_path = os.path.join(
                            detail_page_folder, f"{x}.html.gz")

                        with gzip.open(detail_html_file_path, 'wt', encoding='utf-8') as file:
                            file.write(driver.page_source)

                        break

            except:
                print(f"No detail page found for product {x}, skipping.")

        except Exception as e:
            print(f"Error searching for product {x}: {e}")
            continue

        df_part = df_part.drop(index)
        processed_count += 1

        if processed_count % 100 == 0:
            df_part.to_csv("Mouser_source_202409.tsv",
                           sep='\t', header=False, index=False, mode='a')
            print(f"Updated TSV file after {processed_count} iterations.")

        print(f'{count} parts done.')

    df_part.to_csv("Mouser_source_202409.tsv", sep='\t',
                   header=False, index=False, mode='a')
    print("Final update to TSV file complete.")

    driver.quit()


if __name__ == "__main__":
    # Read the main DataFrame
    df = pd.read_csv("Mouser_source_202409.tsv", sep='\t', header=None)
    df.columns = ['Part Number']

    # Split the DataFrame into 4 smaller DataFrames
    df_parts = np.array_split(df, 4)

    # Define start delays for each process (3 minutes apart)
    start_delays = [0, 180, 360, 540]  # Seconds (0, 3 min, 6 min, 9 min)

    # Use multiprocessing Pool to process the parts concurrently
    with Pool(4) as pool:
        pool.starmap(process_df_part, [(df_part, start_delay)
                     for df_part, start_delay in zip(df_parts, start_delays)])
