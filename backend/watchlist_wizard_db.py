import mysql.connector
import config 

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def create_database():
    """Creates the database tables (if they don't exist)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
             raise mysql.connector.Error("Failed to get database connection.")

        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Movies (
                MovieID INT PRIMARY KEY AUTO_INCREMENT,
                Title VARCHAR(255) NOT NULL,
                Year INT,
                Runtime INT,
                Rating DECIMAL(3, 1),
                PlotSummary TEXT,
                PosterURL VARCHAR(255),
                IMDbID VARCHAR(20) UNIQUE,
                ReleaseDate DATE,
                MPAARating VARCHAR(10)
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

        # Pre-populate Roles table
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Actor')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Director')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Writer')")
        cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES ('Producer')")

        conn.commit()
        print("Database and tables setup complete.")

    except mysql.connector.Error as err:
        print(f"Error during database setup: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def insert_movie_data(movie_data):
    """Inserts or updates movie data into the MySQL database."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            raise mysql.connector.Error("Failed to get database connection.")
        cursor = conn.cursor()

        # Check if the movie already exists
        cursor.execute("SELECT MovieID FROM Movies WHERE IMDbID = %s", (movie_data.get('imdb_id'),))
        existing_movie = cursor.fetchone()

        if existing_movie:
            movie_id = existing_movie[0]
            print(f"Movie '{movie_data.get('title', 'N/A')}' already exists (ID: {movie_id}). Updating...")

            # UPDATE the existing movie
            cursor.execute('''
                UPDATE Movies
                SET Title = %s, Year = %s, Runtime = %s, Rating = %s,
                    PlotSummary = %s, PosterURL = %s, ReleaseDate = %s,
                    MPAARating = %s
                WHERE MovieID = %s
            ''', (movie_data.get('title'), movie_data.get('year'), movie_data.get('runtime'),
                  movie_data.get('rating'), movie_data.get('plot_summary'),
                  movie_data.get('poster_url'), movie_data.get('release_date'),
                  movie_data.get('age_restriction'), movie_id))
        else:
            # INSERT a new movie
            cursor.execute('''
                INSERT INTO Movies (Title, Year, Runtime, Rating, PlotSummary, PosterURL, IMDbID, ReleaseDate, MPAARating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (movie_data.get('title'), movie_data.get('year'), movie_data.get('runtime'), movie_data.get('rating'),
                  movie_data.get('plot_summary'), movie_data.get('poster_url'), movie_data.get('imdb_id'),
                  movie_data.get('release_date'), movie_data.get('age_restriction')))
            movie_id = cursor.lastrowid
            if movie_id == 0:
                 cursor.execute("SELECT MovieID FROM Movies WHERE IMDbID = %s", (movie_data.get('imdb_id'),))
                 movie_id = cursor.fetchone()[0]
            print(f"Inserted new movie: {movie_data.get('title', 'N/A')} (ID: {movie_id})")

        # Insert Genres
        for genre_name in movie_data.get('genres', []):
            if not genre_name: continue
            cursor.execute("INSERT IGNORE INTO Genres (GenreName) VALUES (%s)", (genre_name,))
            cursor.execute("SELECT GenreID FROM Genres WHERE GenreName = %s", (genre_name,))
            result = cursor.fetchone()
            if result:
                genre_id = result[0]
                cursor.execute("INSERT IGNORE INTO MovieGenres (MovieID, GenreID) VALUES (%s, %s)", (movie_id, genre_id))

        # Insert People
        seen_people = set()  # Prevent duplicate person entries for this movie
        for person in movie_data.get('people', []):
            person_imdb_id = person.get('person_id')
            person_name = person.get('name')
            person_role = person.get('role')
            if not person_imdb_id or not person_name or not person_role: continue

            if (person_imdb_id, person_role) not in seen_people:
                cursor.execute("INSERT IGNORE INTO People (IMDbID, Name) VALUES (%s, %s)", (person_imdb_id, person_name))

                # Get PersonID
                cursor.execute("SELECT PersonID FROM People WHERE IMDbID = %s AND Name = %s", (person_imdb_id, person_name))
                person_id_result = cursor.fetchone()
                if not person_id_result:
                    print(f"Warning: Could not retrieve PersonID for {person_name}")
                    continue

                person_id = person_id_result[0]

                # Get RoleID
                cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = %s", (person_role,))
                role_result = cursor.fetchone()
                if role_result:
                    role_id = role_result[0]
                else:
                    cursor.execute("INSERT IGNORE INTO Roles (RoleName) VALUES (%s)", (person_role,))
                    cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = %s", (person_role,))
                    role_result = cursor.fetchone()
                    if not role_result:
                         print(f"Warning: Could not retrieve RoleID for {person_role}")
                         continue
                    role_id = role_result[0]

                cursor.execute("INSERT IGNORE INTO MoviePeople (MovieID, PersonID, RoleID) VALUES (%s, %s, %s)", (movie_id, person_id, role_id))
                seen_people.add((person_imdb_id, person_role))

        # Insert Plot Keywords
        for keyword_text in movie_data.get('plot_keywords', []):
            if not keyword_text: continue # Skip empty keywords
            cursor.execute("INSERT IGNORE INTO PlotKeywords (Keyword) VALUES (%s)", (keyword_text,))
            cursor.execute("SELECT KeywordID FROM PlotKeywords WHERE Keyword = %s", (keyword_text,))
            result = cursor.fetchone()
            if result:
                keyword_id = result[0]
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
        conn = get_db_connection()
        if not conn:
            raise mysql.connector.Error("Failed to get database connection.")
        cursor = conn.cursor()

        person_imdb_id = person_data.get('imdb_id')
        person_name = person_data.get('name')
        if not person_imdb_id or not person_name:
             print(f"Skipping person insert due to missing ID or Name: {person_data}")
             return

        # Insert person using INSERT IGNORE (using IMDbID and Name for uniqueness)
        cursor.execute("""
            INSERT IGNORE INTO People (IMDbID, Name, BirthDate, Bio)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE BirthDate=VALUES(BirthDate), Bio=VALUES(Bio)
        """, (person_imdb_id, person_name, person_data.get('birth_date'), person_data.get('bio')))
        conn.commit()
        print(f"Inserted/Updated person: {person_name}")

        # Get the PersonID
        cursor.execute("SELECT PersonID FROM People WHERE IMDbID = %s AND Name = %s", (person_imdb_id, person_name))
        result = cursor.fetchone()
        if result:
            person_id = result[0]
        else:
            print(f"Error: Could not retrieve PersonID for {person_name}")
            return

        print(f"  Potential Filmography for {person_name} (PersonID: {person_id}):")
        for movie_imdb_id in person_data.get('filmography', []):
            print(f"    - Movie IMDb ID: {movie_imdb_id}")

    except mysql.connector.Error as err:
        print(f"Database error (person insertion): {err}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_all_movies(limit=250, offset=0, search_term=None, genre_filter=None, keyword_filter=None, actor_filter=None):
    """Fetches a list of movies with pagination and filtering."""
    conn = get_db_connection()
    if not conn:
        return []
    movies = []
    try:
        cursor = conn.cursor(dictionary=True)

        # Base query
        sql = """
            SELECT DISTINCT m.MovieID, m.Title, m.Year, m.Rating, m.PosterURL, m.IMDbID
            FROM Movies m
            LEFT JOIN MovieGenres mg ON m.MovieID = mg.MovieID
            LEFT JOIN Genres g ON mg.GenreID = g.GenreID
            LEFT JOIN MovieKeywords mk ON m.MovieID = mk.MovieID
            LEFT JOIN PlotKeywords pk ON mk.KeywordID = pk.KeywordID
            LEFT JOIN MoviePeople mp ON m.MovieID = mp.MovieID
            LEFT JOIN People p ON mp.PersonID = p.PersonID
            LEFT JOIN Roles r ON mp.RoleID = r.RoleID
        """

        where_clauses = []
        params = []

        # Add search term filter (searches Title and PlotSummary)
        if search_term:
            where_clauses.append("(m.Title LIKE %s OR m.PlotSummary LIKE %s)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        # Add genre filter
        if genre_filter:
            where_clauses.append("g.GenreName = %s")
            params.append(genre_filter)

        # Add keyword filter
        if keyword_filter:
             where_clauses.append("pk.Keyword LIKE %s")
             params.append(f"%{keyword_filter}%")

        # Add actor filter
        if actor_filter:
            where_clauses.append("(p.Name LIKE %s AND r.RoleName = 'Actor')")
            params.append(f"%{actor_filter}%")

        # Combine WHERE clauses
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        # Add ordering and pagination
        sql += " ORDER BY m.Rating DESC, m.Year DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        print(f"Executing SQL: {sql}")
        print(f"With Params: {params}")

        cursor.execute(sql, tuple(params))
        movies = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Error fetching filtered movies: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return movies

def get_movie_by_imdb_id(imdb_id):
    """Fetches a single movie by its IMDb ID, including related data."""
    conn = get_db_connection()
    if not conn:
        return None
    movie_data = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Fetch basic movie info
        cursor.execute("SELECT * FROM Movies WHERE IMDbID = %s", (imdb_id,))
        movie_data = cursor.fetchone()

        if movie_data:
            movie_id = movie_data['MovieID']

            # Fetch genres
            cursor.execute("""
                SELECT g.GenreName
                FROM Genres g
                JOIN MovieGenres mg ON g.GenreID = mg.GenreID
                WHERE mg.MovieID = %s
            """, (movie_id,))
            genres = cursor.fetchall()
            movie_data['genres'] = [g['GenreName'] for g in genres]

            # Fetch people
            cursor.execute("""
                SELECT p.Name, p.IMDbID as PersonIMDbID, r.RoleName
                FROM People p
                JOIN MoviePeople mp ON p.PersonID = mp.PersonID
                JOIN Roles r ON mp.RoleID = r.RoleID
                WHERE mp.MovieID = %s
            """, (movie_id,))
            people = cursor.fetchall()
            movie_data['people'] = people

            # Fetch keywords
            cursor.execute("""
                SELECT pk.Keyword
                FROM PlotKeywords pk
                JOIN MovieKeywords mk ON pk.KeywordID = mk.KeywordID
                WHERE mk.MovieID = %s
            """, (movie_id,))
            keywords = cursor.fetchall()
            movie_data['plot_keywords'] = [k['Keyword'] for k in keywords]

    except mysql.connector.Error as err:
        print(f"Error fetching movie details: {err}")
        movie_data = None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return movie_data

def get_all_genres():
    """Fetches all unique genre names."""
    conn = get_db_connection()
    if not conn: return []
    genres = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT GenreName FROM Genres ORDER BY GenreName")
        genres = [row['GenreName'] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        print(f"Error fetching genres: {err}")
    finally:
         if conn.is_connected():
            cursor.close()
            conn.close()
    return genres