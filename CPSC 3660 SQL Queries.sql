#1)Show all tables and explain how they are related to one another (keys, triggers, etc.)
-- Showing all tables in the database:
SHOW TABLES;

-- Describing each table to show structure and keys:
DESCRIBE movies;
-- Explanation: Stores core movie details.
-- PK: MovieID (Auto-incrementing primary key)
-- UNIQUE: IMDbID (Ensures each movie from IMDb is unique)
-- FKs: None

DESCRIBE genres;
-- Explanation: Stores distinct movie genres.
-- PK: GenreID (Auto-incrementing primary key)
-- UNIQUE: GenreName (Ensures genre names are unique)
-- FKs: None

DESCRIBE moviegenres;
-- Explanation: Linking table for the many-to-many relationship between Movies and Genres.
-- PK: (MovieID, GenreID) (Composite primary key, ensures a movie can't have the same genre twice)
-- FKs: MovieID -> Movies(MovieID) (ON DELETE CASCADE: If a movie is deleted, its genre links are removed)
--      GenreID -> Genres(GenreID) (ON DELETE CASCADE: If a genre is deleted, its links to movies are removed)

DESCRIBE people;
-- Explanation: Stores information about people (actors, directors, writers).
-- PK: PersonID (Auto-incrementing primary key)
-- UNIQUE: (IMDbID, Name) (Ensures unique combination of IMDb person ID and name)
-- FKs: None

DESCRIBE roles;
-- Explanation: Stores distinct roles people can have (Actor, Director, Writer).
-- PK: RoleID (Auto-incrementing primary key)
-- UNIQUE: RoleName (Ensures role names are unique)
-- FKs: None

DESCRIBE MoviePeople;
-- Explanation: Linking table for the many-to-many relationship between Movies, People, and Roles.
-- PK: (MovieID, PersonID, RoleID) (Composite primary key, ensures a person doesn't have the same role in the same movie twice)
-- FKs: MovieID -> Movies(MovieID) (ON DELETE CASCADE)
--      PersonID -> People(PersonID) (ON DELETE CASCADE)
--      RoleID -> Roles(RoleID) (ON DELETE CASCADE)

DESCRIBE plotkeywords;
-- Explanation: Stores distinct plot keywords.
-- PK: KeywordID (Auto-incrementing primary key)
-- UNIQUE: Keyword (Ensures keywords are unique)
-- FKs: None

DESCRIBE moviekeywords;
-- Explanation: Linking table for the many-to-many relationship between Movies and PlotKeywords.
-- PK: (MovieID, KeywordID) (Composite primary key)
-- FKs: MovieID -> Movies(MovieID) (ON DELETE CASCADE)
--      KeywordID -> PlotKeywords(KeywordID) (ON DELETE CASCADE)

-- No triggers are explicitly defined or necessary for the basic functionality of this schema. 
-- Referential integrity and cascading actions are handled primarily through Foreign Key constraints with ON DELETE CASCADE.

#2)A basic retrieval query
-- Retrieve the Title and Year of movies released in or after the year 2000.
SELECT
    Title,
    Year
FROM
    Movies
WHERE
    Year >= 2000;


#3)A retrieval query with ordered results
-- Retrieve the Title, Year, and Rating of all movies, ordered by Rating (highest first)
-- and then by Year (most recent first).
SELECT
    Title,
    Year,
    Rating
FROM
    Movies
ORDER BY
    Rating DESC,
    Year DESC;
    
    
#4)A nested retrieval query
-- Retrieve the Title of movies that have a rating higher than the average rating of all movies.
SELECT
    Title
FROM
    Movies
WHERE
    Rating > (SELECT AVG(Rating) FROM Movies WHERE Rating IS NOT NULL); -- Subquery calculates average rating


#5)A retrieval query using joined tables
-- Retrieve the movie Title, person's Name, and their Role for a specific movie (e.g., 'The Dark Knight').
-- This demonstrates joining Movies, MoviePeople, People, and Roles tables.
SELECT
    m.Title AS MovieTitle,
    p.Name AS PersonName,
    r.RoleName
FROM
    Movies m
JOIN
    MoviePeople mp ON m.MovieID = mp.MovieID
JOIN
    People p ON mp.PersonID = p.PersonID
JOIN
    Roles r ON mp.RoleID = r.RoleID
WHERE
    m.Title = 'The Dark Knight';


#6)An update operation with any necessary triggers
UPDATE
    Movies
SET
    Rating = 6.8  -- Set the new rating value
WHERE
    IMDbID = 'tt0468569'; -- Replace with the IMDbID of the movie you want to update

-- Verify the update
SELECT Title, Rating FROM Movies WHERE IMDbID = 'tt0468569';


#7)A deletion operation with any necessary triggers
-- Delete a specific movie 
-- ON DELETE CASCADE Explanation: Because the linking tables (MovieGenres, MoviePeople, MovieKeywords)
-- have foreign keys referencing Movies.MovieID with 'ON DELETE CASCADE', deleting a movie
-- from the Movies table will automatically delete all corresponding rows in those linking tables.
DELETE FROM
    Movies
WHERE
    Title = 'The Dark Knight';

-- Verify the deletion (optional, check multiple tables)
SELECT * FROM Movies WHERE Title = 'The Dark Knight'; -- This should fail if delete worked.
SELECT * FROM MovieGenres WHERE MovieID = 3; -- This should return empty if cascade worked.
SELECT * FROM MoviePeople WHERE MovieID = 3; -- This should return empty if cascade worked.
SELECT * FROM MovieKeywords WHERE MovieID = 3; -- This should return empty if cascade worked.
