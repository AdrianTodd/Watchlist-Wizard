"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { MovieListItem } from "../types";
import MovieImage from "../components/MovieImage";
import axios from "axios"; // Using axios for easier query param handling

function useDebounce(value: string, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

export default function HomePage(): JSX.Element {
  //State
  const [movies, setMovies] = useState<MovieListItem[]>([]);
  const [genres, setGenres] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("");
  const [keywordTerm, setKeywordTerm] = useState(""); // Example for keyword filter
  const [actorTerm, setActorTerm] = useState(""); // Example for actor filter
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  //Debouncing
  const debouncedSearchTerm = useDebounce(searchTerm, 500); // 500ms delay
  const debouncedKeywordTerm = useDebounce(keywordTerm, 500);
  const debouncedActorTerm = useDebounce(actorTerm, 500);

  //Fetch Genres
  useEffect(() => {
    const fetchGenres = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        if (!apiUrl) throw new Error("API URL not configured");
        const response = await axios.get(`${apiUrl}/genres`);
        setGenres(response.data || []); // Ensure it's an array
      } catch (err) {
        console.error("Error fetching genres:", err);
        setError("Failed to load genres");
      }
    };
    fetchGenres();
  }, []); // Fetch genres only once on mount

  //Fetch Movies triggered by debounced terms or genre change
  const fetchMovies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) throw new Error("API URL not configured");

      // Build query parameters based on state
      const params: Record<string, string | number> = { limit: 250 }; // Base params
      if (debouncedSearchTerm) params.search = debouncedSearchTerm;
      if (selectedGenre) params.genre = selectedGenre;
      if (debouncedKeywordTerm) params.keyword = debouncedKeywordTerm;
      if (debouncedActorTerm) params.actor = debouncedActorTerm;
      // Could add other filters here in the future

      console.log("Fetching movies with params:", params);

      const response = await axios.get(`${apiUrl}/movies`, { params });
      setMovies(response.data || []);
    } catch (err) {
      console.error("Error fetching movies:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch movies");
      setMovies([]); // Clear movies on error
    } finally {
      setLoading(false);
    }
  }, [
    debouncedSearchTerm,
    selectedGenre,
    debouncedKeywordTerm,
    debouncedActorTerm,
  ]);

  useEffect(() => {
    fetchMovies();
  }, [fetchMovies]); // Re-run fetchMovies when filters input changes

  return (
    <div>
      <h1 className='text-center mb-8'>Search & Filter Movies</h1>

      {/* Filter Controls */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 p-4 bg-[#181818] text-gray-300 rounded shadow'>
        {/* Search Term */}
        <div>
          <label
            htmlFor='search'
            className='block text-sm font-medium text-gray-300 mb-1'
          >
            Search Title/Plot:
          </label>
          <input
            type='text'
            id='search'
            placeholder='e.g., prison, redemption'
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
          />
        </div>

        {/* Genre Select */}
        <div>
          <label htmlFor='genre' className='block text-sm font-medium mb-1'>
            Filter by Genre:
          </label>
          <select
            id='genre'
            value={selectedGenre}
            onChange={e => setSelectedGenre(e.target.value)}
            className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-[#181818]'
          >
            <option value=''>All Genres</option>
            {genres.map(genre => (
              <option key={genre} value={genre}>
                {genre}
              </option>
            ))}
          </select>
        </div>

        {/* Keyword Input */}
        <div>
          <label htmlFor='keyword' className='block text-sm font-medium mb-1'>
            Filter by Keyword:
          </label>
          <input
            type='text'
            id='keyword'
            placeholder='e.g., escape'
            value={keywordTerm}
            onChange={e => setKeywordTerm(e.target.value)}
            className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
          />
        </div>

        {/* Actor Input */}
        <div>
          <label htmlFor='actor' className='block text-sm font-medium mb-1'>
            Filter by Actor:
          </label>
          <input
            type='text'
            id='actor'
            placeholder='e.g., Morgan Freeman'
            value={actorTerm}
            onChange={e => setActorTerm(e.target.value)}
            className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
          />
        </div>
      </div>

      {/* Movie Grid */}
      {loading && <p className='text-center'>Loading movies...</p>}
      {error && <p className='text-center text-red-600'>Error: {error}</p>}
      {!loading && !error && (
        <div className='grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6'>
          {movies.length > 0 ? (
            movies.map((movie, index) => (
              <div
                key={movie.IMDbID}
                className='bg-[#181818] border border-gray-800 rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300 ease-in-out'
              >
                <Link href={`/movies/${movie.IMDbID}`} className='block group'>
                  <MovieImage
                    src={movie.PosterURL}
                    alt={movie.Title || "Movie Poster"}
                    width={200}
                    height={300}
                    className='w-full h-auto aspect-[2/3] object-cover group-hover:opacity-90 transition-opacit'
                    priority={index < 6}
                  />
                  <div className='p-4'>
                    <h2 className='text-lg font-semibold truncate mb-1'>
                      {movie.Title} ({movie.Year ?? "N/A"})
                    </h2>
                    <p className='text-sm text-gray-300'>
                      Rating: {movie.Rating ?? "N/A"}
                    </p>
                  </div>
                </Link>
              </div>
            ))
          ) : (
            <p className='text-center text-gray-500 col-span-full'>
              No movies match your criteria.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
