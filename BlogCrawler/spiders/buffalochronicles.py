# -*- coding: utf-8 -*-
import scrapy
from dateutil.parser import parse
import json
import requests

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json, get_users

class BuffalochroniclesSpider(scrapy.Spider):
    name = 'buffalochronicles'
    allowed_domains = ['buffalochronicle.com']
    domain = 'buffalochronicle.com'
    start_urls = ['https://buffalochronicle.com/']
    user_agent = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    comment_users = get_users(domain) #For generating user ids

    def parse(self, response):
        #Getting links to catagories
        if response.url == 'https://buffalochronicle.com/':
            for link in response.css("#menu-subjects a").xpath("@href").extract():
                yield scrapy.Request(link)

        #Getting post urls
        all_div = response.css('.mh-posts-grid-col')
        for data in all_div:
            urls = data.css(".mh-posts-grid-title a").xpath("@href").extract()
            for url in urls:
                yield scrapy.Request(url, self.parse_blog)

        #Next page
        next_page = response.xpath("//a[contains(@class, 'next page-numbers')]/@href").extract_first()
        if next_page: yield scrapy.Request(next_page, self.parse)

    def parse_blog(self, response):
        # Posts
        pid = response.css('article').xpath("@id").extract_first().strip().replace(' ','').split('-')[1]
        data = get_stats_data(pid)
        
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.css("h1.entry-title::text").extract_first()
        blog['author'] = parse_author(data, response)
        blog['published_date'] = parse(response.css("span.entry-meta-date.updated a::text").extract_first())
        blog['content'] = "".join(response.xpath("//div[contains(@class, 'entry-content')]//text()").extract()).strip().replace('\n', ' ').replace('\t', ' ')
        blog['content_html'] = "".join(response.xpath("//div[contains(@class, 'entry-content')]").extract())
        blog['links'] = get_links("".join(response.xpath("//div[contains(@class, 'entry-content')]").extract()))
        blog['tags'] = tags_to_json(list(data['tags'].keys())) if data['tags'] else None
        yield blog

        #Stats
        stat = Stats()
        stat['domain'] = self.domain
        stat['url'] = response.url
        stat['views'] = None
        stat['likes'] = data['like_count']
        stat['comments'] = data['comment_count']
        yield stat

        #Comments
        pids__ = [comment.strip().replace(' ','').split('-')[1] for comment in response.css("li").xpath("@id").extract()]
        req = build_batch(pids__, 70000375)
        res = make_api_request(req)
        if res:
            for res_url in res: 
                res_values  = res[res_url] 
                #-Parsing comments
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] =  f"bc_comment_{res_values['ID']}"
                usr_name = res_values['author']['name'].lower() if  res_values['author']['name'] else None
                parsed_comment['username'] = usr_name
                parsed_comment['user_id'] = get_user_id(self.comment_users, usr_name)
                parsed_comment['comment'] = res_values['raw_content']
                parsed_comment['comment_original'] = res_values['content']
                parsed_comment['links'] = get_links(res_values['content'])
                stats_links = res_values['meta']['links']
                parsed_comment['upvotes'] = parse_comments(stats_links['likes'])
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = res_values['date']
                #-Getting replies
                replies = get_wordpress_replies(res, res_values['ID'], 70000375)
                parsed_comment['reply_count'] = replies[0]
                parsed_comment['reply_to'] = replies[1]
                yield parsed_comment


def make_api_request(endpoint):
    r = requests.get(url=endpoint, params={})
    if r.status_code == 200:
        d = r.json()
        return d

def get_user_id(user_dict, user):
    func = lambda x:int(x.split('_')[2]) if x else 0
    values = list(map(func, user_dict.values()))
    count = 0

    if user in user_dict:
        if not user:
            return None
            
        for key in user_dict:
            user_id = func(user_dict[key])
            if user_id == 0:
                count+=1
                user_dict[key] = f"bc_user_{count}"

        usr_id = user_dict[user]
        return usr_id
    else:
        if len(values) == 0:
            values = [0]
        values.sort()
        val = values[-1]
        usr_id = val + 1
        user_dict[user] = f"bc_user_{usr_id}"
        return f"bc_user_{usr_id}"

def get_wordpress_replies(comments_response, comment_id, siteid):
    key = f"/sites/{siteid}/comments/{comment_id}"
    parent = comments_response[key]['parent']

    # If main comment, parent value is False
    if not parent:
        reply_count = 0
        for key in comments_response:
            values = comments_response[key]
            parent_value = values['parent']
            if parent_value:
                if values['parent']['ID'] == comment_id:
                    reply_count += 1

        return reply_count, None
    else:
        reply_comment = comments_response[key]['parent']['ID']
        reply_comment = f"bc_comment_{reply_comment}" if reply_comment else None
        return None, reply_comment

# def get_wordpress_replies(comments_response, comment_id, siteid):
#     key = f"/sites/{siteid}/comments/{comment_id}"
#     parent = comments_response[key]['parent']
#     # If main comment, parent value is False
#     reply_count = 0
#     for key in comments_response:
#         values = comments_response[key]
#         parent_value = values['parent']
#         if parent_value:
#             if values['parent']['ID'] == comment_id:
#                 reply_count += 1
#         return reply_count, None
#     if type(parent) == dict:
#         reply_comment = comments_response[key]['parent']['ID']
#         if reply_count:
#             print("Nested replies!!")
#         return reply_count, reply_comment

def build_batch(pids, siteid):
    api_url = 'https://public-api.wordpress.com/rest/v1/batch?'
    for pid in pids:
        if pid.isdigit():
            appendee = f'&urls[]=/sites/{str(siteid)}/comments/{str(pid)}'
            api_url += appendee
    return api_url

def parse_comments(url_):
    result_data = make_api_request(url_)
    found_result = result_data['found']
    if found_result:
        return found_result
    else:
        return None
        
def parse_author(data, response):
    #Aurthor name from API
    if 'author' in data and 'name' in data['author']:
        if data['author']['name'] != 'The Buffalo Chronicle':
            return data['author']['name']
    #Possible author locaitons
    author_locs = [response.xpath("//div[contains(@class, 'entry-content')]/p[1]//text()").get(),  
            response.xpath('//*[contains(@id, "post-")]/div/p[1]/a//text()').get(), 
            response.xpath("//div[contains(@class, 'entry-content')]/p[2]//text()").extract_first()]
    
    #-Cleaning
    author_locs = [x.lower() for x in author_locs if x]
    if any([x for x in author_locs if x=='by ']):
        #Author name on second loc
        author = author_locs[1]
    elif any([x for x in author_locs if x.startswith('by') and len(x) < 50]):
        #Looking for x that start with by, but not sentance len
        author = [x for x in author_locs if x.startswith('by') and len(x) < 50][0]
    else: 
        author = None

    #Cleaning author string
    if author:
        author = author.replace("by","").replace(':','').strip().title()
        if author.endswith(','): author = author[:-1]
        if author: return author
 
def get_comments_data(comment_id):
    API_ENDPOINT = "https://public-api.wordpress.com/rest/v1/sites/70000375/comments/" + str(comment_id)
    d = make_api_request(API_ENDPOINT)
    return d

def get_stats_data(post_id):
    API_ENDPOINT = "https://public-api.wordpress.com/rest/v1/sites/70000375/posts/" + str(post_id)
    d = make_api_request(API_ENDPOINT)
    return d