-- Watchlist Wizard Tables

CREATE TABLE Movies (
    MovieID INT PRIMARY KEY AUTO_INCREMENT,
    Title VARCHAR(255) NOT NULL,
    Year INT,
    Runtime INT,
    Rating DECIMAL(3 , 1 ),
    PlotSummary TEXT,
    PosterURL VARCHAR(255),
    IMDbID VARCHAR(20) UNIQUE,
    ReleaseDate DATE
);

CREATE TABLE Genres (
    GenreID INT PRIMARY KEY AUTO_INCREMENT,
    GenreName VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE MovieGenres (
    MovieID INT,
    GenreID INT,
    PRIMARY KEY (MovieID, GenreID),
    FOREIGN KEY (MovieID) REFERENCES Movies(MovieID),
    FOREIGN KEY (GenreID) REFERENCES Genres(GenreID)
);

CREATE TABLE People (
    PersonID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(255) NOT NULL,
    BirthDate DATE NULL,
    Bio TEXT NULL
);

CREATE TABLE Roles (
  RoleID INT PRIMARY KEY AUTO_INCREMENT,
  RoleName VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE MoviePeople (
    MovieID INT,
    PersonID INT,
    RoleID INT,
    PRIMARY KEY (MovieID, PersonID, RoleID),
    FOREIGN KEY (MovieID) REFERENCES Movies(MovieID),
    FOREIGN KEY (PersonID) REFERENCES People(PersonID),
	FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
);

CREATE TABLE PlotKeywords (
    KeywordID INT PRIMARY KEY AUTO_INCREMENT,
    Keyword VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE MovieKeywords (
    MovieID INT,
    KeywordID INT,
    PRIMARY KEY (MovieID, KeywordID),
    FOREIGN KEY (MovieID) REFERENCES Movies(MovieID),
    FOREIGN KEY (KeywordID) REFERENCES PlotKeywords(KeywordID)
);

CREATE TABLE Awards (
	AwardID INT PRIMARY KEY AUTO_INCREMENT,
	AwardName VARCHAR(255) NOT NULL,
	AwardCategory VARCHAR(255)
);

CREATE TABLE MovieAwards (
	MovieID INT,
	AwardID INT,
	YearWon INT,
	PRIMARY KEY(MovieID, AwardID, YearWon),
	FOREIGN KEY (MovieID) REFERENCES Movies(MovieID),
	FOREIGN KEY (AwardID) REFERENCES Awards(AwardID)
);

-- Indexes (important for performance)
CREATE INDEX idx_movie_title ON Movies(Title);
CREATE INDEX idx_movie_imdbid ON Movies(IMDbID);
CREATE INDEX idx_person_name ON People(Name);
CREATE INDEX idx_moviepeople_role ON MoviePeople(RoleID);