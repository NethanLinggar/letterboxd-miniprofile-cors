from flask import Flask, jsonify
from flask_cors import CORS
from letterboxdpy.user import User
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def get_poster_url(slug):
    poster_ajax = f"https://letterboxd.com/ajax/poster/film/{slug}/std/500x750/"
    try:
        response = requests.get(poster_ajax, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            img_tag = soup.find("img")
            if img_tag and "srcset" in img_tag.attrs:
                return img_tag["srcset"].split(" ")[0]
    except Exception as e:
        print(f"Error fetching poster: {e}")
    return None

@app.route("/")
def home():
    return "Letterboxd API Proxy is running!"

@app.route("/<username>")
def get_profile(username):
    try:
        # Try to manually scrape instead of using letterboxdpy
        url = f"https://letterboxd.com/{username}/"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": f"User not found or Letterboxd returned {response.status_code}"}), 404
        
        # If manual scraping works, fall back to letterboxdpy
        user_instance = User(username)
        user_data = user_instance.jsonify()

        stats = user_data.get("stats", {})

        filtered_data = {
            "avatar": user_data["avatar"]["url"] if user_data.get("avatar") else None,
            "display_name": user_data.get("display_name"),
            "user_url": user_data.get("url"),
            "followers": stats.get("followers", 0),
            "following": stats.get("following", 0),
            "films_watched": stats.get("films", 0),
            "this_year": stats.get("this_year", 0),
            "lists": stats.get("lists") if stats.get("lists") is not None else stats.get("list", 0),
            "favorites": []
        }

        if "favorites" in user_data:
            for film in list(user_data["favorites"].values())[:4]:
                slug = film["slug"]
                poster_url = get_poster_url(slug)
                filtered_data["favorites"].append({
                    "name": film["name"],
                    "slug": slug,
                    "poster": poster_url
                })

        return jsonify(filtered_data)
    except Exception as e:
        return jsonify({"error": str(e), "details": "Check if Letterboxd is blocking requests"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)