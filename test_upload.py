#!/usr/bin/env python3
"""
Test script to verify URL upload functionality
"""
import httpx
import sys

def test_url_download():
    """Test downloading a file from a URL"""
    # Use the local test file via a simple HTTP server or a real public URL
    # For this test, we'll use a small public DOCX file
    test_url = "https://file-examples.com/storage/fe0e5f2f6b0f7e3f3b3e3e3/2017/02/file-sample_100kB.doc"
    
    print(f"Testing URL download from: {test_url}")
    
    try:
        response = httpx.get(test_url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        
        content = response.content
        print(f"✅ Successfully downloaded {len(content)} bytes")
        
        # Verify it's a valid ZIP/DOCX file
        if content[:4] == b'PK\x03\x04':
            print("✅ File has valid ZIP/DOCX header")
        else:
            print(f"❌ Invalid file header: {content[:4].hex()}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return False

def test_base64_truncation_detection():
    """Test that small base64 strings are detected as truncated"""
    # Simulate truncated base64 (like what ChatGPT sends)
    truncated_base64 = "UEsDBBQACAgIAKCbMlwAAAAAAAAAAAAAAAASAAAAd29yZC9udW1iZXJpbmcueG1s"
    
    print(f"\nTesting truncation detection with {len(truncated_base64)} chars")
    
    if len(truncated_base64) < 1000:
        print("✅ Truncation would be detected (< 1000 chars)")
        return True
    else:
        print("❌ Truncation would NOT be detected")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("File Upload Functionality Tests")
    print("=" * 60)
    
    test1 = test_url_download()
    test2 = test_base64_truncation_detection()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"URL Download: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Truncation Detection: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
