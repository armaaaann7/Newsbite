from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from newspaper import Article
import os
import json
import requests
from typing import Optional

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

@app.get("/")
def read_root():
    return {"message": "Hello, your backend is alive!"}

class ArticleRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    length: Optional[str] = "100-200"  # options: "50-100", "100-200", "200-300"

def extract_text_from_url(url: str) -> str:
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    resolved_url = url
    try:
        redirect_check = requests.get(url, headers=browser_headers, allow_redirects=True, timeout=10)
        resolved_url = redirect_check.url
    except Exception:
        pass

    try:
        article = Article(resolved_url)
        article.config.browser_user_agent = browser_headers["User-Agent"]
        article.config.request_timeout = 15
        article.download()
        article.parse()
        if not article.text or len(article.text.strip()) < 50:
            raise ValueError("empty")
        return article.text
    except Exception as e:
        error_str = str(e)
        if "403" in error_str:
            friendly_msg = "This website is blocking automated access. Try copying the article text directly instead, or use a different source."
        elif "404" in error_str:
            friendly_msg = "That link doesn't seem to lead to a valid page. Please check the URL."
        else:
            friendly_msg = "Couldn't read this article from the link provided. Try pasting the article text directly instead."
        raise HTTPException(status_code=400, detail=friendly_msg)

VALID_TOPICS = ["World", "Politics", "Business", "Tech", "Science", "Health", "Sports", "Entertainment", "Crime", "Environment", "Education", "Lifestyle", "Travel", "Food", "Automotive", "Opinion", "Weather", "Religion", "Military & Defense", "Real Estate"]

TOPIC_FALLBACKS = {
    "movies": "Entertainment", "movie": "Entertainment", "film": "Entertainment",
    "tv": "Entertainment", "celebrity": "Entertainment", "music": "Entertainment",
    "gaming": "Entertainment", "game": "Entertainment",
    "law": "Crime", "legal": "Crime", "court": "Crime",
    "climate": "Environment", "nature": "Environment",
    "war": "Military & Defense", "defense": "Military & Defense", "army": "Military & Defense",
    "housing": "Real Estate", "property": "Real Estate",
}

def normalize_topic(raw_topic: str) -> str:
    if raw_topic in VALID_TOPICS:
        return raw_topic
    lowered = raw_topic.lower()
    for keyword, mapped in TOPIC_FALLBACKS.items():
        if keyword in lowered:
            return mapped
    return "World"

@app.post("/summarize")
def summarize(request: ArticleRequest):
    if not request.text and not request.url:
        raise HTTPException(status_code=400, detail="Please provide either 'text' or 'url'.")

    if request.url:
        article_text = extract_text_from_url(request.url)
    else:
        article_text = request.text

    prompt = f"""Read the following news article and identify the distinct topics it covers — most articles cover just one topic, but some cover two or more clearly separate subjects.

For each topic, write a complete, well-written summary of approximately {request.length} words covering the key points, plus 5-8 relevant keywords.

For the "topic" field, pick the closest match from: World, Politics, Business, Tech, Science, Health, Sports, Entertainment, Crime, Environment, Education, Lifestyle, Travel, Food, Automotive, Opinion, Weather, Religion, Military & Defense, Real Estate. Movies, TV shows, and celebrities use "Entertainment".

Do not use quotation marks inside the summary text — paraphrase any quotes instead of repeating them word for word.

Article:
{article_text}
"""

    tools = [
        {
            "type": "function",
            "function": {
                "name": "return_article_analysis",
                "description": "Return the structured analysis of a news article, split into one or more topic sections.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "The single broad category this section belongs to. Must be one of: World, Politics, Business, Tech, Science, Health, Sports, Entertainment, Crime, Environment, Education, Lifestyle, Travel, Food, Automotive, Opinion, Weather, Religion, Military & Defense, Real Estate. Movies, TV shows, celebrities, and pop culture content use 'Entertainment'."
                                    },
                                    "subtopic": {
                                        "type": "string",
                                        "description": "A specific 1-3 word label, e.g. Football, Finance, Artificial Intelligence."
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": f"A thorough summary, approximately {request.length} words."
                                    },
                                    "keywords": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "5-8 relevant keywords."
                                    }
                                },
                                "required": ["topic", "subtopic", "summary", "keywords"]
                            }
                        }
                    },
                    "required": ["sections"]
                }
            }
        }
    ]

    last_error = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "return_article_analysis"}},
                temperature=0.2,
            )
            tool_call = response.choices[0].message.tool_calls[0]
            result = json.loads(tool_call.function.arguments)

            for section in result.get("sections", []):
                section["topic"] = normalize_topic(section.get("topic", ""))

            return result
        except Exception as e:
            last_error = e
            print(f"SUMMARIZE ERROR (attempt {attempt + 1}): {type(e).__name__}: {e}")

    raise HTTPException(
        status_code=502,
        detail="The AI had trouble analyzing this article. Please try again."
    )