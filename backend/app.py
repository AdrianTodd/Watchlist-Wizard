# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import watchlist_wizard_db as database # Use relative import

app = Flask(__name__)
CORS(app)

@app.route('/api/movies', methods=['GET'])
def get_movies_api():
    # Get filter parameters from query string
    search = request.args.get('search', None) # General search term
    genre = request.args.get('genre', None)   # Specific genre
    keyword = request.args.get('keyword', None) # Plot keyword
    actor = request.args.get('actor', None)   # Actor name

    # Pagination parameters
    limit = request.args.get('limit', 250, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Pass filters to the database function
    movies = database.get_all_movies(
        limit=limit,
        offset=offset,
        search_term=search,
        genre_filter=genre,
        keyword_filter=keyword,
        actor_filter=actor
    )
    return jsonify(movies)

@app.route('/api/movies/<string:imdb_id>', methods=['GET'])
def get_movie_details_api(imdb_id):
    movie = database.get_movie_by_imdb_id(imdb_id)
    if movie:
        return jsonify(movie)
    else:
        return jsonify({"error": "Movie not found"}), 404

@app.route('/api/genres', methods=['GET'])
def get_genres_api():
    genres = database.get_all_genres()
    return jsonify(genres)

# --- Add more API endpoints here (e.g., /api/recommendations) ---
# Example recommendation endpoint (very basic)
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations_api():
    # In a real app, get user preferences (e.g., from request args or session)
    preferred_genre = request.args.get('genre', 'Drama') # Example: get genre from query param
    # Basic: just fetch movies of that genre
    # TODO: Implement more sophisticated recommendation logic in database.py
    conn = database.get_db_connection()
    recommendations = []
    if conn:
         try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT m.MovieID, m.Title, m.Year, m.Rating, m.PosterURL, m.IMDbID
                FROM Movies m
                JOIN MovieGenres mg ON m.MovieID = mg.MovieID
                JOIN Genres g ON mg.GenreID = g.GenreID
                WHERE g.GenreName = %s
                ORDER BY m.Rating DESC
                LIMIT 20
            """, (preferred_genre,))
            recommendations = cursor.fetchall()
         except database.mysql.connector.Error as err:
            print(f"Error getting recommendations: {err}")
         finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    return jsonify(recommendations)


if __name__ == '__main__':
    app.run(debug=True) # debug=True for development, remove for production