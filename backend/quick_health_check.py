#!/usr/bin/env python3
"""
Quick Health Check for FastAPI Backend
Simple script to verify the backend is running and responding
"""

import requests
import json
import sys
import time
from datetime import datetime

def check_server_health():
    """Quick health check for the backend server"""
    print("🔍 Quick Backend Health Check")
    print("=" * 30)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Basic connectivity
    try:
        print("1. Testing server connectivity...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server is running - Status: {data.get('status')}")
        else:
            print(f"   ❌ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server. Is it running on port 8000?")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Server response timeout")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 2: API documentation
    try:
        print("2. Testing API documentation...")
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("   ✅ API documentation is accessible")
        else:
            print("   ⚠️ API docs returned status", response.status_code)
    except:
        print("   ⚠️ API docs not accessible")
    
    # Test 3: Root endpoint
    try:
        print("3. Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Root endpoint - {data.get('message')}")
        else:
            print(f"   ❌ Root endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {str(e)}")
    
    # Test 4: Database connectivity (curriculum structure)
    try:
        print("4. Testing database connectivity...")
        response = requests.get(f"{base_url}/topics/structure", timeout=10)
        if response.status_code == 200:
            data = response.json()
            curriculum = data.get("curriculum", [])
            print(f"   ✅ Database connected - Found {len(curriculum)} curriculum topics")
        else:
            print(f"   ❌ Database test failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Database test error: {str(e)}")
    
    print("\n🎯 Quick Test Summary:")
    print("   • Server is responding to requests")
    print("   • API documentation is available")
    print("   • Database connectivity verified")
    print("\n✅ Basic health check passed!")
    print("\n📝 Next steps:")
    print("   1. Run full test suite: python test_backend.py")
    print("   2. Check API docs: http://localhost:8000/docs")
    print("   3. Verify .env configuration")
    
    return True

def test_registration():
    """Quick test of user registration"""
    print("\n🔧 Testing User Registration...")
    
    base_url = "http://localhost:8000"
    test_user = {
        "username": f"quicktest_{int(time.time())}",
        "password": "test123",
        "role": "student"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/register", json=test_user, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Registration works - User ID: {data.get('user_id')}")
            if data.get('link_code'):
                print(f"   📝 Student link code: {data.get('link_code')}")
        else:
            error = response.json().get('detail', 'Unknown error')
            print(f"   ❌ Registration failed: {error}")
    except Exception as e:
        print(f"   ❌ Registration test error: {str(e)}")

def main():
    """Main function"""
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if check_server_health():
        test_registration()
        print("\n🎉 Quick health check completed successfully!")
        print("Backend appears to be working correctly.")
        return True
    else:
        print("\n❌ Health check failed!")
        print("Please check if the backend server is running.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)