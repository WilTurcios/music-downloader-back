# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response
import json
from flask_cors import CORS
from pytubefix import YouTube
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*", methods=["GET", "POST"], allow_headers=["Content-Type"])

# Ensure Flask's JSON responses don't escape non-ASCII characters
app.config['JSON_AS_ASCII'] = False


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

@app.route('/', methods=['GET'])
def home():
    payload = {"message": "This is the main endpoint"}
    return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json; charset=utf-8'), 200

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    maxResults = int(request.args.get('maxResults', 50))
    all_songs = []
    nextPageToken = None

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    search_query = f"{query} music"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={search_query}&key={YOUTUBE_API_KEY}&maxResults={maxResults}"
    
    if nextPageToken:
        url += f"&pageToken={nextPageToken}"

    try:
        response = requests.get(url).json()

        if "items" not in response:
            return jsonify({"error": "No results found"}), 404

        for item in response["items"]:
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            description = item["snippet"]["description"]
            channel_title = item["snippet"]["channelTitle"]
            publish_time = item["snippet"]["publishTime"]
            thumbnail = item["snippet"]["thumbnails"]["medium"]

            all_songs.append({
                "title": title,
                "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
                "videoId": video_id,
                "description": description,
                "channelTitle": channel_title,
                "thumbnail": thumbnail,
                "publishTime": publish_time
            })

        # Check if there is a next page token to continue fetching
        nextPageToken = response.get("nextPageToken")
        
        if nextPageToken:
            next_page_url = f"/search?query={query}&maxResults={maxResults}&pageToken={nextPageToken}"
        else:
            next_page_url = None

        # Return the current page's songs and the next page URL using UTF-8 JSON
        payload = {
            "songs": all_songs,
            "nextPageUrl": next_page_url
        }
        return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json; charset=utf-8'), 200

    except Exception as e:
        payload = {"error": str(e)}
        return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json; charset=utf-8'), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    urls = data.get('urls')
    
    if not urls:
        return jsonify({"error": "No URLs provided in the request"}), 400

    results = []
    
    for url in urls:
        try:
            yt = YouTube(url)  # No headers needed by default
            audio_stream = yt.streams.filter(only_audio=True).first()
            if not audio_stream:
                raise Exception("No audio stream available")
            
            download_folder = "downloads/"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            file_path = audio_stream.download(output_path=download_folder)
            results.append({"url": url, "status": "success", "file_path": file_path})
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})
    
    return Response(json.dumps(results, ensure_ascii=False), mimetype='application/json; charset=utf-8'), 200


if __name__ == '__main__':
    if not os.path.exists("downloads/"):
        os.makedirs("downloads/")
    app.run(debug=True)