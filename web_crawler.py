import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import urllib.robotparser
import re
import mysql.connector
import os

# Config

BASE_URL = "https://www.imdb.com"
START_URL = "https://www.imdb.com/chart/top/?ref_=nv_mv_250"
DELAY = 2
MAX_PAGES = 10 

# Database Config
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER') 
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# robots.txt Handling
rp = urllib.robotparser.RobotFileParser()
rp.set_url(BASE_URL + "/robots.txt")
rp.read()

def can_fetch(url):
    return rp.can_fetch("*", url)

# Fetching and Parsing

def fetch_page(url):
    if not can_fetch(url):
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



        print(f"movie_data: {movie_data}")

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
        genre_section = soup.find('div', {'data-testid': 'genres'})
        if genre_section:
            genre_tags = genre_section.find_all('a', class_="ipc-chip")
            for tag in genre_tags:
                genres.append(tag.text.strip())
        movie_data['genres'] = genres

        # People
        people = []
        seen_people = set()
        credits = soup.find_all('li', {'data-testid': 'title-pc-principal-credit'})
        for credit in credits:
            label = credit.find('span', {'class': 'ipc-metadata-list-item__label ipc-metadata-list-item__label--btn'})
            if label and (label.text.strip() == 'Director' or label.text.strip() == 'Writers' or label.text.strip() == 'Stars'):
                role = label.text.strip()
                if role == "Writers":
                    role = "Writer"
                if role == "Stars":
                    role = "Actor"
                name_tags = credit.find_all('a', {'class': 'ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link'})
                for name_tag in name_tags:
                    person_id = name_tag.get('href').split('/')[2]
                    name = name_tag.text.strip()
                    if (person_id, role) not in seen_people:
                        people.append({'person_id': person_id, 'name': name, 'role': role})
                        seen_people.add((person_id, role))
        movie_data['people'] = people

        # Plot Keywords
        keywords = []
        keyword_section = soup.find('div', {'data-testid': 'keywords'})
        if keyword_section:
            keyword_tags = keyword_section.find_all('span', class_="ipc-chip__text")
            for tag in keyword_tags:
                keywords.append(tag.text.strip())
        movie_data['plot_keywords'] = keywords
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
        name_tag = soup.find('span', class_="sc-b45a5631-1 hjhOdL")
        person_data['name'] = name_tag.text.strip() if name_tag else None

        # IMDb ID (extract from URL)
        match = re.search(r'/name/(nm\d+)/', html)
        person_data['imdb_id'] = match.group(1) if match else None

        # Birth Date
        birthdate_tag = soup.find('li', {'data-testid': 'person-birthdate'})
        if birthdate_tag:
            date_text = birthdate_tag.find('a').text.strip()
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
                person_data['birth_date'] = date
            except (ValueError, IndexError):
                person_data['birth_date'] = None
        else:
            person_data['birth_date'] = None

        # Bio
        bio_tag = soup.find('p', class_="sc-ae7955ff-6 hPWJmE")
        person_data['bio'] = bio_tag.text.strip() if bio_tag else None

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

# Database Operations

