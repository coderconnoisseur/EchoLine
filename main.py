from app import EchoLineApp
import sys
import os

if __name__ == "__main__":
    exit_code = 1
    try:
        app = EchoLineApp()
        exit_code = app.run()
        print(f"Exiting with code: {exit_code}")
    except KeyboardInterrupt:
        print("Application interrupted by user")
        exit_code = 0
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Force exit so lingering audio threads cannot keep the process alive,
        # flushing first because os._exit skips interpreter shutdown
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)
