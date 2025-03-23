from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import time
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASSWORD = os.getenv('FB_PASSWORD')

# File paths
input_csv_path = r'new_csv.csv'
output_csv_path = r'fb_group_members.csv'

# Load input CSV into a pandas DataFrame
group_df = pd.read_csv(input_csv_path)


def login_to_facebook(driver):
    driver.get('https://www.facebook.com/login')
    wait_after_navigate = '//div[@class="login_form_container"]'
    wait_for_element_presence(driver, wait_after_navigate)
    driver.find_element(By.ID, "email").send_keys(FB_EMAIL)
    driver.find_element(By.ID, "pass").send_keys(FB_PASSWORD)
    driver.find_element(By.NAME, "login").click()
    wait_after_login = '//div[@role="banner"]//div[@aria-label="Facebook" and @role="navigation"]'
    wait_for_element_presence(driver, wait_after_login)
    print("Logged in to Facebook.")


def optimized_scroll_and_collect_urls(driver, max_wait_time=10):
    scroll_pause_time = 0.5  # Time to wait after each scroll (in seconds)
    last_height = driver.execute_script("return document.body.scrollHeight")
    start_time = time.time()

    while True:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            if time.time() - start_time > max_wait_time:
                break
        else:
            start_time = time.time()

        last_height = new_height

    page_html = driver.page_source
    urls = extract_urls_from_html(page_html)

    print(f"Collected {len(urls)} URLs from the People section.")
    return urls


def extract_urls_from_html(members_html):
    soup = BeautifulSoup(members_html, 'html.parser')
    links = soup.find_all('a', href=True)
    all_a_urls = [link['href'] for link in links]
    filtered_profiles_urls = list(
        set([o for o in all_a_urls if o != "" and "/user/" in o]))
    return filtered_profiles_urls


def wait_for_element_presence(driver, xpath, wait_secs=60, by=By.XPATH):
    try:
        WebDriverWait(driver, wait_secs).until(
            EC.presence_of_element_located((by, xpath))
        )
    except Exception as e:
        print(f"wait_for_element_presence Failed {e} XPath :: {xpath}")


def visit_public_group_and_get_all_member_urls(driver, group_url):
    try:
        driver.get(group_url)
        wait_after_navigate_group = "(//span[.='Join Group' or .='Join group'])[1]"
        wait_for_element_presence(driver, wait_after_navigate_group)

        people_tab_path = "//a[@role='tab']/div/span[.='People']"
        scroll_path = "//span[.='New to the group']"

        driver.find_element(By.XPATH, people_tab_path).click()
        time.sleep(2)
        wait_for_element_presence(driver, scroll_path)

        scroll_ele = driver.find_element(By.XPATH, people_tab_path)
        driver.execute_script("arguments[0].scrollIntoView();", scroll_ele)

        profile_urls = optimized_scroll_and_collect_urls(driver)
        return profile_urls
    except Exception as e:
        print(f"Error visiting group: {e}")
        return []


def convert_to_proper_url(broken_url):
    numeric_id = broken_url.split('/')[-2]
    proper_url = f"https://www.facebook.com/profile.php?id={numeric_id}"
    return proper_url


def process_member_urls(urls):
    list1 = []
    for url in urls:
        list1.append(convert_to_proper_url(url))
    return list1


def append_to_csv(df, output_path):
    if not os.path.isfile(output_path):
        df.to_csv(output_path, index=False)
    else:
        df.to_csv(output_path, mode='a', header=False, index=False)


def retrieve_and_process_member_urls(group_df, start_index=0):
    chrome_driver_path = r'chromedriver.exe'
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    driver = webdriver.Chrome(service=Service(
        chrome_driver_path), options=chrome_options)

    try:
        # Step 1: Log in to Facebook
        login_to_facebook(driver)

        # Process each group, starting from the given index
        for index in range(start_index, len(group_df)):
            row = group_df.iloc[index]
            group_url = row['Group URL']
            group_name = row['Group Name']

            print(f"Processing Group: {group_name} ({group_url})")

            # Step 2: Visit the group and get all member URLs
            all_member_urls = visit_public_group_and_get_all_member_urls(
                driver, group_url)

            # Step 3: Process the URLs to get the final list of profile URLs
            final_urls = process_member_urls(all_member_urls)

            # Step 4: Create a DataFrame with the required columns
            result_df = pd.DataFrame({
                'Group URL': [group_url] * len(final_urls),
                'Member URL': final_urls,
                'Group Name': [group_name] * len(final_urls)
            })

            # Step 5: Append the results to the output CSV
            append_to_csv(result_df, output_csv_path)

            # Print statement to indicate completion with group number
            print(f"{index + 1}. {group_name} - done")

            # Step 6: Remove the processed group from the original DataFrame
            group_df.drop(index, inplace=True)
            group_df.to_csv(input_csv_path, index=False)

            # Print the current index at the end of each iteration
            print(f"Last processed index: {index}")

    finally:
        driver.quit()


retrieve_and_process_member_urls(group_df, start_index=0)