def create_database():
    """Creates the database tables (if they don't exist)."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Movies (
                MovieID INT PRIMARY KEY AUTO_INCREMENT,
                Title VARCHAR(255) NOT NULL,
                Year INT,
                AgeRestriction VARCHAR(20),
                Runtime VARCHAR(20),
                Rating DECIMAL(3, 1),
                PlotSummary TEXT,
                PosterURL VARCHAR(255),
                IMDbID VARCHAR(20) UNIQUE,
                ReleaseDate DATE
            )
        ''')
        print("Movies table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Genres (
                GenreID INT PRIMARY KEY AUTO_INCREMENT,
                GenreName VARCHAR(50) NOT NULL UNIQUE
            )
        ''')
        print("Genres table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS MovieGenres (
                MovieID INT,
                GenreID INT,
                PRIMARY KEY (MovieID, GenreID),
                FOREIGN KEY (MovieID) REFERENCES Movies(MovieID) ON DELETE CASCADE,
                FOREIGN KEY (GenreID) REFERENCES Genres(GenreID) ON DELETE CASCADE
            )
        ''')
        print("MovieGenres table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS People (
                PersonID INT PRIMARY KEY AUTO_INCREMENT,
                IMDbID VARCHAR(20),
                Name VARCHAR(255) NOT NULL,
                BirthDate DATE NULL,
                Bio TEXT NULL,
                UNIQUE (IMDbID, Name)
            )
        ''')
        print("People table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Roles (
                RoleID INT PRIMARY KEY AUTO_INCREMENT,
                RoleName VARCHAR(50) NOT NULL UNIQUE
            )
        ''')
        print("Roles table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS MoviePeople (
                MovieID INT,
                PersonID INT,
                RoleID INT,
                PRIMARY KEY (MovieID, PersonID, RoleID),
                FOREIGN KEY (MovieID) REFERENCES Movies(MovieID) ON DELETE CASCADE,
                FOREIGN KEY (PersonID) REFERENCES People(PersonID) ON DELETE CASCADE,
                FOREIGN KEY (RoleID) REFERENCES Roles(RoleID) ON DELETE CASCADE
            )
        ''')
        print("MoviePeople table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS PlotKeywords (
                KeywordID INT PRIMARY KEY AUTO_INCREMENT,
                Keyword VARCHAR(50) NOT NULL UNIQUE
            )
        ''')
        print("PlotKeywords table created (or already exists).")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS MovieKeywords (
                MovieID INT,
                KeywordID INT,
                PRIMARY KEY (MovieID, KeywordID),
                FOREIGN KEY (MovieID) REFERENCES Movies(MovieID) ON DELETE CASCADE,
                FOREIGN KEY (KeywordID) REFERENCES PlotKeywords(KeywordID) ON DELETE CASCADE
            )
        ''')
        print("MovieKeywords table created (or already exists).")

        # Insert default Roles (important to do this only *once*)
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Actor')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Director')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Writer')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Producer')")


        conn.commit()
        print("Database and tables created (or already existed).")

    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
    finally:
        if conn and conn.is_connected():
            if cursor:  # Check if cursor is defined
                cursor.close()
            conn.close()



def insert_movie_data(movie_data):
    """Inserts movie data into the MySQL database, handling duplicates."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()

        # Check if themovie already exists
        cursor.execute("SELECT MovieID FROM Movies WHERE IMDbID = %s", (movie_data['imdb_id'],))
        existing_movie = cursor.fetchone()

        if existing_movie:
            movie_id = existing_movie[0]
            print(f"Movie already exists (ID: {movie_id}). Updating...")

            # UPDATE the existing movie
            cursor.execute('''
                UPDATE Movies
                SET Title = %s, Year = %s, AgeRestriction = %s, Runtime = %s, Rating = %s,
                    PlotSummary = %s, PosterURL = %s, ReleaseDate = %s
                WHERE MovieID = %s
            ''', (movie_data['title'], movie_data['year'], movie_data['age_restriction'], movie_data['runtime'],
                  movie_data['rating'], movie_data['plot_summary'],
                  movie_data['poster_url'], movie_data['release_date'], movie_id))
        else:
            # INSERT a new movie
            cursor.execute('''
                INSERT INTO Movies (Title, Year, AgeRestriction, Runtime, Rating, PlotSummary, PosterURL, IMDbID, ReleaseDate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (movie_data['title'], movie_data['year'], movie_data['age_restriction'], movie_data['runtime'], movie_data['rating'],
                  movie_data['plot_summary'], movie_data['poster_url'], movie_data['imdb_id'], movie_data['release_date']))
            movie_id = cursor.lastrowid
            print(f"Inserted new movie: {movie_data['title']} (ID: {movie_id})")

        # Insert Genres
        for genre_name in movie_data['genres']:
            cursor.execute("INSERT IGNORE INTO Genres (GenreName) VALUES (%s)", (genre_name,))
            # Always get GenreID, even if it was just inserted or already existed
            cursor.execute("SELECT GenreID FROM Genres WHERE GenreName = %s", (genre_name,))
            result = cursor.fetchone()
            if result:
                genre_id = result[0]
                cursor.execute("INSERT IGNORE INTO MovieGenres (MovieID, GenreID) VALUES (%s, %s)", (movie_id, genre_id))

        # Insert People
        seen_people = set()  # Prevent duplicate person entries
        for person in movie_data['people']:
            if (person['person_id'], person['role']) not in seen_people:
                cursor.execute("INSERT IGNORE INTO People (IMDbID, Name) VALUES (%s, %s)", (person['person_id'], person['name']))

                # Get PersonID
                cursor.execute("SELECT PersonID FROM People WHERE IMDbID = %s AND Name = %s", (person['person_id'], person['name']))
                person_id = cursor.fetchone()[0]

                # Get RoleID
                cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = %s", (person['role'],))
                role_result = cursor.fetchone()
                if role_result:
                    role_id = role_result[0]
                else:
                    # Role doesn't exist yet so it will be inserted
                    cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES (%s)", (person['role'],))
                    cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = %s", (person['role'],))  # Get newly inserted ID.
                    role_id = cursor.fetchone()[0]

                cursor.execute("INSERT IGNORE INTO MoviePeople (MovieID, PersonID, RoleID) VALUES (%s, %s, %s)", (movie_id, person_id, role_id))
                seen_people.add((person['person_id'], person['role']))


        # Insert Plot Keywords
        for keyword_text in movie_data['plot_keywords']:
            cursor.execute("INSERT IGNORE INTO PlotKeywords (Keyword) VALUES (%s)", (keyword_text,))
            # Get the KeywordID
            cursor.execute("SELECT KeywordID FROM PlotKeywords WHERE Keyword = %s", (keyword_text,))
            keyword_id = cursor.fetchone()[0]
            cursor.execute("INSERT IGNORE INTO MovieKeywords (MovieID, KeywordID) VALUES (%s, %s)", (movie_id, keyword_id))

        conn.commit()

    except mysql.connector.Error as err:
        print(f"Database error (movie insertion): {err}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()



def insert_person_data(person_data):
    """Inserts person data into the MySQL database."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()

        # Insert person (using IMDbID and Name for uniqueness)
        cursor.execute("""
            INSERT IGNORE INTO People (IMDbID, Name, BirthDate, Bio)
            VALUES (%s, %s, %s, %s)
        """, (person_data.get('imdb_id'), person_data['name'], person_data.get('birth_date'), person_data.get('bio')))
        conn.commit()

        # Get the PersonID (select based on IMDbID and Name)
        cursor.execute("SELECT PersonID FROM People WHERE IMDbID = %s AND Name = %s", (person_data.get('imdb_id'), person_data['name']))
        result = cursor.fetchone()
        if result:
            person_id = result[0]
        else:
            print(f"Error: Could not retrieve PersonID for {person_data['name']}")
            return  # Exit if PersonID not found

    except mysql.connector.Error as err:
        print(f"Database error (person insertion): {err}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def crawl():
    """Main crawling function, using Breadth-First Search."""
    create_database()
    # --- DEBUGGING: ONLY CRAWL ONE MOVIE PAGE ---
    # test_url = "https://www.imdb.com/title/tt0111161/"  # Shawshank Redemption
    # html = fetch_page(test_url)
    # if html:
    #     parse_movie_page(html, test_url)
    # --- END DEBUGGING SECTION ---
    queue = [START_URL]
    visited = set()
    pages_visited = 0

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        html = fetch_page(url)
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
                        absolute_url = urllib.parse.urljoin(BASE_URL, href)
                        absolute_url = absolute_url.split("?")[0] # Removes queries
                        if can_fetch(absolute_url) and absolute_url not in queue:  
                            queue.append(absolute_url)


        if "/title/tt" in url:
            movie_data = parse_movie_page(html, url)
            if movie_data:
                insert_movie_data(movie_data)

            # Enqueue people links from movie pages
                for person in movie_data.get('people', []):  # movie_data['people'] might be None
                    if person.get('person_id'): # Use .get()
                        person_url = f"{BASE_URL}/name/{person['person_id']}/"
                        if can_fetch(person_url) and person_url not in visited and person_url not in queue:
                            queue.append(person_url)

        # Enqueue movie links from person pages
        if "/name/nm" in url:
            person_data = parse_person_page(html)
            if person_data:
                insert_person_data(person_data)
                for movie_id in person_data.get('filmography', []): 
                    movie_url = f"{BASE_URL}/title/{movie_id}/"
                    if can_fetch(movie_url) and movie_url not in visited and movie_url not in queue:
                        queue.append(movie_url)
        pages_visited += 1
        if MAX_PAGES and pages_visited >= MAX_PAGES:
            break
        time.sleep(DELAY)

if __name__ == "__main__":
    crawl()
    print("Crawling complete.")