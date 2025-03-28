import requests
import urllib.robotparser
from bs4 import BeautifulSoup
import re
from datetime import datetime
import utils

def fetch_page(url):
    if not utils.can_fetch(url):
        print(f"Skipping (robots.txt): {url}")
        return None
    try:
        response = requests.get(url, headers={'User-Agent': 'MyMovieProjectCrawler/1.0'})
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_movie_page(html, movie_url):
    """Parses an IMDb movie page, robust to variations in HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    movie_data = {}

    try:
        # Title
        title_tag = soup.find('h1', attrs={"data-testid": "hero__pageTitle"})
        movie_data['title'] = title_tag.text.strip() if title_tag else None

        # Year, Runtime, Age Restriction
        twitter_title_meta = soup.find('meta', attrs={'property': 'twitter:title'})
        twitter_desc_meta = soup.find('meta', attrs={'property': 'twitter:description'})

        if twitter_title_meta:
            title_content = twitter_title_meta['content']
            # Extract year using regex
            year_match = re.search(r'\((\d{4})\)', title_content)
            movie_data['year'] = int(year_match.group(1)) if year_match else None
        else:
             movie_data['year'] = None

        if twitter_desc_meta:
            desc_content = twitter_desc_meta['content']
             # Extract runtime and age restriction
            runtime_age_match = re.search(r'(\d+h\s*\d+m|\d+h|\d+m)\s*\|\s*([A-Za-z0-9-]+)', desc_content)

            if runtime_age_match:
                runtime_text = runtime_age_match.group(1)
                age_restriction = runtime_age_match.group(2)

                movie_data['age_restriction'] = age_restriction

                # Runtime conversion
                match = re.search(r'(\d+)h', runtime_text)
                hours = int(match.group(1)) if match else 0
                match = re.search(r'(\d+)m', runtime_text)
                minutes = int(match.group(1)) if match else 0
                movie_data['runtime'] = hours * 60 + minutes
            else:
                movie_data['runtime'] = None
                movie_data['age_restriction'] = None
        else:
            movie_data['runtime'] = None
            movie_data['age_restriction'] = None

        # print(f"movie_data: {movie_data}")

        # IMDB Rating
        rating_wrapper = soup.find('div', {"data-testid": "hero-rating-bar__aggregate-rating__score"})
        if rating_wrapper:
            rating_tag = rating_wrapper.find('span')
            movie_data['rating'] = float(rating_tag.text.strip()) if rating_tag else None
        else:
            movie_data['rating'] = None

        # Plot Summary
        plot_summary_tag = soup.find('span', attrs={"data-testid": "plot-xl"})
        movie_data['plot_summary'] = plot_summary_tag.text.strip() if plot_summary_tag else None

        # Poster URL
        poster_tag = soup.find('img', class_='ipc-image')
        movie_data['poster_url'] = poster_tag['src'] if poster_tag and 'src' in poster_tag.attrs else None

        # IMDb ID
        match = re.search(r'/title/(tt\d+)/', movie_url)
        movie_data['imdb_id'] = match.group(1) if match else None

        # Release Date
        release_date_tag = soup.find('a', string='Release date')
        date = None
        if release_date_tag:
            parent_release_date = release_date_tag.find_parent('li')
            if parent_release_date:
                date_container = parent_release_date.find('div', class_='ipc-metadata-list-item__content-container')
                if date_container:
                    date_text = date_container.find('a').text.strip()
                    try:
                        date_parts = date_text.split('(')[0].strip().split()
                        if len(date_parts) == 3:
                            month, day, year = date_parts
                            date = datetime.strptime(f"{month} {day} {year}", "%B %d, %Y").strftime("%Y-%m-%d")
                        elif len(date_parts) == 2:
                            month, year = date_parts
                            date = datetime.strptime(f"{month} {year}", "%B %Y").strftime("%Y-%m-01")
                        elif len(date_parts) == 1:
                            date = datetime.strptime(date_parts[0], "%Y").strftime("%Y-01-01")
                    except (ValueError, IndexError) as e:
                        print(f"Error converting date: {date_text} - {e}")
                        date = None
        movie_data['release_date'] = date

        # Genres
        genres = []
        genre_section = soup.find('div', class_ = 'ipc-chip-list__scroller')
        if genre_section:
            genre_tags = genre_section.find_all('span', class_="ipc-chip__text")
            for tag in genre_tags:
                genres.append(tag.text.strip())
        movie_data['genres'] = genres

        # People
        people = []
        seen_people = set()
        credits = soup.find_all('li', {'data-testid': 'title-pc-principal-credit'})
        for credit in credits:
            label_span = credit.find('a', class_='ipc-metadata-list-item__label')
            if label_span:
                label = label_span.get_text(strip=True)
                role = None  # Initialize role
                if label == 'Director' or label == 'Directors':
                    role = 'Director'
                elif label == 'Writer' or label == 'Writers':
                    role = 'Writer'
                elif label == 'Stars' or label == 'Star':
                    role = 'Actor'  # Always use 'Actor'

                if role:  # Only proceed if a valid role was found
                    name_links = credit.find_all('a', class_='ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link')
                    for name_link in name_links:
                        person_id = name_link['href'].split('/')[2]
                        name = name_link.get_text(strip=True)
                        #print(f"person_id: {person_id}, name: {name}, role: {role}")
                        if (person_id, role) not in seen_people: # Use tuple for uniqueness
                            people.append({'person_id': person_id, 'name': name, 'role': role})
                            seen_people.add((person_id, role))  # Add to seen_people

        movie_data['people'] = people
        #print(f"people: {people}")

        # Plot Keywords
        if movie_data['plot_summary']:
            keywords = utils.extract_keywords(movie_data['plot_summary'])
            movie_data['plot_keywords'] = keywords
        else:
            movie_data['plot_keywords'] = []
            
    except Exception as e:
        print(f"Error parsing {movie_url}: {e}")
        return None

    return movie_data

def parse_person_page(html):
    """Parses a person page and extracts name, birth date, bio, and filmography."""
    soup = BeautifulSoup(html, 'html.parser')
    person_data = {}

    try:
        # Name
        name_tag = soup.find('span', class_="hero__primary-text")
        person_data['name'] = name_tag.text.strip() if name_tag else None

        # # IMDb ID (extract from URL)
        match = re.search(r'/name/(nm\d+)/', html)
        person_data['imdb_id'] = match.group(1) if match else None

        # Birth Date
        birthdate_tag = soup.find('div', class_="sc-59a43f1c-1 dOuYzr")
        if birthdate_tag:
            date_text = birthdate_tag.find_all('span', class_="sc-59a43f1c-2 bMLVWg")
            try:
                for date in date_text:
                    if date != "Born":
                        date_text = date.text.strip()
                        date_parts = date_text.split('(')[0].strip().split()
                        if len(date_parts) == 3:
                            month, day, year = date_parts
                            date = datetime.strptime(f"{month} {day} {year}", "%B %d, %Y").strftime("%Y-%m-%d")
                            person_data['birth_date'] = date
                        elif len(date_parts) == 2:
                            month, year = date_parts
                            date = datetime.strptime(f"{month} {year}", "%B %Y").strftime("%Y-%m-01")
                
            except (ValueError, IndexError):
                person_data['birth_date'] = None
        else:
            person_data['birth_date'] = None

        # Bio
        bio_tag = soup.find('div', class_="ipc-html-content-inner-div")
        person_data['bio'] = bio_tag.text.strip() #if bio_tag else None
        print(f"bio: {person_data['bio']}")

        # Filmography (Movie IMDb IDs)
        filmography = []
        filmography_div = soup.find('div', id=re.compile(r'filmography-category-section'))
        if filmography_div:
            for item in filmography_div.find_all('a', href=re.compile(r'/title/tt\d+/')):
                match = re.search(r'/title/(tt\d+)/', item['href'])
                if match:
                    filmography.append(match.group(1))
        person_data['filmography'] = filmography


    except Exception as e:
        print(f"Error parsing person page: {e}")
        return None

    return person_data