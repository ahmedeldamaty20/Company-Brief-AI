import os
import re
import sys
import gradio as gr
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from website_content_collector import fetch_page_and_all_relevant_links

# Initialize and constants

load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
openai_model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')

gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_url = os.getenv('GEMINI_URL')
gemini_model = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')

MAX_CONTENT_CHARS = int(os.getenv('MAX_CONTENT_CHARS', 20000))
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'brochures'))

if not (openai_api_key and openai_api_key.startswith("sk-proj-")):
    print("There might be a problem with your API key.")
if not (gemini_api_key and gemini_api_key.startswith("AIza")):
    print("There might be a problem with your GEMINI API key.")

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

def _build_messages(company_name, client, model, url):
    site_content = fetch_page_and_all_relevant_links(url, model, client)
    return [
        {"role": "system", "content": brochure_system_prompt},
        {"role": "user", "content": build_brochure_user_prompt(company_name, site_content)},
    ]

def create_brochure(company_name, client, model, url):
    response = client.chat.completions.create(
        model=model,
        messages=_build_messages(company_name, client, model, url),
    )
    return response.choices[0].message.content

def create_brochure_stream(company_name, client, model, url):
    stream = client.chat.completions.create(
        model=model,
        messages=_build_messages(company_name, client,   model, url),
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

def get_client(model):
    if model.startswith("gemini"):
        return OpenAI(api_key=gemini_api_key, base_url=gemini_url)
    else:
        return OpenAI(api_key=openai_api_key)

def generate_brochure(name, url, using_stream, provider):
    client = get_client(provider)

    model = gemini_model if provider.startswith("Gemini") else openai_model

    if using_stream:
        brochure = ""
        for chunk in create_brochure_stream(name, client, model, url):
            brochure += chunk
            yield brochure
    else:
        brochure = create_brochure(name, client, model, url)
        yield brochure
    
if __name__ == "__main__":

    name_input = gr.Textbox(label="Company Name:")
    url_input = gr.Textbox(label="Landing Page URL:", info="Include the full https URL of the company's landing page.")
    using_stream_input = gr.Checkbox(label="Use streaming?", info="If checked, the brochure will be generated in a streaming fashion.")
    provider_selector = gr.Dropdown(["GPT", "Gemini"], label="Select Provider", value="GPT")
    message_output = gr.Markdown(label="Response:")

    gr.Interface(
        fn=generate_brochure,
        title="Company Brochure Generator",
        inputs=[name_input, url_input, using_stream_input, provider_selector],
        outputs=message_output,
        examples=[
            ["AKVELON", "https://akvelon.com", False, "GPT"],
            ["AKVELON", "https://akvelon.com", True, "GPT"],
            ["AKVELON", "https://akvelon.com", False, "Gemini"],
            ["AKVELON", "https://akvelon.com", True, "Gemini"],
        ],
        flagging_mode="never",
    ).launch()

    # name = sys.argv[1] if len(sys.argv) > 1 else "AKVELON"
    # site = sys.argv[2] if len(sys.argv) > 2 else "https://akvelon.com"
    # using_stream = sys.argv[3].lower() == "stream" if len(sys.argv) > 3 else False
    # provider = sys.argv[4] if len(sys.argv) > 4 else "GPT"

    # brochure = ""
    # for chunk in generate_brochure(name, site, using_stream, provider):
    #     brochure += str(chunk)
    #     print(chunk, end="", flush=True)

    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # with open(OUTPUT_DIR / f"{slugify(name)}_brochure.md", "w", encoding="utf-8") as f:
    #     f.write(brochure) # type: ignore
