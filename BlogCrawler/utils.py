from BlogCrawler.pipelines import get_connection
from urllib.parse import urlparse
from json import JSONDecoder
import pycountry
import scrapy
import json
import os
import re
from dateutil.parser import parse

def tags_to_json(tags):
    if tags:
        df = {'tags':tags}
        return json.dumps(df)
    else:
        return None

def links_to_json(links):
    if links: 
        df = {'links':links}
        return json.dumps(df)
    else:
        return None

def get_links(html):
    if type(html) == None: raise TypeError('''Passed a None object to get links. 
        This should be the html of the page, so look into your code why you aren't selecting the hmtl properly.''')
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

def get_users(domain):
    connection = get_connection()
    with connection.cursor() as cursor: 
        cursor.execute("SELECT username, user_id FROM comments where domain = %s;", domain)
        user_dict = {}
        for x in cursor.fetchall():
            user_dict[x['username']] = x['user_id']      
    connection.close()
    return user_dict

def parse_datetime(date):
    if 'EDT' in date:
        result = parse(date, tzinfos={"EDT": "UTC-5"}) 
    elif 'EST' in date:
        result = parse(date, tzinfos={"EST": "UTC-5"}) 
    else:
        result = parse(date) 
    return result

def find_json(text, decoder=JSONDecoder()):
    """Find JSON objects in text, and yield the decoded JSON data
    https://stackoverflow.com/questions/54235528/how-to-find-json-object-in-text-with-python
    Does not attempt to look for JSON arrays, text, or other JSON types outside
    of a parent JSON object.
    """
    results = []
    pos = 0
    while True:
        match = text.find('{', pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            if result: results.append(result)
            pos = match + index
        except ValueError:
            pos = match + 1
    return results

def author_title(author):
    result = author
    if ' and ' in result or ' & ' in result:
        result_split = result.split('and')
        res = 'and'.join([x.title() for x in result_split])
    elif result.isupper():
        return result.title()
    else:
        res = result
    return res.title()