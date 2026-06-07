from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    youtube_url = data.get("url")

    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    video_id = get_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        fetcher = YouTubeTranscriptApi()
        transcript_list = fetcher.fetch(video_id)
        transcript_text = " ".join([chunk.text for chunk in transcript_list])
    except Exception as e:
        return jsonify({"error": f"Could not get transcript: {str(e)}"}), 400

    prompt = f"""
    You are an educational assistant. I will give you a video transcript.

    Please do TWO things:

    PART 1 - SUMMARY:
    Summarize the video in exactly 5 bullet points. Each point should be one clear sentence.

    PART 2 - QUIZ:
    Create 3 multiple choice questions based on the video.
    Each question should have 4 options (A, B, C, D) and one correct answer.

    Format your response as JSON like this:
    {{
      "summary": ["point 1", "point 2", "point 3", "point 4", "point 5"],
      "quiz": [
        {{
          "question": "What is ...?",
          "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
          "answer": "A"
        }}
      ]
    }}

    Here is the transcript:
    {transcript_text[:8000]}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return jsonify(result)
        else:
            return jsonify({"error": "AI response was not valid JSON"}), 500
    except Exception as e:
        return jsonify({"error": f"AI error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)