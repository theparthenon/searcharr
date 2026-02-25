"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Sonarr API Wrapper
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import time
from urllib.parse import quote

from .api_client import ApiClient


class Sonarr(ApiClient):
    def __init__(self, api_url, api_key, verbose=False):
        super().__init__(api_url, api_key, "sonarr", verbose)
        self._all_series = {}
        self.get_all_series()

    def lookup_series(self, title=None, tvdb_id=None):
        """Look up series by title or TVDB ID.
        
        Args:
            title (str, optional): Series title to search. Defaults to None.
            tvdb_id (int, optional): TVDB ID to search. Defaults to None.
            
        Returns:
            list: List of series objects matching the search
        """
        r = self._api_get(
            "series/lookup", {"term": f"tvdb:{tvdb_id}" if tvdb_id else quote(title)}
        )
        if not r:
            return []

        return [
            {
                "title": x.get("title"),
                "seasonCount": len(x.get("seasons")),
                "status": x.get("status", "Unknown Status"),
                "overview": x.get("overview", "Overview not available."),
                "network": x.get("network"),
                "remotePoster": x.get(
                    "remotePoster",
                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                ),
                "year": x.get("year"),
                "tvdbId": x.get("tvdbId"),
                "seriesType": x.get("seriesType"),
                "imdbId": x.get("imdbId"),
                "certification": x.get("certification"),
                "id": x.get("id", self._series_internal_id(x.get("tvdbId"))),
                "titleSlug": x.get("titleSlug"),
                "cleanTitle": x.get("cleanTitle"),
                "tvRageId": x.get("tvRageId"),
                "images": x.get("images"),
                "seasons": x.get("seasons"),
                "genres": x.get("genres", []),
            }
            for x in r
        ]

    def _series_internal_id(self, tvdb_id):
        """Get the internal ID for a series by TVDB ID.
        
        Args:
            tvdb_id (int): TVDB ID
            
        Returns:
            int: Internal ID or None if not found
        """
        return next(
            (x["id"] for x in self.get_all_series() if x.get("tvdbId", 0) == tvdb_id),
            None,
        )

    def get_all_series(self):
        """Get all series, with caching.
        
        Returns:
            list: All series in Sonarr
        """
        if int(round(self._all_series.get("ts", 0))) < int(round(time.time())) - 30:
            self.logger.debug("Refreshing all series cache...")
            r = self._api_get("series", {})
            self._all_series.update({"series": r, "ts": time.time()})

        return self._all_series["series"]

    def add_series(
        self,
        series_info=None,
        tvdb_id=None,
        search=True,
        season_folders=True,
        monitored=True,
        unmonitor_existing=True,
        additional_data={},
    ):
        """Add a series to Sonarr.
        
        Args:
            series_info (dict, optional): Series info from lookup_series. Defaults to None.
            tvdb_id (int, optional): TVDB ID if series_info not provided. Defaults to None.
            search (bool, optional): Whether to search for episodes. Defaults to True.
            season_folders (bool, optional): Whether to use season folders. Defaults to True.
            monitored (bool, optional): Whether the series should be monitored. Defaults to True.
            unmonitor_existing (bool, optional): Ignore episodes with files. Defaults to True.
            additional_data (dict, optional): Additional data from user selections. Defaults to {}.
            
        Returns:
            dict: Added series object or False on failure
        """
        if not series_info and not tvdb_id:
            return False

        if not series_info:
            series_info = self.lookup_series(tvdb_id=tvdb_id)
            if len(series_info):
                series_info = series_info[0]
            else:
                return False

        self.logger.debug(f"Additional data: {additional_data}")

        path = additional_data["p"]
        quality = int(additional_data["q"])
        monitor_options = int(additional_data.get("m", 0))
        
        # Apply monitor options to seasons
        if monitor_options == 1:
            # Monitor only the first season
            for s in series_info["seasons"]:
                if s["seasonNumber"] != 1:
                    s.update({"monitored": False})
        elif monitor_options == 2:
            if next(
                (x for x in series_info["seasons"] if x["seasonNumber"] == 0), False
            ):
                # There is a Season 0
                max_season = len(series_info["seasons"]) - 1
            else:
                max_season = len(series_info["seasons"])
            # Monitor only the latest season
            for s in series_info["seasons"]:
                if s["seasonNumber"] != max_season:
                    s.update({"monitored": False})
                    
        # Process tags
        tags = additional_data.get("t", "")
        if len(tags):
            tag_ids = [int(x) for x in tags.split(",")]
        else:
            tag_ids = []

        self.logger.debug(f"{series_info['seasons']=}")

        params = {
            "tvdbId": series_info["tvdbId"],
            "title": series_info["title"],
            "qualityProfileId": quality,
            "titleSlug": series_info["titleSlug"],
            "images": series_info["images"],
            "seasons": series_info["seasons"],
            "rootFolderPath": path,
            "tvRageId": series_info["tvRageId"],
            "seasonFolder": season_folders,
            "monitored": monitored,
            "seriesType": "anime" if additional_data.get("st") == "a" else "standard",
            "tags": tag_ids,
            "addOptions": {
                "ignoreEpisodesWithFiles": unmonitor_existing,
                "ignoreEpisodesWithoutFiles": False,
                "searchForMissingEpisodes": search,
            },
        }

        return self._api_post("series", params)