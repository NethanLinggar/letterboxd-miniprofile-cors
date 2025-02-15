from flask import Flask, jsonify
from flask_cors import CORS
from letterboxdpy.user import User
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

def get_poster_url(slug):
    poster_ajax = f"https://letterboxd.com/ajax/poster/film/{slug}/std/500x750/"
    response = requests.get(poster_ajax)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img")
        if img_tag and "srcset" in img_tag.attrs:
            return img_tag["srcset"].split(" ")[0]  # Get first URL in srcset
    return None  # Fallback if no image found

@app.route("/")
def home():
    return "Letterboxd API Proxy is running!"

@app.route("/<username>")
def get_profile(username):
    try:
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
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
