import mysql.connector
import config  # Import configuration

# Database Operations

def create_database():
    """Creates the database tables (if they don't exist)."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
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
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
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
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
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