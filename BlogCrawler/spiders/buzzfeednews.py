# -*- coding: utf-8 -*-
import dateutil.parser
import requests
import urllib
import scrapy
import json

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links

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
    data = requests.get(url, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}).json()
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
            yield scrapy.Request(url, self.parse_article, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})

    def parse_article(self, response):
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath('//*[@id="js-post-container"]/div/div[1]/header/h1/text()').get()
        blog['author'] = response.xpath('//*[@id="js-post-container"]/div/div[1]/header/div[2]/a/span/span[1]/text()').get()
        blog['published_date']= get_date(response.xpath('//*[@id="js-post-container"]/div/div[1]/header/div[3]/p/text()').get())
        blog['content'] = ' '.join(response.xpath('//*[@id="js-post-container"]/div/div[1]/div[1]/div/p/text()').getall()).strip()
        blog['content_html'] = " ".join(response.xpath('//*[@id="js-post-container"]/div/div[1]/div[1]/div').getall())
        blog['links'] = get_links(blog['content_html'])
        blog['tags'] = None
        yield blog

        #Comments requests
        article_url = response.url.replace('https://www.buzzfeednews.com/article/', '')
        comments, authors = get_comments(article_url)
        reply_dic = get_reply_dic(comments)
        if comments: #Catches no comments
            for c in comments: 
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] = c['id']
                parsed_comment['username'] = [x['name'] for x in authors if c['authorID'] == x['id']][0]
                parsed_comment['user_id'] = c['authorID']
                parsed_comment['comment'] = c['body']['text']
                parsed_comment['comment_original'] = c['body']['text']
                parsed_comment['links'] = get_links(c['body']['text'])
                parsed_comment['upvotes'] = c['likeCount']
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = dateutil.parser.parse(c['timestamp']['text'])
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
        

def get_comments(post_url):
    #Changing the urls
    base_url = "https://www.buzzfeed.com/"
    buzzfeed_url = base_url + post_url
    buzzfeed_url = urllib.parse.quote(buzzfeed_url, safe='')
    url = f"https://www.facebook.com/plugins/feedback.php?app_id=162111247988300&href={buzzfeed_url}"
    #Sending request for fb Iframe
    r = requests.get(url, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
    #Getting the main comment id for the article
    pos = r.text.find("commentIDs") + len("commentIDs") + 4
    comment_id = r.text[pos:pos+16]

    #Sending the API request for comments, loading data
    url = f'https://www.facebook.com/plugins/comments/async/{comment_id}/pager/social/'
    form_data = {
    'limit': 500000,
    '__a': 1}
    session = requests.Session()
    r = session.post(url, data=form_data)
    if len(r.content) <= 13:
        #No comments on the page
        return None, None
    else: 
        try: 
            data = json.loads(r.content[9:])
        except Exception as e: 
            if "something went wrong" in r.content.decode('utf-8'): #This only happened once with a very old commnet
                # error_url = f"https://www.facebook.com/plugins/feedback.php?app_id=162111247988300&href={buzzfeed_url}"
                # raise Exception(f"Facebook had trouble getting these comments: {error_url}")
                pass
            else: 
                print(e)

    #Parsing the comments
    comment_list = []
    author_list = []
    comments = data['payload']['idMap']
    for item in comments:
        # Checking if it's a comment, comments have a longer id than just the comment id, checking that is comment type
        if comment_id in item and comment_id != item and comments[item]['type'] == 'comment':
            comment_list.append(comments[item])
            #Sending additional requests for replies
            if 'public_replies' in comments[item] and 'afterCursor' in comments[item]['public_replies']:
                replies, authors = get_replies(item, comments[item]['public_replies']['afterCursor'])
                comment_list += replies
                author_list += authors
        else:
            author_list.append(comments[item])
    return comment_list, author_list


def get_replies(comment_id, after_cursor):
    #Sending replies request, loading data
    url = f'https://www.facebook.com/plugins/comments/async/comment/{comment_id}/pager/'
    form_data = {
    'after_cursor': after_cursor,
    'limit': 500000,
    '__a': 1
    }
    session = requests.Session()
    r = session.post(url, data=form_data)
    data = json.loads(r.content[9:])

    #Resettign comment id, parsing replies
    comment_list = []
    author_list = []
    original_id = comment_id
    comment_id = comment_id[:16]
    comments = data['payload']['idMap']
    for item in comments:
        # Checking if it's a comment, comments have a longer id than just the comment id, checking that it is comment type
        if comment_id in item and comment_id != item and comments[item]['type'] == 'comment':
            comment_list.append(comments[item])
            #Sending additional requests for replies
            if 'public_replies' in comments[item] and 'afterCursor' in comments[item]['public_replies']:
                replies, authors = get_replies(item, comments[item]['public_replies']['afterCursor'])
                comment_list += replies
                author_list += authors
        elif item != original_id:
            author_list.append(comments[item])
    return comment_list, author_list

def get_reply_dic(comments):
    if comments:
        dic = {}
        for comment in comments:
            if 'public_replies' in comment:
                try:
                    for cid in comment['public_replies']['commentIDs']:
                        dic[cid] = comment['id']
                except KeyError:
                    # This does not seem to effect the reply author lookup dic (duplicate comments in data but not in blog)
                    # raise Exception(f"Facebook API missing reply id's in this blog: {comment['ogURL']}")
                    pass
        return dic
    else: #No comments
        return None 


def get_date(date_string):
    date_string = date_string.strip()
    date_string = date_string.replace('Posted on ', '')
    date_string = date_string.replace('Last updated on ', '')
    return dateutil.parser.parse(date_string)