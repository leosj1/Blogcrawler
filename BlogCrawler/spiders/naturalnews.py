# -*- coding: utf-8 -*-
import json
import time
import scrapy
import requests
from lxml import html
from dateutil.parser import parse

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, tags_to_json

class NaturalnewsSpider(scrapy.Spider):
    name = 'naturalnews'
    domain = 'naturalnews.com'
    address = "https://www.naturalnews.com/"
    allowed_domains = ['naturalnews.com']
    start_urls = ['https://www.naturalnews.com/all-posts.html']

    def parse(self, response):
        for url in [self.address + x for x in response.xpath('//div[contains(@class, "f-p-title")]/h2/a/@href').getall()]:
            yield scrapy.Request(url, self.parse_blog)
        try:
            next_page = self.address + response.xpath('//li[contains(@class, "pagination-next")]/a/@href').get()    
            yield scrapy.Request(next_page, self.parse)
        except TypeError:
            print("End of the pages.")

    def parse_blog(self, response):
        #There are dead links on the pages that can't be processed
        if not "The page you are looking for cannot be found or is no longer available." in response.text:
            blog = Posts()
            blog['domain'] = self.domain
            blog['url'] = response.url
            blog['title'] = response.xpath('//*[@id="Headline"]/h1/text()').get()
            blog['author'] = response.xpath('//*[@id="Headline"]/p/span/a/text()').get()
            blog['published_date']= parse(response.xpath('//*[@id="Headline"]/p/span/text()').get().replace(' by: ', ''))
            blog['content'] = "".join(response.xpath('//*[@id="Col2"]/article/div[2]//text()').getall()).strip().replace('\n', ' ')
            blog['content_html'] = response.xpath('//*[@id="Col2"]/article/div[2]').get()
            blog['links'] = get_links(blog['content_html'])
            blog['tags'] = tags_to_json(response.xpath('//*[@id="Headline"]/p/span/i/a/text()').getall())
            yield blog

            #Stats
            stat = Stats()
            stat['domain'] = self.domain
            stat['url'] = response.url
            stat['views'] = get_views(response.url)
            stat['likes'] = None
            comment_data = get_comments(response.url)
            stat['comments'] = comment_data['total']
            yield stat

            for comment in comment_data['comments']:
                #Comments
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] = comment['id']
                parsed_comment['username'] = comment['author']['username'] if 'username' in comment['author'] else comment['author']['name']
                parsed_comment['user_id'] = comment['author']['id'] if 'id' in comment['author'] else None
                parsed_comment['comment'] = comment['raw_message']
                parsed_comment['comment_original'] = comment['message']
                parsed_comment['links'] = get_links(comment['message'])
                parsed_comment['upvotes'] = comment['likes']
                parsed_comment['downvotes'] = comment['dislikes']
                parsed_comment['published_date'] = parse(comment['createdAt'])
                parsed_comment['reply_count'] = len([x for x in comment_data['comments'] if str(x['parent']) == str(comment['id'])])
                parsed_comment['reply_to'] = comment['parent']
                yield parsed_comment



def get_views(article_url):
    endpoint = f'https://www.naturalnews.com/getviews2.asp?url={article_url}'
    data = requests.get(endpoint).json()
    return data

def get_comments(article_url):
    #Getting Thread
    endpoint = f"https://disqus.com/embed/comments/?f=naturalnews&t_u={article_url}"
    page = requests.get(endpoint)
    if page.status_code == 500: 
        #Page failed to load, trying agian
        time.sleep(2)
        page = requests.get(endpoint)
    tree = html.fromstring(page.content)
    try: 
        data = json.loads(tree.xpath('//*[@id="disqus-threadData"]/text()')[0])
    except IndexError:
        #Unable to get proper request for thread
        return {'total':0, 'comments':[]}

    #Sending request for comments
    if len(data['response']['posts']) != 0: 
        thread = data['response']['posts'][0]['thread']
        api_key = 'E8Uh5l5fHZ6gD8U3KycjAIAk46f68Zw7C6eW8WSjZvCLXebZ7p0r1yrYDrLilk2F'
        data = process_comments(thread, api_key)
    else: 
        #No comments
        data = {'total':0, 'comments':[]}
    return data

def process_comments(thread, api_key):
    processed_data = {'total':0, 'comments':[]}
    data = comment_request(thread, api_key)
    for item in data:
        processed_data['total'] += len(item['response'])
        processed_data['comments'] += item['response']
    return processed_data

def comment_request(thread, api_key, cursor='0:0:0'):
    data_list = []
    endpoint = f"https://disqus.com/api/3.0/threads/listPostsThreaded?limit=100&thread={thread}&forum=naturalnews&api_key={api_key}&cursor={cursor}"
    try: 
        data = requests.get(endpoint).json()
    #Error Handling
    except json.decoder.JSONDecodeError:
        #invalid response
        return []
    if data['code'] == 15:
        #Internal error getting response, trying again
        print("Trying to get comments again: {}".format(data))
        time.sleep(2)
        data_list += comment_request(thread, api_key)
    #Proper Response
    elif data['code'] == 0:
        if data['cursor']['more'] == True:
            #Recursive for multi pages of comments
            data_list += comment_request(thread, api_key, cursor=data['cursor']['next'])
        data_list.append(data)
    
    else:
        raise Exception(data)
    return data_list

