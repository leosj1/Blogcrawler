from BlogCrawler.pipelines import get_connection
from urllib.parse import urlparse
import pycountry
import scrapy
import json
import os
import re


def links_to_json(links):
    if links: 
        df = {'links':links}
        return json.dumps(df)
    else:
        return None

def get_links(html):
    return links_to_json(re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+',html.replace('};', '')))

def get_matching_links(html, match_str):
    links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+',html.replace('};', ''))
    return [link for link in links if match_str in link]

def get_domain(url):
    return urlparse(url).netloc
    
def get_start_urls(domain):
    connection = get_connection()
    with connection.cursor() as cursor: 
        cursor.execute("SELECT url FROM posts where domain = %s;", domain)
        records = [x['url'] for x in cursor.fetchall()]
    connection.close()
    return records