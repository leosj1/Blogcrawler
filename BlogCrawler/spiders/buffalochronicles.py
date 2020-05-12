# -*- coding: utf-8 -*-
import scrapy
from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json
from dateutil.parser import parse
import json
import requests

class BuffalochroniclesSpider(scrapy.Spider):
    name = 'buffalochronicles'
    allowed_domains = ['buffalochronicle.com']
    domain = 'buffalochronicle.com'
    start_urls = ['https://buffalochronicle.com/']

    def parse(self, response):
        #Getting links to catagories
        if response.url == 'https://buffalochronicle.com/':
            for link in response.css("#menu-subjects a").xpath("@href").extract():
                yield scrapy.Request(link, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
        #Getting post urls
        all_div = response.css('.mh-posts-grid-col')
        for data in all_div:
            urls = data.css(".mh-posts-grid-title a").xpath("@href").extract()
            for url in urls:
                yield scrapy.Request(url, self.parse_blog, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
                # response.css('.mh-posts-grid-col')

        next_page = response.xpath("//a[contains(@class, 'next page-numbers')]/@href").extract_first()
        if next_page: yield scrapy.Request(next_page, self.parse, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})

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
        for x in response.css("ol.commentlist"):
            for comment in x.css("li").xpath("@id").extract():
                commentid = comment.strip().replace(' ','').split('-')[1]
                comment_data = get_comments_data(commentid)

                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] = self.name + "_" + commentid
                parsed_comment['username'] = comment_data['author']['name']
                parsed_comment['user_id'] = comment_data['author']['ID']
                parsed_comment['comment'] = comment_data['raw_content']
                parsed_comment['comment_original'] = comment_data['content']
                parsed_comment['links'] = get_links(comment_data['content'])
                stats_links = comment_data['meta']['links']
                parsed_comment['upvotes'] = parse_comments(stats_links['likes'])
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = comment_data['date']
                parsed_comment['reply_count'] = parse_comments(stats_links['replies'])
                parsed_comment['reply_to'] = None
                yield parsed_comment

                
def parse_comments(url_):
    result = requests.get(url = url_, params = {}, headers = {"Accept":"application/json","User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}) 
    if result.status_code == 200:
        result_data = result.json()
        found_result = result_data['found']
        if found_result:
            return found_result
        else:
            return None
    else:
        return None


def parse_author(data, response):
    author_api = data['author']['nice_name'] if len(data['author']) > 0 else None

    author_list = response.xpath("//div[contains(@class, 'entry-content')]/p[1]//text()").extract() + response.xpath('//*[contains(@id, "post-")]/div/p[1]/a//text()').extract()
    res = []
    for i in author_list:
        if i not in res:
            res.append(i)
            
    author = ''.join(res).strip()
    author = author.replace('BY ', '').replace('By ', '').replace('By: ', '')  if str(author).startswith('BY') or str(author).startswith('By') or str(author).startswith('By:') else author_api
 
    if author:
        if ',' in author:
            author = author.split(',')[0]
        if len(author) < 100:
            return str(author).strip().lower().rstrip(',')
        else:
            author = response.xpath("//div[contains(@class, 'entry-content')]/p[2]//text()").extract_first().strip()
            author = author.replace('BY ', '').replace('By ', '').replace('By: ', '')  if str(author).startswith('BY') or str(author).startswith('By') or str(author).startswith('By:') else ""
            
            if author:
                if ',' in author:
                    author = author.split(',')[0]
                if len(author) < 100:
                    return str(author).strip().lower().rstrip(',') 
                else:
                    return None
    else:
        author = response.xpath("//div[contains(@class, 'entry-content')]/p[2]//text()").extract_first().strip()
        author = author.replace('BY ', '').replace('By ', '').replace('By: ', '')  if str(author).startswith('BY') or str(author).startswith('By') or str(author).startswith('By:') else ""
        
        if author:
            if ',' in author:
                author = author.split(',')[0]
            if len(author) < 100:
                return str(author).strip().lower().rstrip(',') 
            else:
                return None

def get_comments_data(comment_id):
    API_ENDPOINT = "https://public-api.wordpress.com/rest/v1/sites/70000375/comments/" + str(comment_id)
    r = requests.get(url = API_ENDPOINT, params = {}, headers = {"Accept":"application/json","User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}) 
    if r.status_code == 200:
        d = r.json() 
    return d

def get_stats_data(post_id):
    API_ENDPOINT = "https://public-api.wordpress.com/rest/v1/sites/70000375/posts/" + str(post_id)
    r = requests.get(url = API_ENDPOINT, params = {}, headers = {"Accept":"application/json","User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}) 
    if r.status_code == 200:
        d = r.json() 
    return d