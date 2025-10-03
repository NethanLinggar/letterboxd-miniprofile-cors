from flask import Flask, jsonify
from flask_cors import CORS
from letterboxdpy.user import User
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# TMDb API Configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def get_movie_name_from_slug(slug):
    """Extract movie name and year from Letterboxd slug"""
    try:
        url = f"https://letterboxd.com/film/{slug}/"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Get movie title
            title_tag = soup.find("meta", property="og:title")
            if title_tag:
                title = title_tag.get("content", "").split(" (")[0]
                
                # Get year
                year_tag = soup.find("meta", property="og:url")
                if year_tag:
                    url_content = year_tag.get("content", "")
                    # Extract year from URL or page
                    year_div = soup.find("div", class_="releaseyear")
                    year = year_div.text.strip() if year_div else None
                    
                    return title, year
    except Exception as e:
        print(f"Error extracting movie info: {e}")
    return None, None

def get_poster_from_tmdb(movie_name, year=None):
    """Get movie poster from TMDb API"""
    try:
        # Search for the movie
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': movie_name
        }
        if year:
            params['year'] = year
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                poster_path = data['results'][0].get('poster_path')
                if poster_path:
                    return f"{TMDB_IMAGE_BASE_URL}{poster_path}"
    except Exception as e:
        print(f"Error fetching poster from TMDb: {e}")
    return None

def get_poster_url(slug, movie_name=None):
    """Get poster URL from TMDb API only"""
    if not movie_name:
        movie_name, year = get_movie_name_from_slug(slug)
    else:
        year = None
    
    if movie_name:
        tmdb_poster = get_poster_from_tmdb(movie_name, year)
        if tmdb_poster:
            return tmdb_poster
    
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
                movie_name = film["name"]
                poster_url = get_poster_url(slug, movie_name)
                filtered_data["favorites"].append({
                    "name": movie_name,
                    "slug": slug,
                    "poster": poster_url
                })

        return jsonify(filtered_data)
    except Exception as e:
        return jsonify({"error": str(e), "details": "Check if Letterboxd is blocking requests"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)