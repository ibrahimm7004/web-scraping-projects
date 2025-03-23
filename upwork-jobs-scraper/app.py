import time
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service

# Google Sheets and Selenium configurations
driver_path = r'chromedriver.exe'
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
sheet_path = r"sheets-5e3cf7f4981a.json"
sheet_url = "example-sheet-url"

# Authenticate and access the Google Sheet
gc = gspread.service_account(filename=sheet_path)
sh = gc.open_by_url(sheet_url)
worksheet = sh.get_worksheet(0)

# Retrieve the column headers and map them to column indices
column_headers = worksheet.row_values(2)
columns = {header: idx + 1 for idx, header in enumerate(column_headers)}

# Assign column numbers to variables for easier access
name_col = columns.get("Name")
url_col = columns.get("URL")
title_col = columns.get("Title")
payment_type_col = columns.get("Payment Type")
price_col = columns.get("Price")
project_type_col = columns.get("Project Type")
skills_col = columns.get("Skills")
proposals_col = columns.get("Proposals")
last_viewed_col = columns.get("Last viewed")
interviewing_col = columns.get("Interviewing")
invites_sent_col = columns.get("Invites sent")
unanswered_invites_col = columns.get("Unanswered invites")
done_col = columns.get("Done")
experience_level_col = columns.get("Experience Level")
duration_col = columns.get("Duration")
member_since_col = columns.get("Member Since")
location_col = columns.get("Location")
total_spent_col = columns.get("Total Spent")
hires_col = columns.get("Hires")
client_type_col = columns.get("Client Type")
description_col = columns.get("Description")

# Get the URLs and Done status from the relevant columns
urls_column = worksheet.col_values(url_col)[2:]  # From row 3 onward
done_column = worksheet.col_values(done_col)[2:]  # From row 3 onward

