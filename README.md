# Newsbite

Paste a news article or a link, and get back a structured summary — key points, topic and subtopic tags, keywords, and an adjustable length (short, medium, or long).

Most summarizer demos just paraphrase whatever text you give them. Newsbite goes a step further: it detects when an article actually covers more than one topic — which happens a lot in longer news pieces — and splits it into separate, individually categorized sections instead of blending everything into one paragraph.

## Features

- **Paste text or a link** — either works. Links are automatically scraped and cleaned before summarization.
- **Multi-topic detection** — articles covering more than one subject are split into distinct sections, each with its own topic, subtopic, summary, and keywords.
- **Adjustable summary length** — choose short (50-100 words), medium (100-200), or long (200-300) per request.
- **20-category topic classification** — covers everything from Sports and Politics to Crime, Environment, and Real Estate, with a specific free-form subtopic on top (e.g. "Football," "Artificial Intelligence").
- **Graceful failure handling** — if a site blocks scraping or the AI response is malformed, the app shows a clear message and automatically retries once before giving up.

## Tech stack

**Backend**
- FastAPI — REST API framework
- Groq — LLM inference (currently using openai/gpt-oss-120b)
- newspaper4k — article extraction from URLs
- Python's requests for redirect resolution on shortened links

**Frontend**
- Plain HTML, CSS, and JavaScript — no framework, no build step
- Google Fonts (Fraunces + Lora) for the editorial look

## How it works

1. The frontend sends either raw article text or a URL to the /summarize endpoint.
2. If a URL is given, the backend resolves any redirects, fetches the page with browser-like headers, and extracts the clean article text.
3. The article text is sent to an LLM with a structured schema (via tool calling) that forces the response into a strict shape — no more hoping the AI's JSON is well-formed.
4. The backend validates the AI's chosen topic against a fixed list of 20 categories, silently correcting it if it doesn't match (e.g. "Movies" becomes "Entertainment").
5. If the AI call fails, the backend automatically retries once before returning a clean error message.

## Running it locally

### 1. Clone the repo

git clone https://github.com/armaaaann7/Newsbite.git
cd Newsbite

### 2. Set up a virtual environment

python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies

pip install fastapi uvicorn python-dotenv groq newspaper4k lxml_html_clean requests

### 4. Add your API key

Create a .env file in the project root with the following two lines:

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

Get a free key at console.groq.com

### 5. Run the backend

uvicorn main:app --reload

### 6. Open the frontend

Just open index.html directly in your browser (double-click the file, or drag it into a browser window).

## Known limitations

- Some news sites (particularly larger publishers with anti-bot protection) will block automated article extraction. When this happens, the app shows a clear error and suggests pasting the article text directly instead.
- Topic classification is done via LLM prompting rather than a trained classifier, so it's not guaranteed to be perfect on every article — though the backend validates and corrects the AI's output before returning it.

## Roadmap

- [ ] Saved history (PostgreSQL)
- [ ] User accounts
- [ ] Sentiment analysis
- [ ] Reading time estimate
- [ ] Batch summarization (multiple URLs to one digest)
- [ ] Multi-language support
- [ ] Automated daily digest
