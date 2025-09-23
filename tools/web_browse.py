# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Xinchen Wang 王欣辰

import requests
from bs4 import BeautifulSoup
import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils.llm import get_llm_response
import argparse
import asyncio
from crawl4ai import AsyncWebCrawler
from urllib.parse import quote
import time, random
import subprocess
import json
def search_links(query):
    query = quote(query)
    url = f"https://cn.bing.com/search?q={query}"
    max_retry_node = 3
    results = []
    for retry in range(max_retry_node):
        file_path = '/home/tools/search_links.js'
        try:
            result = subprocess.run(['node', file_path, query], capture_output=True, text=True, check=True)
            print(result.stdout)
            print(result.stderr)
            links = json.loads(result.stdout)
            results.extend([('title', link) for link in links])
            if len(results) >= 3:
                results = results[:3]
                break
            else:
                delay = random.randint(1, 4)
                time.sleep(delay)
        except subprocess.CalledProcessError as e:
            if retry < max_retry_node - 1:
                delay = random.randint(1, 4)
                time.sleep(delay)
    return results

async def search_content(link):
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=link,
            word_count_threshold=10,
            excluded_tags=['form', 'header'],
            exclude_external_links=True,
            process_iframes=True,
            remove_overlay_elements=True,
            bypass_cache=False  
        )
        return result.markdown

def search_relevant_content(query, content):
    formatted_prompt = f"""\
You are an expert in summarizing web content. Your role is to analyze and summarize the web search results based on the given questions. 
Your task is to provide a clear, accurate, and direct summary of the search results.
The summary should capture the key points and main ideas presented in the search results. 

Questions: 
{query}

Web Searching Results:
{content}

Please just provide the summary of the search results below:
"""

    messages = [{"role": "system", "content": formatted_prompt}]
    relevant_content, _ = get_llm_response("gpt-4o-2024-05-13", messages)
    return relevant_content

def search_summarized_content(query, relevant_contents):
    relevant_contents = [f"***** Web Search Result {i+1} *****\n: {content}\n" for i, content in enumerate(relevant_contents)]
    formatted_prompt = f"""\
You are an expert in summarizing web content. Your role is to analyze and summarize the web search results based on the given questions. 
Your task is to provide a clear, accurate, and direct summary of the search results.
The summary should capture the key points and main ideas presented in the search results. 

Questions: 
{query}

Web Searching Results:
{relevant_contents}

Please provide the summary of the search results in the format below:

### Web Search Results:
XXX
"""

    messages = [{"role": "system", "content": formatted_prompt}]
    relevant_content, _ = get_llm_response("gpt-4o-2024-05-13", messages)
    return relevant_content

def run_search(query):

    results = search_links(query)
    relevant_contents = []
    for i, (title, link) in enumerate(results):
        content = asyncio.run(search_content(link,))
        relevant_content = search_relevant_content(query, content)
        relevant_contents.append(relevant_content)
    summarized_content = search_summarized_content(query, relevant_contents)
    return summarized_content

def main():
    parser = argparse.ArgumentParser(description="Search the web")
    parser.add_argument("-q", "--query", type=str, required=True)
    args = parser.parse_args()
    summarized_content = run_search(args.query)
    print(summarized_content)
    return summarized_content

if __name__ == "__main__":
    main()

