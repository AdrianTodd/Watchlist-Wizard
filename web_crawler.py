import requests
from bs4 import BeautifulSoup
import time
import urllib.robotparser
import re

# Project start to make sure I can fetch data using top 250 movies list

# Config
BASE_URL = "https://www.imdb.com"
START_URL = "https://www.imdb.com/chart/top/?ref_=nv_mv_250"  # Top 250 Movies List Page

# --- Fetching and Parsing ---
def fetch_page(url):
    # if not can_fetch(url):
    #     print(f"Skipping (robots.txt): {url}")
    #     return None

    try:
        response = requests.get(url, headers={'User-Agent': 'MyMovieProjectCrawler/1.0'})
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_top250_page(html):
    """Parses the Top 250 Movies page and extracts title, year, and IMDb ID."""
    soup = BeautifulSoup(html, 'html.parser')
    movie_data = []

    # Find the table containing the movie list
    table = soup.find('ul', class_="ipc-metadata-list ipc-metadata-list--dividers-between sc-e22973a9-0 khSCXM compact-list-view ipc-metadata-list--base")
    if not table:
      print("Could not find table")
      return []
    # Find all list items within the table
    movie_items = table.find_all('li', class_='ipc-metadata-list-summary-item')

    for item in movie_items:
        try:
            # Title and link to movie page
            title_tag = item.find('h3', class_="ipc-title__text")
            title = title_tag.text.strip() if title_tag else None

            # Extract IMDb ID from the link
            link_tag = item.find('a', class_="ipc-title-link-wrapper")
            href = link_tag['href'] if link_tag else None
            imdb_id_match = re.search(r'/title/(tt\d+)/', href) if href else None
            imdb_id = imdb_id_match.group(1) if imdb_id_match else None

            print(title_tag), print(href), print(imdb_id)
            if title and imdb_id:
                movie_data.append({
                    'title': title,
                    'imdb_id': imdb_id
                })

        except Exception as e:
            print(f"Error parsing a movie entry: {e}")
            continue  # Continue to the next movie even if one fails

    return movie_data

if __name__ == "__main__":
    html = fetch_page(START_URL)
    if html:
        movies = parse_top250_page(html)
        for movie in movies:
            print(movie)
    else:
        print("Failed to fetch the starting page.")