# Loop through the URLs, skipping rows marked as "TRUE" in the Done column
for i, (url, done) in enumerate(zip(urls_column, done_column)):
    first_unchecked_row = i + 3  # Since data starts from row 3

    # If the URL is empty, stop the script (end of data)
    if not url:
        print(f"Stopping at row {first_unchecked_row} due to no URL.")
        break

    # Skip rows that are already marked as "TRUE" (done)
    if done.upper() == "TRUE":
        print(
            f"Skipping row {first_unchecked_row} as it's already marked 'Done'")
        continue

    # If URL is not empty, proceed to scrape
    print(f"Processing row {first_unchecked_row} - {url}")

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    driver.get(url)
    time.sleep(3)  # Give page some time to load

    try:
        # Scrape the job title
        job_title_element = driver.find_element(By.CSS_SELECTOR, "h4.m-0")
        job_title = job_title_element.text
        worksheet.update_cell(first_unchecked_row, title_col, job_title)
    except:
        pass

    try:
        # Scrape job description
        description_element = driver.find_element(
            By.CSS_SELECTOR, "div.break.mt-2 p.text-body-sm")
        job_description = description_element.text
        worksheet.update_cell(first_unchecked_row,
                              description_col, job_description)
    except:
        pass

    try:
        # Check if the job is hourly or fixed price
        hourly_element = driver.find_element(
            By.CSS_SELECTOR, "div[data-cy='clock-hourly']")
        payment_type = "Hourly"
        worksheet.update_cell(first_unchecked_row,
                              payment_type_col, payment_type)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        prices = soup.find_all('strong', attrs={'data-v-8d6ae40e': True})

        if len(prices) == 2:
            min_price = prices[0].get_text().strip()
            max_price = prices[1].get_text().strip()
            hourly_rate = f"{min_price} - {max_price}"
            worksheet.update_cell(first_unchecked_row, price_col, hourly_rate)
        else:
            worksheet.update_cell(first_unchecked_row,
                                  price_col, "No hourly rate provided")
    except:
        try:
            budget_element = driver.find_element(
                By.CSS_SELECTOR, "[data-v-8d6ae40e]")
            payment_type = "Fixed Price"
            worksheet.update_cell(first_unchecked_row,
                                  payment_type_col, payment_type)

            price_element = budget_element.find_element(By.TAG_NAME, "strong")
            price = price_element.text
            worksheet.update_cell(first_unchecked_row, price_col, price)
        except:
            pass

    try:
        # Scrape skills
        all_skills = []
        skills_sections = driver.find_elements(
            By.CSS_SELECTOR, "div.skills-list.mt-3")
        for section in skills_sections:
            skill_elements = section.find_elements(
                By.CSS_SELECTOR, "span.air3-badge.air3-badge-highlight.badge.disabled")
            section_skills = [skill.text for skill in skill_elements]
            all_skills.extend(section_skills)

        unique_skills = list(set(all_skills))
        if unique_skills:
            skills_text = ", ".join(unique_skills).strip(
                ", ")  # Remove extra commas
        else:
            skills_text = "No skills listed"

        worksheet.update_cell(first_unchecked_row, skills_col, skills_text)
    except:
        pass

    try:
        # Scrape Duration
        duration_element = driver.find_element(
            By.CSS_SELECTOR, "div[data-cy='duration2'] + strong")
        duration = duration_element.text
        worksheet.update_cell(first_unchecked_row, duration_col, duration)
    except:
        pass

    try:
        # Scrape Experience Level
        experience_level_element = driver.find_element(
            By.CSS_SELECTOR, "div[data-cy='expertise'] + strong")
        experience_level = experience_level_element.text
        worksheet.update_cell(first_unchecked_row,
                              experience_level_col, experience_level)
    except:
        pass

    try:
        # Scrape Project Type (e.g., Ongoing project, etc.)
        project_type_element = driver.find_element(
            By.CSS_SELECTOR, "div[data-cy='briefcase-outlined'] + strong")
        project_type = project_type_element.text
        worksheet.update_cell(first_unchecked_row,
                              project_type_col, project_type)
    except:
        pass

    # Scrape Activity Section
    try:
        activity_section = driver.find_element(
            By.CSS_SELECTOR, "ul.client-activity-items.list-unstyled.visitor")

        try:
            proposals = activity_section.find_element(
                By.XPATH, ".//span[contains(text(), 'Proposals')]/following-sibling::span[@class='value']").text
            worksheet.update_cell(first_unchecked_row,
                                  proposals_col, proposals)
        except:
            pass

        try:
            last_viewed = activity_section.find_element(
                By.XPATH, ".//span[contains(text(), 'Last viewed by client')]/following-sibling::span[@class='value']").text
            worksheet.update_cell(first_unchecked_row,
                                  last_viewed_col, last_viewed)
        except:
            pass

        try:
            interviewing = activity_section.find_element(
                By.XPATH, ".//span[contains(text(), 'Interviewing')]/following-sibling::div[@class='value']").text
            worksheet.update_cell(first_unchecked_row,
                                  interviewing_col, interviewing)
        except:
            pass

        try:
            invites_sent = activity_section.find_element(
                By.XPATH, ".//span[contains(text(), 'Invites sent')]/following-sibling::div[@class='value']").text
            worksheet.update_cell(first_unchecked_row,
                                  invites_sent_col, invites_sent)
        except:
            pass

        try:
            unanswered_invites = activity_section.find_element(
                By.XPATH, ".//span[contains(text(), 'Unanswered invites')]/following-sibling::div[@class='value']").text
            worksheet.update_cell(first_unchecked_row,
                                  unanswered_invites_col, unanswered_invites)
        except:
            pass
    except:
        pass

    # Scrape About Client Section
    try:
        about_client_section = driver.find_element(
            By.CSS_SELECTOR, "div.cfe-about-client-v2")

        try:
            member_since = about_client_section.find_element(
                By.CSS_SELECTOR, "div[data-qa='client-contract-date'] small").text.replace("Member since ", "")
            worksheet.update_cell(first_unchecked_row,
                                  member_since_col, member_since)
        except:
            pass

        try:
            location_city = about_client_section.find_element(
                By.CSS_SELECTOR, "li[data-qa='client-location'] strong").text
            location_time = about_client_section.find_element(
                By.CSS_SELECTOR, "li[data-qa='client-location'] div span:nth-child(1)").text
            location = f"{location_time}, {location_city}".strip(", ")
            worksheet.update_cell(first_unchecked_row, location_col, location)
        except:
            pass

        try:
            total_spent = about_client_section.find_element(
                By.CSS_SELECTOR, "strong[data-qa='client-spend'] span").text
            worksheet.update_cell(first_unchecked_row,
                                  total_spent_col, total_spent)
        except:
            pass

        try:
            hires = about_client_section.find_element(
                By.CSS_SELECTOR, "div[data-qa='client-hires']").text
            worksheet.update_cell(first_unchecked_row, hires_col, hires)
        except:
            pass

        try:
            client_type = about_client_section.find_element(
                By.CSS_SELECTOR, "li[data-qa='client-company-profile'] strong").text
            company_size = about_client_section.find_element(
                By.CSS_SELECTOR, "li[data-qa='client-company-profile'] div[data-qa='client-company-profile-size']").text
            client_type_details = f"{client_type}, {company_size}"
        except:
            try:
                client_type_details = about_client_section.find_element(
                    By.CSS_SELECTOR, "li[data-qa='client-company-profile']").text
            except:
                client_type_details = "Individual client"

        worksheet.update_cell(first_unchecked_row,
                              client_type_col, client_type_details)

    except:
        pass

    # Mark the "Done" column as TRUE for this row after completing scraping
    worksheet.update_cell(first_unchecked_row, done_col, "TRUE")

    # Close the driver after completing scraping for one URL
    driver.quit()

    # Sleep for 3 seconds before moving to the next URL (to avoid CAPTCHA issues)
    time.sleep(3)

print("Scraping completed.")
