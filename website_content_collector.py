import json
from openai import OpenAI
from scraper import fetch_website_links, fetch_website_contents

system_prompt = """
You are provided with a list of links found on a webpage.
You are able to decide which of the links would be most relevant to include in a brochure about the company,
such as links to an About page, or a Company page, or Careers/Jobs pages.
You should respond in JSON as in this example:

{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page", "url": "https://another.full.url/careers"}
    ]
}
"""

def get_links_user_prompt(url):
    user_prompt = f"""
    Here is the list of links on the website {url} -
    Please decide which of these are relevant web links for a brochure about the company, 
    respond with the full https URL in JSON format.
    Do not include Terms of Service, Privacy, email links.
    
    Links (some might be relative links):
    
    """
    
    links = fetch_website_links(url)
    user_prompt += "\n".join(links)
    return user_prompt

def select_relevant_links(url, model, client:OpenAI):
    print(f"Selecting relevant links for {url} by calling {model}...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_links_user_prompt(url)}
        ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    links = json.loads(result) # type: ignore
    print(f"Found {len(links['links'])} relevant links")
    return links

def fetch_page_and_all_relevant_links(url, model, client:OpenAI):
    contents = fetch_website_contents(url)
    relevant_links = select_relevant_links(url, model, client)
    result = f"## Landing Page:\n\n{contents}\n## Relevant Links:\n"
    for link in relevant_links['links']:
        result += f"\n\n### Link: {link['type']}\n"
        result += fetch_website_contents(link["url"])
    return result
