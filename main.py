from flask import Flask, request, jsonify, abort
from notion_client import Client
from datetime import datetime, date
import os
import logging
from dotenv import load_dotenv
from functools import lru_cache

# -------------------------
# Load .env for local development only
# -------------------------
load_dotenv()

# Validate and print the NOTION_TOKEN
notion_token = os.getenv("NOTION_TOKEN")
if notion_token:
    print("NOTION_TOKEN:", notion_token)
else:
    print("NOTION_TOKEN is not set or could not be found.")

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# Environment variable utilities
# -------------------------
def get_env_variable(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

@lru_cache
def get_api_key():
    return get_env_variable("API_KEY")

@lru_cache
def get_notion_client():
    return Client(auth=get_env_variable("NOTION_TOKEN"))

@lru_cache
def get_database_id():
    return get_env_variable("NOTION_DATABASE_ID")

# -------------------------
# Flask setup
# -------------------------
app = Flask(__name__)

# -------------------------
# Middleware
# -------------------------
def check_api_key():
    incoming_key = request.headers.get("X-API-Key")
    if incoming_key != get_api_key():
        abort(401, description="Unauthorized")

def validate_database_schema():
    try:
        notion = get_notion_client()
        database = notion.databases.retrieve(database_id=get_database_id())
        required_properties = ["Command", "Action", "Status"]
        for prop in required_properties:
            if prop not in database["properties"]:
                raise RuntimeError(f"Missing required property: {prop}")
    except Exception as e:
        logger.error(f"Failed to validate database schema: {e}")
        raise

validate_database_schema()

@app.route("/")
def home():
    return "🚀 Notion GPT API is running!"

# -------------------------
# CRUD Endpoints
# -------------------------
@app.route("/create", methods=["POST"])
def create():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ["command", "action", "status"]):
        return jsonify({"error": "Missing required fields"}), 400
    now = datetime.now().isoformat()
    try:
        notion = get_notion_client()
        notion.pages.create(
            parent={"database_id": get_database_id()},
            properties={
                "Command": {"title": [{"text": {"content": data["command"]}}]},
                "Action": {"rich_text": [{"text": {"content": data["action"]}}]},
                "Status": {"select": {"name": data["status"]}},
                "Created At": {"rich_text": [{"text": {"content": now}}]},
                "Last Updated": {"rich_text": [{"text": {"content": now}}]}
            }
        )
        return jsonify({"message": "Created"}), 200
    except Exception as e:
        logger.error(f"Create failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/fetch", methods=["GET"])
def fetch():
    check_api_key()
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        results = [
            {
                "Command": p["properties"]["Command"]["title"][0]["plain_text"],
                "Status": p["properties"]["Status"]["select"]["name"]
            } for p in pages
        ]
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/update", methods=["POST"])
def update():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ["command", "action", "status"]):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if title == data["command"]:
                notion.pages.update(
                    page_id=page["id"],
                    properties={
                        "Action": {"rich_text": [{"text": {"content": data["action"]}}]},
                        "Status": {"select": {"name": data["status"]}},
                        "Last Updated": {"rich_text": [{"text": {"content": datetime.now().isoformat()}}]}
                    }
                )
                return jsonify({"message": "Updated"}), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or "command" not in data:
        return jsonify({"error": "Missing required field: command"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if title == data["command"]:
                notion.pages.update(page_id=page["id"], archived=True)
                return jsonify({"message": "Deleted"}), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Smart & Utility Endpoints
# -------------------------
@app.route("/search", methods=["GET"])
def search():
    check_api_key()
    query_param = request.args.get("query", "").lower()
    if not query_param:
        return jsonify({"error": "Missing query parameter"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        results = []
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if query_param in title.lower():
                results.append({
                    "Command": title,
                    "Status": page["properties"]["Status"]["select"]["name"]
                })
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/filter", methods=["GET"])
def filter_by_status():
    check_api_key()
    status = request.args.get("status")
    if not status:
        return jsonify({"error": "Missing status parameter"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        filtered = [
            {
                "Command": p["properties"]["Command"]["title"][0]["plain_text"],
                "Status": p["properties"]["Status"]["select"]["name"]
            } for p in pages if p["properties"]["Status"]["select"]["name"].lower() == status.lower()
        ]
        return jsonify(filtered), 200
    except Exception as e:
        logger.error(f"Filter failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/grouped", methods=["GET"])
def grouped_by_status():
    check_api_key()
    try:
        notion = get_notion_client()
        grouped = {}
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            status = page["properties"]["Status"]["select"]["name"]
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            grouped.setdefault(status, []).append(title)
        return jsonify(grouped), 200
    except Exception as e:
        logger.error(f"Grouped fetch failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get-task", methods=["GET"])
def get_task():
    check_api_key()
    command = request.args.get("command")
    if not command:
        return jsonify({"error": "Missing command parameter"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if title.lower() == command.lower():
                return jsonify({
                    "Command": title,
                    "Status": page["properties"]["Status"]["select"]["name"],
                    "Action": page["properties"]["Action"]["rich_text"][0]["text"]["content"]
                }), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Get-task failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status-counts", methods=["GET"])
def status_counts():
    check_api_key()
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        counts = {}
        for page in pages:
            status = page["properties"]["Status"]["select"]["name"]
            counts[status] = counts.get(status, 0) + 1
        return jsonify(counts), 200
    except Exception as e:
        logger.error(f"Status counts failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/duplicate", methods=["POST"])
def duplicate():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or "command" not in data:
        return jsonify({"error": "Missing required field: command"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if title == data["command"]:
                now = datetime.now().isoformat()
                notion.pages.create(
                    parent={"database_id": get_database_id()},
                    properties={
                        "Command": {"title": [{"text": {"content": f"{title} (Copy)"}}]},
                        "Action": page["properties"]["Action"],
                        "Status": page["properties"]["Status"],
                        "Created At": {"rich_text": [{"text": {"content": now}}]},
                        "Last Updated": {"rich_text": [{"text": {"content": now}}]}
                    }
                )
                return jsonify({"message": "Duplicated"}), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Duplicate failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/complete", methods=["POST"])
def complete():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or "command" not in data:
        return jsonify({"error": "Missing required field: command"}), 400
    try:
        notion = get_notion_client()
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            title = page["properties"]["Command"]["title"][0]["plain_text"]
            if title == data["command"]:
                notion.pages.update(
                    page_id=page["id"],
                    properties={
                        "Status": {"select": {"name": "Done"}},
                        "Last Updated": {"rich_text": [{"text": {"content": datetime.now().isoformat()}}]}
                    }
                )
                return jsonify({"message": "Marked complete"}), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Complete failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/daily-summary", methods=["GET"])
def daily_summary():
    check_api_key()
    today = date.today().isoformat()
    try:
        notion = get_notion_client()
        results = []
        pages = notion.databases.query(database_id=get_database_id())["results"]
        for page in pages:
            created = page["properties"].get("Created At", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if created.startswith(today):
                results.append({
                    "Command": page["properties"]["Command"]["title"][0]["plain_text"],
                    "Status": page["properties"]["Status"]["select"]["name"]
                })
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Daily summary failed: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Run the server
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Updated default port to 8000
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
