import pandas as pd
import requests
from bs4 import BeautifulSoup

# Read the CSV file
df = pd.read_csv('C:/Users/hp/Downloads/final.csv')

for index, row in df.iterrows():
    # Iterate over all rows starting from row 1785
    # if index >= 11800 and index <= 11804:
        # Get the URL from the 'Links' column
        url = row['Links']

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        # Send a GET request to the URL and retrieve the page content
        response = requests.get(url, headers=headers)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the h4 element containing the "Spoken languages" text
        spoken_languages_h4 = soup.find('h4', text='Spoken languages')

        if spoken_languages_h4:
            # Find the ul element containing the spoken languages
            spoken_languages_ul = spoken_languages_h4.find_next_sibling('ul', class_='Profile__list--hyphenated')
            if spoken_languages_ul:
                # Find the li element containing the spoken language
                spoken_language_li = spoken_languages_ul.find('li')
                if spoken_language_li:
                    # Extract the text of the spoken language
                    spoken_language = spoken_language_li.text.strip()
                    print(index, ' ', spoken_language)
                else:
                    spoken_language = 'Not found'
            else:
                spoken_language = 'Not found'
        else:
            spoken_language = 'Not found'

        # Update the 'Spoken languages' column with the extracted language
        df.at[index, 'Spoken languages'] = spoken_language

        # Save the updated row to the original CSV file
        df.to_csv('C:/Users/hp/Downloads/final.csv', index=False)

print('DONE')


'C:/Users/hp/Downloads/final.csv'