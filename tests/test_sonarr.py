# tests/test_sonarr.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sonarr import Sonarr
import settings

def test_sonarr_initialization():
    """Test that Sonarr client can be initialized and version detected"""
    sonarr = Sonarr(settings.sonarr_url, settings.sonarr_api_key, verbose=True)
    assert sonarr is not None
    assert sonarr.version is not None
    print(f"Detected Sonarr version: {sonarr.version}")
    return True

def test_sonarr_functionality():
    """Test core Sonarr functionality"""
    sonarr = Sonarr(settings.sonarr_url, settings.sonarr_api_key, verbose=True)
    
    # Test series lookup
    series = sonarr.lookup_series("Breaking Bad")
    print(f"Found {len(series)} series")
    
    # Test all series cache
    all_series = sonarr.get_all_series()
    print(f"Found {len(all_series)} series in library")
    
    # Test tag operations
    tags = sonarr.get_all_tags()
    print(f"Found {len(tags)} tags")
    
    # Test quality profiles
    profiles = sonarr._quality_profiles
    print(f"Found {len(profiles)} quality profiles")
    
    # Test root folders
    folders = sonarr._root_folders
    print(f"Found {len(folders)} root folders")
    
    return True

def run_all_tests():
    """Run all tests and return overall success"""
    init_success = test_sonarr_initialization()
    func_success = test_sonarr_functionality()
    return init_success and func_success

if __name__ == "__main__":
    success = run_all_tests()
    print(f"Tests {'PASSED' if success else 'FAILED'}")