from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import pandas as pd
import os
import json
import gzip

df = pd.read_csv("Mouser_source_sample.tsv", sep='\t', header=None)
df.columns = ['Part Number']

url = "https://www.mouser.com/"
driver_path = r'chromedriver.exe'
chrome_options = Options()
chrome_options.page_load_strategy = 'none'

count = 0

driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
driver.get(url)

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

for index, x in df['Part Number'].items():
    count += 1
    driver.get(url)

    try:
        # Use a reduced polling frequency for faster interaction with elements
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

        home_html_file_path = os.path.join(home_page_folder, f"{x}.html.gz")

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
            # Skip the product if the table is not found within 2 seconds
            print(f"No detail page found for product {x}, skipping.")

    except Exception as e:
        print(f"Error searching for product {x}: {e}")
        continue

    df = df.drop(index)
    processed_count += 1

    if processed_count % 100 == 0:
        df.to_csv("Mouser_source_202409.tsv",
                  sep='\t', header=False, index=False)
        print(f"Updated TSV file after {processed_count} iterations.")

    print(f'{count} parts done.')

df.to_csv("Mouser_source_202409.tsv", sep='\t', header=False, index=False)
print("Final update to TSV file complete.")

driver.quit()
