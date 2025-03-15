"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Readarr API Wrapper
By Ayman Bagabas
https://github.com/toddrob99/searcharr
"""
from urllib.parse import quote

from .api_client import ApiClient


class Readarr(ApiClient):
    def __init__(self, api_url, api_key, verbose=False):
        super().__init__(api_url, api_key, "readarr", verbose)
        self._metadata_profiles = self.get_all_metadata_profiles()

    def lookup_book(self, title):
        """Look up books by title.
        
        Args:
            title (str): Book title to search
            
        Returns:
            list: List of book objects matching the search
        """
        r = self._api_get("search", {"term": quote(title)})
        if not r:
            return []

        return [
            {
                "title": x.get("book").get("title"),
                "authorId": x.get("book").get("authorId"),
                "authorTitle": x.get("book").get("authorTitle"),
                "seriesTitle": x.get("book").get("seriesTitle"),
                "disambiguation": x.get("book").get("disambiguation"),
                "overview": x.get("book").get("overview", "No overview available."),
                "remotePoster": x.get("book").get(
                    "remoteCover",
                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                ),
                "releaseDate": x.get("book").get("releaseDate"),
                "foreignBookId": x.get("book").get("foreignBookId"),
                "id": x.get("book").get("id"),
                "pageCount": x.get("book").get("pageCount"),
                "titleSlug": x.get("book").get("titleSlug"),
                "images": x.get("book").get("images"),
                "links": x.get("book").get("links"),
                "author": x.get("book").get("author"),
                "editions": x.get("book").get("editions"),
            }
            for x in r
            if x.get("book")
        ]

    def add_book(
        self,
        book_info=None,
        search=True,
        monitored=True,
        additional_data={},
    ):
        """Add a book to Readarr.
        
        Args:
            book_info (dict): Book info from lookup_book.
            search (bool, optional): Whether to search for the book. Defaults to True.
            monitored (bool, optional): Whether the book should be monitored. Defaults to True.
            additional_data (dict, optional): Additional data from user selections. Defaults to {}.
            
        Returns:
            dict: Added book object or False on failure
        """
        if not book_info:
            return False

        self.logger.debug(f"Additional data: {additional_data}")

        path = additional_data["p"]
        quality = int(additional_data["q"])
        metadata = int(additional_data["m"])
        
        # Process tags
        tags = additional_data.get("t", "")
        if len(tags):
            tag_ids = [int(x) for x in tags.split(",")]
        else:
            tag_ids = []

        params = {
            "title": book_info["title"],
            "releaseDate": book_info["releaseDate"],
            "foreignBookId": book_info["foreignBookId"],
            "titleSlug": book_info["titleSlug"],
            "monitored": monitored,
            "anyEditionOk": True,
            "addOptions": {
                "searchForNewBook": False  # manually searching below instead
            },
            "editions": book_info["editions"],
            "author": {
                "qualityProfileId": quality,
                "metadataProfileId": metadata,
                "foreignAuthorId": book_info["author"]["foreignAuthorId"],
                "rootFolderPath": path,
                "tags": tag_ids,
            },
        }

        rsp = self._api_post("book", params)
        if rsp is not None and search:
            # Force book search
            srsp = self._api_post(
                "command", {"name": "BookSearch", "bookIds": [rsp.get("id")]}
            )
            self.logger.debug(f"Result of attempt to search book: {srsp}")
        return rsp

    def lookup_metadata_profile(self, v):
        """Look up metadata profile from a profile name or id.
        
        Args:
            v (str): Metadata profile name or ID
            
        Returns:
            dict: Metadata profile object or None if not found
        """
        return next(
            (x for x in self._metadata_profiles if str(v) in [x["name"], str(x["id"])]),
            None,
        )

    def get_all_metadata_profiles(self):
        """Get all metadata profiles.
        
        Returns:
            list: Metadata profile objects or None on failure
        """
        return (self._api_get("metadataprofile", {})) or None