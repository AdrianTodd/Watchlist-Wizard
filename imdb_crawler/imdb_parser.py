import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
try:
    from . import utils # If running as part of a package
except ImportError:
    import utils # If running as a standalone script



# Define a standard Desktop User-Agent
DESKTOP_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36" # Example Chrome on Windows

def fetch_page(url):
    """Fetches a webpage, requesting the desktop version, respecting robots.txt."""
    if not utils.can_fetch(url): # Use the function from utils
        print(f"Skipping (robots.txt): {url}")
        return None
    try:
        # Use the Desktop User-Agent in the headers
        headers = {'User-Agent': DESKTOP_USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Check for HTTP errors

        # Check content type to ensure it's HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            print(f"Warning: Non-HTML content type '{content_type}' for URL: {url}")
            return None # Don't try to parse non-HTML

        print(f"Successfully fetched {url}")
        return response.text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during fetch for {url}: {e}")
        return None

def fetch_page_with_selenium(url, scroll_attempts=5, scroll_delay=1):
    """
    Fetches a webpage using Selenium, allowing JavaScript to execute.
    Includes scrolling to attempt loading dynamic content.
    """
    print(f"Fetching URL with Selenium: {url}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no GUI)
    chrome_options.add_argument("--disable-gpu") # Recommended for headless
    chrome_options.add_argument("--window-size=1920,1080") # Specify window size
    chrome_options.add_argument(f'user-agent=MyMovieProjectCrawler/1.0 {time.time()}') # Custom user agent

    driver = None
    try:
        # Use webdriver-manager to handle driver download/path
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url) # Loads webpage in current browser session

        # Attempt to load dynamic content by scrolling
        print("  Scrolling down to load dynamic content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(scroll_attempts):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_delay) # Wait for content to potentially load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height: # Stop scrolling if height doesn't change
                print("  Reached end of scroll or no new content loaded.")
                break
            last_height = new_height
        time.sleep(2)

        html = driver.page_source # Get the fully rendered HTML
        print(f"  Successfully fetched with Selenium.")
        return html

    except Exception as e:
        print(f"Error using Selenium for {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit() # close the browser instance

def parse_movie_page(html, movie_url):
    """Parses an IMDb movie page, robust to variations in HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    movie_data = {}

    try:
        # Parse Movie Title
        title_tag = soup.find('h1', attrs={"data-testid": "hero__pageTitle"})
        movie_data['title'] = title_tag.text.strip() if title_tag else None

        # Parse Movie Year, Runtime, AgeRating from meta tags
        twitter_title_meta = soup.find('meta', attrs={'property': 'twitter:title'})
        twitter_desc_meta = soup.find('meta', attrs={'property': 'twitter:description'})

        year = None
        runtime_text = None
        age_restriction = None

        if twitter_title_meta:
            title_content = twitter_title_meta.get('content', '')
            year_match = re.search(r'\((\d{4})\)', title_content)
            year = int(year_match.group(1)) if year_match else None

        if twitter_desc_meta:
            desc_content = twitter_desc_meta.get('content', '')
            runtime_age_match = re.search(r'(\d+h\s*\d+m|\d+h|\d+m)\s*\|\s*([A-Za-z0-9-]+)', desc_content)
            if runtime_age_match:
                runtime_text = runtime_age_match.group(1)
                age_restriction = runtime_age_match.group(2)
            else:
                 match_runtime_only = re.search(r'(\d+h\s*\d+m|\d+h|\d+m)', desc_content)
                 if match_runtime_only:
                     runtime_text = match_runtime_only.group(1)
                 match_rating_only = re.search(r'([A-Za-z0-9-]+)$', desc_content) # Check end for rating
                 if match_rating_only and match_rating_only.group(1) in ('G', 'PG', 'PG-13', 'R', 'NC-17', 'TV-Y', 'TV-Y7', 'TV-G', 'TV-PG', 'TV-14', 'TV-MA', '18A', 'APPROVED', 'Approved', 'UNRATED', 'Unrated', 'NOT RATED', 'Not Rated', 'PASSED', 'Passed'):
                     age_restriction = match_rating_only.group(1)


        movie_data['year'] = year
        movie_data['age_restriction'] = age_restriction

        # Movie Runtime
        if runtime_text:
            match_h = re.search(r'(\d+)h', runtime_text)
            hours = int(match_h.group(1)) if match_h else 0
            match_m = re.search(r'(\d+)m', runtime_text)
            minutes = int(match_m.group(1)) if match_m else 0
            movie_data['runtime'] = hours * 60 + minutes
        else:
            movie_data['runtime'] = None

        # IMDb Rating
        rating_wrapper = soup.find('div', {"data-testid": "hero-rating-bar__aggregate-rating__score"})
        if rating_wrapper:
            rating_tag = rating_wrapper.find('span')
            movie_data['rating'] = float(rating_tag.text.strip()) if rating_tag else None
        else:
            # Fallback: Try getting rating from twitter title meta
            if twitter_title_meta:
                title_content = twitter_title_meta.get('content', '')
                rating_match = re.search(r'⭐\s*([\d.]+)', title_content)
                movie_data['rating'] = float(rating_match.group(1)) if rating_match else None
            else:
                movie_data['rating'] = None

        # Movie Plot Summary
        plot_summary_tag = soup.find('span', attrs={"data-testid": "plot-xl"})
        movie_data['plot_summary'] = plot_summary_tag.text.strip() if plot_summary_tag else None

        # Movie Poster URL
        poster_tag = soup.find('img', class_='ipc-image')
        movie_data['poster_url'] = poster_tag['src'] if poster_tag and 'src' in poster_tag.attrs else None

        # Movie IMDb ID
        match_id = re.search(r'/title/(tt\d+)/', movie_url)
        movie_data['imdb_id'] = match_id.group(1) if match_id else None

        # Movie Release Date
        release_date_tag = soup.find('a', string='Release date')
        date = None
        if release_date_tag:
            parent = release_date_tag.find_parent('li')
            if parent:
                container = parent.find('div', class_='ipc-metadata-list-item__content-container')
                if container:
                    date_a_tag = container.find('a') # Find the 'a' tag containing the date
                    if date_a_tag:
                        date_text = date_a_tag.text.strip()
                        try:
                            parts = date_text.split('(')[0].strip().split()
                            if len(parts) == 3:
                                month, day, year_text = parts
                                date = datetime.strptime(f"{month} {day} {year_text}", "%B %d, %Y").strftime("%Y-%m-%d")
                            elif len(parts) == 2:
                                month, year_text = parts
                                date = datetime.strptime(f"{month} {year_text}", "%B %Y").strftime("%Y-%m-01")
                            elif len(parts) == 1:
                                date = datetime.strptime(parts[0], "%Y").strftime("%Y-01-01")
                        except (ValueError, IndexError) as e:
                            print(f"Error converting date: {date_text} - {e}")
                            date = None
        movie_data['release_date'] = date

        # Movie Genres
        genres = []
        genre_section = soup.find('div', {'data-testid': 'genres'})
        if genre_section:
            genre_tags = genre_section.find_all('a', class_="ipc-chip") # Class for genre links
            for tag in genre_tags:
                genres.append(tag.text.strip())
        movie_data['genres'] = genres


        # Movie People
        people = []
        seen_people = set()

        # Find the section containing credits list
        credits_section = soup.find('div', {'data-testid': 'title-pc-wide-screen'}) or \
                          soup.find('section', {'data-testid': 'title-cast'})

        if credits_section:
            # Find all list items that represent a credit role like director, writer, star
            # This selector targets the list items directly
            credit_items = credits_section.find_all('li', {'data-testid': 'title-pc-principal-credit'})

            if not credit_items: # Fallback if the above fails, try finding by role label within any li
                 credit_items = credits_section.find_all(lambda tag: tag.name == 'li' and tag.find(class_=re.compile(r'ipc-metadata-list-item__label')))

            for credit in credit_items:
                label_tag = credit.find('span', class_=re.compile(r'ipc-metadata-list-item__label')) or \
                            credit.find('a', class_=re.compile(r'ipc-metadata-list-item__label')) or \
                            credit.find('button', class_=re.compile(r'ipc-metadata-list-item__label'))

                if label_tag:
                    label_text = label_tag.text.strip()
                    role = None
                    if 'Director' in label_text: role = 'Director'
                    elif 'Writer' in label_text: role = 'Writer'
                    elif 'Star' in label_text: role = 'Actor'

                    if role:
                        # Find name links within the content container of the credit item
                        content_container = credit.find('div', class_=re.compile(r'ipc-metadata-list-item__content-container'))
                        if content_container:
                            name_tags = content_container.find_all('a', class_=re.compile(r'ipc-metadata-list-item__list-content-item--link'))
                            for name_tag in name_tags:
                                href = name_tag.get('href')
                                if href and '/name/nm' in href:
                                    person_id_match = re.search(r'/name/(nm\d+)/', href)
                                    if person_id_match:
                                        person_id = person_id_match.group(1)
                                        name = name_tag.text.strip()
                                        if (person_id, role) not in seen_people:
                                            people.append({'person_id': person_id, 'name': name, 'role': role})
                                            seen_people.add((person_id, role))
        movie_data['people'] = people
        #print(f"Extracted People: {people}")


        # Movie Plot Keywords
        if movie_data.get('plot_summary'):
            keywords = utils.extract_keywords(movie_data['plot_summary'])
            movie_data['plot_keywords'] = keywords
        else:
            movie_data['plot_keywords'] = []

    except Exception as e:
        print(f"*** UNEXPECTED Error parsing {movie_url}: {e} ***")
        import traceback
        traceback.print_exc() # Print full traceback for unexpected errors
        return None

    return movie_data

def parse_person_page(html, person_url):
    """Parses a person page using selectors verified against provided HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    person_data = {}
    print(f"--- Parsing Person Page: {person_url} ---")

    try:
        # Persons Name
        name_tag_container = soup.find('h1', attrs={"data-testid": "hero__pageTitle"})
        if name_tag_container:
            name_span = name_tag_container.find('span', class_="hero__primary-text")
            person_data['name'] = name_span.text.strip() if name_span else None
        else:
            person_data['name'] = None
        print(f"DEBUG (Person Parse): Name: {person_data['name']}")

        # Persons IMDb ID
        match_id = re.search(r'/name/(nm\d+)/', person_url)
        person_data['imdb_id'] = match_id.group(1) if match_id else None
        print(f"DEBUG (Person Parse): IMDb ID: {person_data['imdb_id']}")

        # Persons Birth Date
        birth_date_container = soup.find('div', attrs={'data-testid': 'birth-and-death-birthdate'})
        date = None
        if birth_date_container:
            # Find all spans inside, take the text of the second one
            date_spans = birth_date_container.find_all('span', class_=re.compile(r'sc-59a43f1c-2'))
            if len(date_spans) > 1: # Check if at least two spans found
                date_text = date_spans[1].text.strip() # Get text from the second span
                try:
                    date_parts = date_text.split('(')[0].strip().split()
                    if len(date_parts) == 3:
                        month, day, year_text = date_parts
                        day = day.replace(',', '')
                        date = datetime.strptime(f"{month} {day} {year_text}", "%B %d %Y").strftime("%Y-%m-%d")
                    elif len(date_parts) == 2:
                        month, year_text = date_parts
                        date = datetime.strptime(f"{month} {year_text}", "%B %Y").strftime("%Y-%m-01")
                    elif len(date_parts) == 1 and re.match(r'^\d{4}$', date_parts[0]):
                         date = datetime.strptime(date_parts[0], "%Y").strftime("%Y-01-01")
                except (ValueError, IndexError) as e:
                    print(f"Error converting date: {date_text} - {e}")
                    date = None
            else:
                 print(f"Could not find enough spans for birth date.")
        person_data['birth_date'] = date
        print(f"Birth Date Parsed: {person_data['birth_date']}")

        # Persons Bio
        bio_section = soup.find('div', attrs={"data-testid": "bio"})
        if bio_section:
             bio_content_div = bio_section.find('div', class_="ipc-html-content-inner-div") # Find the specific inner div
             person_data['bio'] = bio_content_div.text.strip() if bio_content_div else None
        else:
             # Fallback: Try finding the div directly if testid isn't present/working
             bio_content_div = soup.find('div', class_="ipc-html-content-inner-div")
             person_data['bio'] = bio_content_div.text.strip() if bio_content_div else None
        print(f"DEBUG (Person Parse): Bio Found: {person_data['bio'] is not None}")

        # Persons Filmography
        filmography = []
        # Find the main container using the data-testid
        filmography_section = soup.find('div', attrs={'data-testid': 'Filmography'})
        print(f"Filmography Section Found (using data-testid='Filmography'): {filmography_section is not None}")

        if filmography_section:
            # Find the individual rows
            filmography_rows = filmography_section.find_all('div', class_=re.compile(r'filmo-row'))
            print(f"Found {len(filmography_rows)} filmography rows (using class*='filmo-row').")

            if not filmography_rows: # Fallback if filmo-row isn't found
                    credits_container = filmography_section.find('div', class_=re.compile(r'ipc-accordion__item__content'))
                    if credits_container:
                        filmography_rows = credits_container.find_all('li')
                        print(f"DEBUG (Person Parse): Found {len(filmography_rows)} potential filmography list items as fallback.")


            for row in filmography_rows:
                # Find the link to the movie title within this row
                movie_link = row.find('a', href=re.compile(r'/title/tt\d+/'))
                if movie_link:
                        title_b_tag = row.find('b')
                        if title_b_tag and title_b_tag.find('a') == movie_link:
                            match = re.search(r'/title/(tt\d+)/', movie_link['href'])
                            if match:
                                filmography.append(match.group(1))
                        elif not title_b_tag:
                            match = re.search(r'/title/(tt\d+)/', movie_link['href'])
                            if match:
                                filmography.append(match.group(1))


        person_data['filmography'] = list(set(filmography))
        print(f"Extracted Filmography IDs: {person_data['filmography']}")

    except Exception as e:
        print(f"*** UNEXPECTED Error parsing person page {person_url}: {e} ***")
        import traceback
        traceback.print_exc()
        return None

    print(f"--- Finished Parsing Person Page: {person_url} ---")
    return person_data