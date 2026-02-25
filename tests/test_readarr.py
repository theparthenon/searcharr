# tests/test_readarr.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.readarr import Readarr
import settings

def test_readarr_initialization():
    """Test that Readarr client can be initialized and version detected"""
    # Skip test if Readarr is not enabled in settings
    if not settings.readarr_enabled:
        print("Readarr is disabled in settings, skipping tests")
        return True
        
    readarr = Readarr(settings.readarr_url, settings.readarr_api_key, verbose=True)
    assert readarr is not None
    assert readarr.version is not None
    print(f"Detected Readarr version: {readarr.version}")
    return True

def test_readarr_functionality():
    """Test core Readarr functionality"""
    # Skip test if Readarr is not enabled in settings
    if not settings.readarr_enabled:
        print("Readarr is disabled in settings, skipping tests")
        return True
        
    readarr = Readarr(settings.readarr_url, settings.readarr_api_key, verbose=True)
    
    # Test book lookup
    books = readarr.lookup_book("Dune")
    print(f"Found {len(books)} books")
    
    # Test tag operations
    tags = readarr.get_all_tags()
    print(f"Found {len(tags)} tags")
    
    # Test quality profiles
    quality_profiles = readarr._quality_profiles
    print(f"Found {len(quality_profiles)} quality profiles")
    
    # Test metadata profiles
    metadata_profiles = readarr._metadata_profiles
    print(f"Found {len(metadata_profiles)} metadata profiles")
    
    # Test root folders
    folders = readarr._root_folders
    print(f"Found {len(folders)} root folders")
    
    return True

def run_all_tests():
    """Run all tests and return overall success"""
    init_success = test_readarr_initialization()
    func_success = test_readarr_functionality()
    return init_success and func_success

if __name__ == "__main__":
    success = run_all_tests()
    print(f"Tests {'PASSED' if success else 'FAILED'}")