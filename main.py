from flask import Flask, request, jsonify, abort
from notion_client import Client
import os
import time

# API key for secure access
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is not set!")

def check_api_key():
    incoming_key = request.headers.get("X-API-Key")
    if incoming_key != API_KEY:
        abort(401, description="Unauthorized")

# Notion & Flask setup
app = Flask(__name__)
notion_token = os.getenv("NOTION_TOKEN")
if not notion_token:
    raise RuntimeError("NOTION_TOKEN environment variable is not set!")

notion = Client(auth=notion_token)
database_id = os.getenv("NOTION_DATABASE_ID")
if not database_id:
    raise RuntimeError("NOTION_DATABASE_ID environment variable is not set!")

def validate_database_schema():
    try:
        database = notion.databases.retrieve(database_id=database_id)
        required_properties = ["Command", "Action", "Status"]
        for prop in required_properties:
            if prop not in database["properties"]:
                raise RuntimeError(f"Missing required property: {prop}")
    except Exception as e:
        raise RuntimeError(f"Failed to validate database schema: {str(e)}")

validate_database_schema()

@app.route("/")
def home():
    return "🚀 Notion GPT API is running!"

@app.route("/create", methods=["POST"])
def create():
    check_api_key()
    data = request.get_json(silent=True)
    if not data or not all(key in data for key in ["command", "action", "status"]):
        return jsonify({"error": "Missing required fields: command, action, status"}), 400

    try:
        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Command": {"title": [{"text": {"content": data["command"]}}]},
                "Action": {"rich_text": [{"text": {"content": data["action"]}}]},
                "Status": {"select": {"name": data["status"]}}
            }
        )
        return jsonify({"message": "Created"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to create page: {str(e)}"}), 500

# Other routes remain similar with error handling added

# --------------------
# UPDATE route
# --------------------
@app.route("/update", methods=["POST"])
def update():
    check_api_key()

    data = request.json
    if not data or not all(key in data for key in ["command", "action", "status"]):
        return jsonify({"error": "Missing required fields: command, action, status"}), 400

    query = notion.databases.query(database_id=database_id)
    for page in query["results"]:
        title = page["properties"]["Command"]["title"][0]["plain_text"]
        if title == data["command"]:
            notion.pages.update(
                page_id=page["id"],
                properties={
                    "Action": {"rich_text": [{"text": {"content": data["action"]}}]},
                    "Status": {"select": {"name": data["status"]}}
                }
            )
            return jsonify({"message": "Updated"}), 200
    return jsonify({"error": "Task not found"}), 404

# --------------------
# DELETE route
# --------------------
@app.route("/delete", methods=["POST"])
def delete():
    check_api_key()

    data = request.json
    if not data or "command" not in data:
        return jsonify({"error": "Missing required field: command"}), 400

    query = notion.databases.query(database_id=database_id)
    for page in query["results"]:
        title = page["properties"]["Command"]["title"][0]["plain_text"]
        if title == data["command"]:
            notion.pages.update(page_id=page["id"], archived=True)
            return jsonify({"message": "Deleted"}), 200
    return jsonify({"error": "Task not found"}), 404

# --------------------
# FETCH route
# --------------------
@app.route("/fetch", methods=["GET"])
def fetch():
    check_api_key()

    query = notion.databases.query(database_id=database_id)
    results = []
    for page in query["results"]:
        title = page["properties"]["Command"]["title"][0]["plain_text"]
        status = page["properties"]["Status"]["select"]["name"]
        results.append({"Command": title, "Status": status})
    return jsonify(results), 200

# --------------------
# RUN APP
# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)