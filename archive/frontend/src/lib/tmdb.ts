export function getPosterUrl(path?: string | null) {
  if (!path) return null;
  return `https://image.tmdb.org/t/p/w500${path}`;
}
