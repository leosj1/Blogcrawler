# -*- coding: utf-8 -*-
import requests
import urllib
import scrapy
import json

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json, parse_datetime
from BlogCrawler.comments_api import facebook_comments

#Initalize Functions
def get_api_pages_wrapper(base_urls):
    #A wrapper for get_api_page
    links = []
    for base_url in base_urls:
        links += get_api_pages(base_url)
    return links

def get_api_pages(base_url, page_count=1):
    data_list = []
    url = f"{base_url}?page={page_count}&page_size=10"
    data = requests.get(url).json()
    if data['results']:
        data_list += ([x['url'] for x in data['results']])
    else:
        return []
    #loop
    data_list += get_api_pages(base_url, page_count+1)
    return data_list


class BuzzfeednewsSpider(scrapy.Spider):
    name = 'buzzfeednews'
    domain = 'buzzfeednews.com'
    allowed_domains = ['buzzfeednews.com']
    start_urls = ['https://www.buzzfeednews.com/', 'https://www.buzzfeednews.com/section/arts-entertainment', 'https://www.buzzfeednews.com/section/business', 'https://www.buzzfeednews.com/investigations', 'https://www.buzzfeednews.com/section/lgbtq', 'https://www.buzzfeednews.com/collection/opinion', 'https://www.buzzfeednews.com/section/politics', 'https://www.buzzfeednews.com/section/reader', 'https://www.buzzfeednews.com/section/science', 'https://www.buzzfeednews.com/section/tech', 'https://www.buzzfeednews.com/section/world']
    # #Getting API pages
    base_urls = ['https://www.buzzfeednews.com/site-component/v1/en-us/trending-on-buzzfeednews']
    links = get_api_pages_wrapper(base_urls) + get_start_urls(domain)

    def parse(self, response):
        self.links += get_matching_links(response.body.decode('utf-8'), 'https://www.buzzfeednews.com/article/')
        for url in self.links:
            yield scrapy.Request(url, self.parse_article)

    def parse_article(self, response):
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath('//*[@class="news-article-header__title"]/text()').get()
        blog['author'] = response.xpath('//*[@class="news-byline-full__info-wrapper"]/span/text()').get()
        blog['published_date']= get_date(response.xpath('//*[@class="news-article-header__timestamps-posted"]/text()').get())
        blog['content'] = " ".join(response.xpath('//*[@id="js-post-container"]/div/div[1]/div[1]/div/p/text()').getall()).strip()
        blog['content_html'] = " ".join(response.xpath('//*[@id="js-post-container"]/div/div[1]/div[1]/div').getall())
        blog['links'] = get_links(blog['content_html'])
        blog['tags'] = tags_to_json(parse_tags(response))
        yield blog

        #Comments requests
        article_url = format_comment_url(response.url)
        comment_data = facebook_comments(article_url, '162111247988300')
        comments = comment_data['comments']
        authors = comment_data['authors']
        reply_dic = comment_data['reply_dic']
        if comments: #Catches no comments
            for c in comments: 
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] = c['id']
                parsed_comment['username'] = [x['name'] for x in authors if c['authorID'] == x['id']][0]
                parsed_comment['user_id'] = c['authorID']
                parsed_comment['comment'] = c['body']['text']
                parsed_comment['comment_original'] = None
                parsed_comment['links'] = get_links(c['body']['text'])
                parsed_comment['upvotes'] = c['likeCount']
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = parse_datetime(c['timestamp']['text'])
                if 'public_replies' in c:
                    parsed_comment['reply_count'] = len([x for x in comments if 'targetID' in x and x['targetID'] == c['id']])
                else:
                    parsed_comment['reply_count'] = 0
                if c['id'] in reply_dic:
                    parsed_comment['reply_to'] = reply_dic[c['id']]
                else:
                    parsed_comment['reply_to'] = None
                yield parsed_comment

        #Stats
        stat = Stats()
        stat['domain'] = self.domain
        stat['url'] = response.url
        stat['views'] = None
        stat['likes'] = None
        if comments is None: 
            stat['comments'] = 0
        else:
            stat['comments'] = len(comments) 
        yield stat
        
def format_comment_url(url):
    article_url = url.replace('https://www.buzzfeednews.com/article/', '')
    base_url = "https://www.buzzfeed.com/"
    return base_url + article_url
    
def get_date(date_string):
    date_string = date_string.strip()
    date_string = date_string.replace('Posted on ', '')
    date_string = date_string.replace('Last updated on ', '')
    return parse_datetime(date_string)

def parse_tags(response):
    tag_script = response.xpath("//script[contains(., 'window.BZFD')]/text()").extract_first().strip().replace(' ','').replace('\n','').replace('window.BZFD={Config:','').replace('},Context:{',',')
    if tag_script[-2:] == '};':
        data = json.loads(tag_script[:-2])
        tag_list = data['buzz']['tags']
        results = [x.replace("--primarykeyword-", '') for x in tag_list if '--' not in x or 'primarykeyword' in x]
        return list(set(results))