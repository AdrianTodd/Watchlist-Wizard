// frontend/types.ts

// Type for the basic movie data shown in lists (from /api/movies)
export interface MovieListItem {
  MovieID: number; // Assuming integer ID from DB
  Title: string;
  Year: number | null;
  Rating: number | null;
  PosterURL: string | null;
  IMDbID: string;
}

// Type for a person involved in a movie (from details API /api/movies/:id)
export interface MoviePerson {
  Name: string;
  PersonIMDbID: string; // Assuming this is the field name from your API
  RoleName: string;
}

// Type for the full movie details (from /api/movies/:id)
// Extends MovieListItem to include common fields
export interface MovieDetails extends MovieListItem {
  Runtime: number | null; // Storing as total minutes
  PlotSummary: string | null;
  ReleaseDate: string | null; // Keep as ISO string (YYYY-MM-DD)
  MPAARating: string | null; // Matches the DB column
  genres: string[];
  people: MoviePerson[];
  plot_keywords: string[];
}

// If your /api/recommendations returns a different structure, define it here
export interface Recommendation extends MovieListItem {
  // Add any extra fields specific to recommendations if needed
}
