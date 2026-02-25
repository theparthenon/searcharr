# tests/test_radarr.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.radarr import Radarr
from config import settings

def test_radarr_functionality():
    radarr = Radarr(settings.radarr_url, settings.radarr_api_key, verbose=True)
    
    # Test version detection
    print(f"Detected Radarr version: {radarr.version}")
    
    # Test movie lookup
    movies = radarr.lookup_movie("Inception")
    print(f"Found {len(movies)} movies")
    
    # Test tag operations
    tags = radarr.get_all_tags()
    print(f"Found {len(tags)} tags")
    
    # Test quality profiles
    profiles = radarr._quality_profiles
    print(f"Found {len(profiles)} quality profiles")
    
    # Test root folders
    folders = radarr._root_folders
    print(f"Found {len(folders)} root folders")
    
    return True

if __name__ == "__main__":
    success = test_radarr_functionality()
    print(f"Test {'PASSED' if success else 'FAILED'}")