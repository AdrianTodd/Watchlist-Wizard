import Link from "next/link";
import { MovieDetails } from "../../../types";
import MovieImage from "../../../components/MovieImage";

interface MovieDetailsPageProps {
  params: { imdbId: string };
}

async function fetchMovieDetails(imdbId: string): Promise<MovieDetails | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    console.error("API URL not configured");
    return null;
  }
  try {
    const response = await fetch(`${apiUrl}/movies/${imdbId}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const movie: MovieDetails = await response.json();
    return movie;
  } catch (err) {
    console.error(`Error fetching movie ${imdbId}:`, err);
    return null;
  }
}

function formatRuntime(minutes: number | null): string {
  if (minutes === null || minutes <= 0) return "N/A";
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  let formatted = "";
  if (hours > 0) formatted += `${hours}h`;
  if (remainingMinutes > 0) formatted += ` ${remainingMinutes}m`;
  return formatted.trim();
}

export default async function MovieDetailsPage({
  params,
}: MovieDetailsPageProps): Promise<JSX.Element> {
  const { imdbId } = await params;
  const movie: MovieDetails | null = await fetchMovieDetails(imdbId);

  if (!movie) {
    return (
      <div className='text-center py-10'>
        <h1 className='text-2xl mb-4'>Movie Not Found</h1>
        <Link href='/' className='text-blue-600 hover:underline'>
          Go back home
        </Link>
      </div>
    );
  }

  return (
    <div className='container mx-auto px-4 py-8'>
      <div className='bg-[181818] rounded-lg shadow-xl overflow-hidden border border-gray-700'>
        <div className='md:flex'>
          {/* Poster Section */}
          <div className='md:flex-shrink-0'>
            {/* USE THE MovieImage COMPONENT */}
            <MovieImage
              src={movie.PosterURL}
              alt={movie.Title || "Movie Poster"}
              width={384} // Adjust as needed
              height={568} // Adjust based on desired aspect ratio
              className='h-auto w-full object-cover md:w-80 lg:w-96'
              priority={true} // This image is likely important, load it eagerly
            />
          </div>

          {/* Details Section */}
          <div className='p-6 md:p-8 flex-grow'>
            <h1 className='text-3xl font-bold mb-2'>
              {movie.Title}{" "}
              <span className='font-normal text-2xl text-gray-900'>
                ({movie.Year ?? "N/A"})
              </span>
            </h1>

            {/* Metadata Bar */}
            <div className='flex flex-wrap items-center text-sm text-black mb-4'>
              {movie.MPAARating && (
                <span className='mr-3 border px-1.5 py-0.5 rounded'>
                  {movie.MPAARating}
                </span>
              )}
              {movie.Runtime && (
                <span className='mr-3'>{formatRuntime(movie.Runtime)}</span>
              )}
              {movie.ReleaseDate && (
                <span>
                  {new Date(movie.ReleaseDate + "T00:00:00").toLocaleDateString(
                    undefined,
                    { year: "numeric", month: "long", day: "numeric" }
                  )}
                </span>
              )}
            </div>

            {/* Rating */}
            {movie.Rating && ( // Check if movie.Rating is truthy (not null, undefined, 0)
              <div className='flex items-center mb-4'>
                <svg
                  className='w-5 h-5 text-yellow-400 mr-1'
                  fill='currentColor'
                  viewBox='0 0 20 20'
                >
                  <path d='M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.817 5.955 6.572.955-4.756 4.635 1.123 6.545z'></path>
                </svg>
                {/* Add a type check before calling toFixed */}
                {typeof movie.Rating === "number" ? (
                  <span className='text-lg font-bold'>
                    {movie.Rating.toFixed(1)}
                  </span>
                ) : (
                  <span className='text-lg font-bold'>N/A</span> // Handle if it's somehow not a number
                )}
                <span className='text-sm text-gray-500'>/10</span>
              </div>
            )}
            {/* Add this block if you want to display N/A when rating is null/0 */}
            {!movie.Rating && (
              <div className='flex items-center mb-4 text-gray-500'>
                Rating: N/A
              </div>
            )}

            {/* Genres */}
            {movie.genres && movie.genres.length > 0 && (
              <div className='mb-4'>
                {movie.genres.map(genre => (
                  <span
                    key={genre}
                    className='inline-block bg-gray-200 rounded-full px-3 py-1 text-sm font-semibold text-gray-700 mr-2 mb-2'
                  >
                    {genre}
                  </span>
                ))}
              </div>
            )}

            {/* Plot */}
            <p className='text-gray-700 mb-6'>{movie.PlotSummary ?? "N/A"}</p>

            {/* Cast & Crew */}
            <div className='mb-6'>
              <h3 className='text-xl font-semibold mb-2 border-b pb-1'>
                Cast & Crew
              </h3>
              <ul>
                {/* Use optional chaining for safety and improve key */}
                {movie.people?.map((person, index) => (
                  <li
                    key={`<span class="math-inline">\{person\.PersonIMDbID \|\| 'no\-id'\}\-</span>{person.RoleName || 'no-role'}-${index}`}
                  >
                    {" "}
                    {/* <-- IMPROVED KEY */}
                    {person.Name} ({person.RoleName})
                  </li>
                ))}
              </ul>
            </div>

            {/* Keywords */}
            {movie.plot_keywords && movie.plot_keywords.length > 0 && (
              <div>
                <h3 className='text-xl font-semibold mb-2 border-b pb-1'>
                  Keywords
                </h3>
                {movie.plot_keywords.map(keyword => (
                  <span
                    key={keyword}
                    className='inline-block bg-blue-100 text-blue-800 rounded-full px-3 py-1 text-sm font-medium mr-2 mb-2'
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className='mt-8'>
        <Link href='/' className='text-blue-600 hover:underline'>
          ← Back to movie list
        </Link>
      </div>
    </div>
  );
}
