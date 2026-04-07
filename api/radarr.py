"""
Searcharr
Sonarr & Radarr Telegram Bot
Radarr API Wrapper
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from urllib.parse import quote

from .api_client import ApiClient


class Radarr(ApiClient):
    def __init__(self, api_url, api_key, verbose=False):
        super().__init__(api_url, api_key, "radarr", verbose)

    def lookup_movie(self, title=None, tmdb_id=None):
        """Look up a movie by title or TMDB ID.
        
        Args:
            title (str, optional): Movie title to search. Defaults to None.
            tmdb_id (int, optional): TMDB ID to search. Defaults to None.
            
        Returns:
            list: List of movie objects matching the search
        """
        r = self._api_get(
            "movie/lookup", {"term": f"tmdb:{tmdb_id}" if tmdb_id else quote(title)}
        )
        if not r:
            return []

        return [
            {
                "title": x.get("title"),
                "overview": x.get("overview", "No overview available."),
                "status": x.get("status", "Unknown Status"),
                "inCinemas": x.get("inCinemas"),
                "remotePoster": x.get(
                    "remotePoster",
                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                ),
                "year": x.get("year"),
                "tmdbId": x.get("tmdbId"),
                "imdbId": x.get("imdbId", None),
                "runtime": x.get("runtime"),
                "id": x.get("id"),
                "titleSlug": x.get("titleSlug"),
                "images": x.get("images"),
            }
            for x in r
        ]

    def add_movie(
        self,
        movie_info=None,
        tmdb_id=None,
        search=True,
        monitored=True,
        min_avail="released",
        additional_data={},
    ):
        """Add a movie to Radarr.
        
        Args:
            movie_info (dict, optional): Movie info from lookup_movie. Defaults to None.
            tmdb_id (int, optional): TMDB ID if movie_info not provided. Defaults to None.
            search (bool, optional): Whether to search for the movie. Defaults to True.
            monitored (bool, optional): Whether the movie should be monitored. Defaults to True.
            min_avail (str, optional): Minimum availability. Defaults to "released".
            additional_data (dict, optional): Additional data from user selections. Defaults to {}.
            
        Returns:
            dict: Added movie object or False on failure
        """
        if not movie_info and not tmdb_id:
            return False

        if not movie_info:
            movie_info = self.lookup_movie(tmdb_id=tmdb_id)
            if len(movie_info):
                movie_info = movie_info[0]
            else:
                return False

        self.logger.debug(f"Additional data: {additional_data}")

        path = additional_data["p"]
        quality = int(additional_data["q"])
        
        # Process tags
        tags = additional_data.get("t", "")
        if len(tags):
            tag_ids = [int(x) for x in tags.split(",")]
        else:
            tag_ids = []

        params = {
            "tmdbId": movie_info["tmdbId"],
            "title": movie_info["title"],
            "year": movie_info["year"],
            "qualityProfileId": quality,
            "titleSlug": movie_info["titleSlug"],
            "images": movie_info["images"],
            "rootFolderPath": path,
            "monitored": monitored,
            "minimumAvailability": min_avail,
            "tags": tag_ids,
            "addOptions": {"searchForMovie": search},
        }

        return self._api_post("movie", params)