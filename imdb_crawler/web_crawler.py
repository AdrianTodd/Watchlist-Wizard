from bs4 import BeautifulSoup
import time
import urllib.parse
import urllib.robotparser
try:
    from . import imdb_parser
    from . import watchlist_wizard_db
    from . import config
    from . import utils
except ImportError:
    import imdb_parser
    import watchlist_wizard_db
    import config
    import utils
import re

def crawl():
    """Main crawling function, using BFS and Selenium for list pages."""
    watchlist_wizard_db.create_database()
    queue = [config.START_URL]  # Seed the queue with the start URL, I am using the Top 250 list from IMDB
    visited = set() # Set to keep track of visited URLs to prevent revisiting the same page
    pages_visited = 0

    print(f"Starting crawl with START_URL: {config.START_URL}")
    print(f"MAX_PAGES set to: {config.MAX_PAGES}")

    while queue and (pages_visited < config.MAX_PAGES):
        url = queue.pop(0) # Dequeue the next URL to process from the front of the queue
        print(f"\n--- Processing URL ({pages_visited + 1}/{config.MAX_PAGES}): {url} ---")
        print(f"Queue size: {len(queue)}, Visited size: {len(visited)}")

        if url in visited:
            print(f"URL: {url} --- URL already visited. Skipping.")
            continue
        visited.add(url)

        html = None
        # Comment out for demo so that you can see the different pages being crawled.
        if "chart/top" in url: # Selenium is needed to navigate the Top 250 list page due to dynamic content loading otherwise only the first 25 movies are fetched
            print("  Using Selenium to fetch list page...")
            html = imdb_parser.fetch_page_with_selenium(url)
        else: # Use regular requests for movie/person detail pages, Selenium is not needed here
            print("  Using requests to fetch page...")
            html = imdb_parser.fetch_page(url)

        if not html:
            print(f"Failed to fetch HTML for URL: {url} --- Skipping.")
            continue

        pages_visited += 1
        soup = BeautifulSoup(html, 'html.parser')
        movie_data = None
        person_data = None

        # Extract relevant links from top 250 page
        if "chart/top" in url:
            print("  Processing Top 250 list page...")
            links_found_on_page = 0
            main_content = soup.find('main')
            search_area = main_content if main_content else soup

            # Use the selector that finds list items directly
            movie_items = search_area.find_all('li', class_=re.compile(r"ipc-metadata-list-summary-item"))
            print(f"  Found {len(movie_items)} potential movie items on list page.")

            if not movie_items: 
                 print("  WARNING: No movie items found. Check Top 250 page structure/selectors. They may have changed.")

            for item in movie_items:
                link_tag = item.find('a', class_=re.compile(r"ipc-title-link-wrapper"))
                href = link_tag.get('href') if link_tag else None
                if href:
                    absolute_url = urllib.parse.urljoin(config.BASE_URL, href)
                    absolute_url = absolute_url.split("?")[0]
                    if absolute_url not in visited and absolute_url not in queue:
                         if utils.can_fetch(absolute_url):
                            queue.append(absolute_url)
                            links_found_on_page += 1
            print(f"  Found and queued {links_found_on_page} new movie links.")

        # Extract links from Movie Detail Pages
        elif "/title/tt" in url:
            print(f"  Processing movie page...")
            movie_data = imdb_parser.parse_movie_page(html, url)
            if movie_data:
                print(f"  Parsing successful. Inserting/Updating movie: {movie_data.get('title', 'N/A')}")
                watchlist_wizard_db.insert_movie_data(movie_data)

                # Enqueue people links
                links_found_on_page = 0
                for person in movie_data.get('people', []):
                    if person.get('person_id'):
                        person_url = f"{config.BASE_URL}/name/{person['person_id']}/"
                        if person_url not in visited and person_url not in queue:
                            if utils.can_fetch(person_url):
                                queue.append(person_url)
                                links_found_on_page += 1
                print(f"  Found and queued {links_found_on_page} new person links.")
            else:
                 print(f"  Parsing failed for movie page.")

        # Extract links from Person Detail Pages
        elif "/name/nm" in url:
            print(f"  Processing person page...")
            person_data = imdb_parser.parse_person_page(html, url)
            if person_data:
                 print(f"  Parsing successful. Inserting/Updating person: {person_data.get('name', 'N/A')}")
                 watchlist_wizard_db.insert_person_data(person_data)

                 # Enqueue movie links
                 links_found_on_page = 0
                 for movie_imdb_id in person_data.get('filmography', []):
                     movie_url_from_person = f"{config.BASE_URL}/title/{movie_imdb_id}/"
                     movie_url_from_person = movie_url_from_person.split("?")[0]
                     if movie_url_from_person not in visited and movie_url_from_person not in queue:
                         if utils.can_fetch(movie_url_from_person):
                             queue.append(movie_url_from_person)
                             links_found_on_page += 1
                 print(f"  Found and queued {links_found_on_page} new movie links from person page.")
            else:
                  print(f"  Parsing failed for person page.")

        # Limit the number of requests to avoid overwhelming the server, unlikely with a large website like IMDB but still good practice when crawling
        time.sleep(config.DELAY)

    print("-" * 20) # Make it easy to spot the end of the crawl in terminal output
    print(f"Crawling loop finished. Visited {len(visited)} pages.")
    print("-" * 20)

if __name__ == "__main__":
    try:
        import nltk
        nltk.data.find('corpora/stopwords')
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        import nltk
        print("NLTK data not found. Downloading...")
        nltk.download('stopwords')
        nltk.download('punkt')
        print("NLTK data downloaded.")

    crawl()