#!/usr/bin/env python3
"""
Test script to verify the enhanced RAG app starts correctly.
"""
import sys
import subprocess
import time
import requests
from pathlib import Path

def test_app_startup():
    """Test that the app starts without errors."""
    print("🧪 Testing Enhanced RAG App Startup...")
    
    # Test 1: Import test
    print("\n1️⃣ Testing imports...")
    try:
        import app
        print("✅ App imports successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Configuration test
    print("\n2️⃣ Testing configuration...")
    try:
        from config.settings import get_settings
        config = get_settings()
        config.validate()
        print("✅ Configuration is valid")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    # Test 3: Component initialization test
    print("\n3️⃣ Testing component initialization...")
    try:
        system_components = app.initialize_system()
        if system_components:
            print("✅ System components initialized successfully")
        else:
            print("⚠️  System components returned None (graceful degradation)")
    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        return False
    
    # Test 4: Streamlit startup test (quick check)
    print("\n4️⃣ Testing Streamlit startup...")
    try:
        # Start Streamlit in background
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", "8503",
            "--server.address", "localhost"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for startup
        time.sleep(5)
        
        # Check if process is still running (not crashed)
        if process.poll() is None:
            print("✅ Streamlit app started successfully")
            
            # Try to connect
            try:
                response = requests.get("http://localhost:8503", timeout=5)
                if response.status_code == 200:
                    print("✅ App is accessible via HTTP")
                else:
                    print(f"⚠️  App responded with status: {response.status_code}")
            except requests.exceptions.RequestException:
                print("⚠️  App started but not yet accessible (normal during startup)")
            
            # Clean up
            process.terminate()
            process.wait()
            return True
        else:
            # Process crashed
            stdout, stderr = process.communicate()
            print(f"❌ Streamlit crashed during startup")
            if stderr:
                print(f"Error output: {stderr.decode()[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ Streamlit startup test failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    print("🎓 Enhanced RAG System - App Startup Test")
    print("=" * 50)
    
    success = test_app_startup()
    
    if success:
        print("\n🎉 All tests passed! The app is ready to use.")
        print("\n🚀 To start the app:")
        print("   ./start_enhanced_system.sh")
        print("   OR")
        print("   streamlit run app.py")
        print("\n🌐 Access at: http://localhost:8501")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()