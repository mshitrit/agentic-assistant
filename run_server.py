import subprocess
import time
import sys
import requests

def load_config():
    config = {}
    with open("jira_config.txt") as f:
        for line in f:
            key, _, value = line.strip().partition("=")
            config[key] = value
    return config

def wait_for_server(url: str, retries: int = 10, delay: float = 1.0):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                print("Server is up.")
                return True
        except requests.ConnectionError:
            print(f"Waiting for server... ({attempt + 1}/{retries})")
            time.sleep(delay)
    return False

if __name__ == "__main__":
    config = load_config()
    listener_url = config.get("LISTENER_URL")

    if not listener_url:
        print("ERROR: LISTENER_URL not set in jira_config.txt")
        sys.exit(1)

    # 1. Start the FastAPI server as a subprocess
    print("Starting webhook listener...")
    server = subprocess.Popen(["uvicorn", "webhook_listner:app", "--host", "0.0.0.0", "--port", "8000"])

    # 2. Wait until the server is ready
    if not wait_for_server("http://localhost:8000/health"):
        print("ERROR: Server did not start in time.")
        server.terminate()
        sys.exit(1)

    # 3. Register the webhook with Jira
    print(f"Registering webhook at {listener_url}...")
    from webhook_listner import register_webhook
    register_webhook(listener_url)

    # 4. Keep running until interrupted
    try:
        server.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.terminate()
