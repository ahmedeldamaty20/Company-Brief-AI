import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from website_content_collector import fetch_page_and_all_relevant_links

# Initialize and constants

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')
MODEL = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
MAX_CONTENT_CHARS = int(os.getenv('MAX_CONTENT_CHARS', 20000))
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'brochures'))

if not (api_key and api_key.startswith("sk-proj-")):
    print("There might be a problem with your API key.")

client = OpenAI(api_key=api_key)

brochure_system_prompt = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short brochure about the company for prospective customers, investors and recruits.
Respond in markdown without code blocks.
Include details of company culture, customers and careers/jobs if you have the information.
"""

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def build_brochure_user_prompt(company_name, site_content):
    header = (
        f"You are looking at a company called: {company_name}\n"
        "Here are the contents of its landing page and other relevant pages;\n"
        "use this information to build a short brochure of the company "
        "in markdown without code blocks.\n\n"
    )
    return header + site_content[:MAX_CONTENT_CHARS]

def _build_messages(company_name, url):
    site_content = fetch_page_and_all_relevant_links(url, MODEL, client)
    return [
        {"role": "system", "content": brochure_system_prompt},
        {"role": "user", "content": build_brochure_user_prompt(company_name, site_content)},
    ]

def create_brochure(company_name, url):
    response = client.chat.completions.create(
        model=MODEL,
        messages=_build_messages(company_name, url),
    )
    return response.choices[0].message.content

def create_brochure_stream(company_name, url):
    stream = client.chat.completions.create(
        model=MODEL,
        messages=_build_messages(company_name, url),
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
    
if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "AKVELON"
    site = sys.argv[2] if len(sys.argv) > 2 else "https://akvelon.com"
    using_stream = sys.argv[3].lower() == "stream" if len(sys.argv) > 3 else False

    if using_stream:
        print("Creating brochure with streaming...")
        brochure = ""
        for chunk in create_brochure_stream(name, site):
            brochure += chunk
            print(chunk, end="", flush=True)
    else:
        brochure = create_brochure(name, site)
        print(brochure)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / f"{slugify(name)}_brochure.md", "w", encoding="utf-8") as f:
        f.write(brochure) # type: ignore
