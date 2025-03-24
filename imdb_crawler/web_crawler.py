
from bs4 import BeautifulSoup
import time
import urllib.robotparser
import imdb_parser
import watchlist_wizard_db
import config
import utils


def crawl():
    """Main crawling function, using Breadth-First Search."""
    watchlist_wizard_db.create_database()
    # --- DEBUGGING: ONLY CRAWL ONE MOVIE PAGE ---
    # test_url = "https://www.imdb.com/title/tt0111161/"  # Shawshank Redemption
    # html = fetch_page(test_url)
    # if html:
    #     parse_movie_page(html, test_url)
    # --- END DEBUGGING SECTION ---
    queue = [config.START_URL]
    visited = set()
    pages_visited = 0

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        html = imdb_parser.fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # BFS Crawl
        # Enqueue movie links from the Top 250 list
        if "chart/top" in url:
            movie_list = soup.find('ul', class_="ipc-metadata-list ipc-metadata-list--dividers-between sc-e22973a9-0 khSCXM compact-list-view ipc-metadata-list--base")
            if movie_list:
                movie_items = movie_list.find_all('li', class_='ipc-metadata-list-summary-item')
                for item in movie_items:
                    link_tag = item.find('a', class_="ipc-title-link-wrapper")
                    href = link_tag.get('href') if link_tag else None
                    if href:
                        absolute_url = urllib.parse.urljoin(config.BASE_URL, href)
                        absolute_url = absolute_url.split("?")[0] # Removes queries
                        if utils.can_fetch(absolute_url) and absolute_url not in queue:  
                            queue.append(absolute_url)


        if "/title/tt" in url:
            movie_data = imdb_parser.parse_movie_page(html, url)
            if movie_data:
                watchlist_wizard_db.insert_movie_data(movie_data)

            # Enqueue people links from movie pages
                for person in movie_data.get('people', []):  # movie_data['people'] might be None
                    if person.get('person_id'): # Use .get()
                        person_url = f"{config.BASE_URL}/name/{person['person_id']}/"
                        if utils.can_fetch(person_url) and person_url not in visited and person_url not in queue:
                            queue.append(person_url)

        # Enqueue movie links from person pages
        if "/name/nm" in url:
            person_data = imdb_parser.parse_person_page(html)
            if person_data:
                watchlist_wizard_db.insert_person_data(person_data)
                for movie_id in person_data.get('filmography', []): 
                    movie_url = f"{config.BASE_URL}/title/{movie_id}/"
                    if utils.can_fetch(movie_url) and movie_url not in visited and movie_url not in queue:
                        queue.append(movie_url)
        pages_visited += 1
        if config.MAX_PAGES and pages_visited >= config.MAX_PAGES:
            break
        time.sleep(config.DELAY)
    print("Crawling complete.")