from app import EchoLineApp
import sys
import os

if __name__ == "__main__":
    try:
        app = EchoLineApp()
        exit_code = app.run()
        print(f"Exiting with code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Force exit if needed
        os._exit(0)