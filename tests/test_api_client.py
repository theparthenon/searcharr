# tests/test_api_client.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_client import ApiClient
import settings as settings

def test_api_client_initialization():
    """Test that the base ApiClient can be initialized for each service type"""
    
    # Test Sonarr
    if settings.sonarr_enabled and settings.sonarr_url and settings.sonarr_api_key:
        try:
            sonarr_client = ApiClient(settings.sonarr_url, settings.sonarr_api_key, "sonarr", verbose=True)
            assert sonarr_client is not None
            assert sonarr_client.version is not None
            print(f"Initialized ApiClient for Sonarr, version: {sonarr_client.version}")
        except Exception as e:
            print(f"Error initializing Sonarr client: {e}")
            return False
    else:
        print("WARNING: Sonarr is not properly configured - skipping")
    
    # Test Radarr
    if settings.radarr_enabled and settings.radarr_url and settings.radarr_api_key:
        try:
            radarr_client = ApiClient(settings.radarr_url, settings.radarr_api_key, "radarr", verbose=True)
            assert radarr_client is not None
            assert radarr_client.version is not None
            print(f"Initialized ApiClient for Radarr, version: {radarr_client.version}")
        except Exception as e:
            print(f"Error initializing Radarr client: {e}")
            return False
    else:
        print("WARNING: Radarr is not properly configured - skipping")
    
    # Test Readarr if enabled
    if settings.readarr_enabled and settings.readarr_url and settings.readarr_api_key:
        try:
            readarr_client = ApiClient(settings.readarr_url, settings.readarr_api_key, "readarr", verbose=True)
            assert readarr_client is not None
            assert readarr_client.version is not None
            print(f"Initialized ApiClient for Readarr, version: {readarr_client.version}")
        except Exception as e:
            print(f"Error initializing Readarr client: {e}")
            return False
    else:
        print("WARNING: Readarr is not properly configured - skipping")
    
    return True

def test_base_functionality():
    """Test the base functionality of ApiClient with each service"""
    
    # Test with Radarr
    if settings.radarr_enabled and settings.radarr_url and settings.radarr_api_key:
        try:
            print("\n--- Evaluating Radarr ---")
            client = ApiClient(settings.radarr_url, settings.radarr_api_key, "radarr", verbose=True)
            
            # Test tag methods
            tags = client.get_all_tags()
            print(f"Found {len(tags)} tags in Radarr")
            
            # Test quality profiles
            profiles = client.get_all_quality_profiles()
            print(f"Found {len(profiles) if profiles else 0} quality profiles in Radarr")
            
            # Test root folders
            folders = client.get_root_folders()
            print(f"Found {len(folders)} root folders in Radarr")
        except Exception as e:
            print(f"Error testing base functionality with Radarr: {e}")
            return False
    
    # Test with Sonarr
    if settings.sonarr_enabled and settings.sonarr_url and settings.sonarr_api_key:
        try:
            print("\n--- Evaluating Sonarr ---")
            client = ApiClient(settings.sonarr_url, settings.sonarr_api_key, "sonarr", verbose=True)
            
            # Test tag methods
            tags = client.get_all_tags()
            print(f"Found {len(tags)} tags in Sonarr")
            
            # Test quality profiles
            profiles = client.get_all_quality_profiles()
            print(f"Found {len(profiles) if profiles else 0} quality profiles in Sonarr")
            
            # Test root folders
            folders = client.get_root_folders()
            print(f"Found {len(folders)} root folders in Sonarr")
        except Exception as e:
            print(f"Error testing base functionality with Sonarr: {e}")
            return False
    
    # Test with Readarr
    if settings.readarr_enabled and settings.readarr_url and settings.readarr_api_key:
        try:
            print("\n--- Evaluating Readarr ---")
            client = ApiClient(settings.readarr_url, settings.readarr_api_key, "readarr", verbose=True)
            
            # Test tag methods
            tags = client.get_all_tags()
            print(f"Found {len(tags)} tags in Readarr")
            
            # Test quality profiles
            profiles = client.get_all_quality_profiles()
            print(f"Found {len(profiles) if profiles else 0} quality profiles in Readarr")
            
            # Test root folders
            folders = client.get_root_folders()
            print(f"Found {len(folders)} root folders in Readarr")
        except Exception as e:
            print(f"Error testing base functionality with Readarr: {e}")
            return False
    
    return True

def run_all_tests():
    """Run all tests and return overall success"""
    init_success = test_api_client_initialization()
    func_success = test_base_functionality()
    return init_success and func_success

if __name__ == "__main__":
    success = run_all_tests()
    print(f"\nTests {'PASSED' if success else 'FAILED'}")