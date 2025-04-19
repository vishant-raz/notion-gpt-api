from flask import Flask, request, jsonify, abort
from notion_client import Client
import os

app = Flask(__name__)
notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

def check_auth(request):
    user_key = request.headers.get("X-API-Key")
    if user_key != os.getenv("API_KEY"):
        abort(401, "Unauthorized")

@app.route("/")
def home():
    return "🚀 Notion GPT API is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
