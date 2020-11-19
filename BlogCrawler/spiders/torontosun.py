# -*- coding: utf-8 -*-
import requests
import urllib
import scrapy
import json
import re
from scrapy.http import HtmlResponse
import time


from BlogCrawler.comments_api import get_torontosun_comments 
from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json, parse_datetime, author_title, get_domain

class TorontosunSpider(scrapy.Spider):
    name = 'torontosun'
    allowed_domains = ['torontosun.com', 'vancouversun.com']
    domain = 'torontosun.com'
    start_urls = ['https://torontosun.com/category/news/local-news/','https://torontosun.com/category/news/provincial/','https://torontosun.com/category/news/national/',
        'https://torontosun.com/category/news/world/','https://torontosun.com/category/news/crime/','https://torontosun.com/category/news/weird/','https://torontosun.com/category/business/',
        'https://torontosun.com/category/technology/','https://torontosun.com/category/opinion/editorials/','https://torontosun.com/category/opinion/columnists/',
        'https://torontosun.com/category/opinion/letters/','https://torontosun.com/category/health/','https://torontosun.com/category/travel/']
   
    def parse(self, response):
        # Getting generated key
        key = response.xpath('//div//@data-list-id').extract_first()

        # Getting arguments from url
        args = [x for x in str(response.url).split('/') if x]
        request_type = args[2] if args else None
        request_name = args[-1] if args else None

        start = 0
        size = 25
        # while start <= 25:
        while True:
            url_format = f"https://torontosun.com/api-root/lists/{key}/expanded/?format=json&name={request_name}&from={start}&type={request_type}&size={size}&load_origin_urls=false&template_name=feed-card-list"
            resp = requests.get(url_format)
            if resp.status_code != 200: 
                break
            resp = resp.json()
            if not resp['errors'] and 'items' in resp and resp['items']:
                # for url in [x['get_amp_long_url'].split('/amp/')[0] for x in resp['items']]:
                # for url in [x['get_amp_long_url'] for x in resp['items']]:
                for url in [x['origin_url'] for x in resp['items']]:
                    # if url == '/news/crime/homeless-victoria-man-terrorized-common-law-partner-daily-for-six-months':
                    #     print('here')
                    if 'torontosun.com' not in url and 'vancouversun.com' not in url:
                        print('here')

                    if url and not any([x for x in ["/sunshine-girls/", "/gallery/"] if x in url]): 
                        # yield scrapy.Request("http://torontosun.com"+url, self.parse_blog)
                        yield scrapy.Request(url, self.parse_blog)
                start+=size
            else: 
                break

   
    def parse_blog(self, response):
        # Posts
        script =  response.xpath("//script[contains(., 'identity')]/text()").extract_first()
        try:
            data = json.loads(script)
        except Exception as e:
            print(str(e) + f"\n{str(response.url)}")
            data = {}
        
        if data:
            blog = Posts()
            blog['domain'] = get_domain(response.url)
            blog['url'] = response.url
            blog['title'] = response.css('.article-title::text').extract_first()      
            author, date = parse_authors_date(data) if data else None
            blog['author'] = author.replace("&nbsp;", "").strip() if author else None
            blog['published_date'] = date if date else None
            blog['tags'] = tags_to_json(data['page']['tags']) if 'page' in data else None
            blog['content'] = get_content(response)
            blog['content_html'] = " ".join(response.xpath('//*[@class="article-content"]').extract())
            blog['links'] = get_links(" ".join(response.xpath('//*[@class="article-content"]').extract()))
            yield blog
        else:
            print('here')
            pass

        # Comments
        article_id = data['page']['articleId'] if 'page' in data else None
        comments = get_torontosun_comments(article_id)
        if comments: #Catches no comments
            for c in comments:
                if 'content' in c and c['content']: #Skipping empty comments 
                    parsed_comment = Comments()
                    parsed_comment['domain'] = self.domain
                    parsed_comment['url'] = response.url
                    parsed_comment['comment_id'] = c['content_uuid']
                    parsed_comment['username'] = None #Could not find API to get this
                    parsed_comment['user_id'] = c['actor_uuid']
                    parsed_comment['comment'] = c['content'] if 'content' in c else None
                    parsed_comment['comment_original'] = None
                    parsed_comment['links'] = get_links(c['content']) if 'content' in c else None
                    parsed_comment['upvotes'] = c['total_likes']
                    parsed_comment['downvotes'] = c['total_dislikes']
                    parsed_comment['published_date'] = parse_datetime(time.strftime('%m/%d/%Y %H:%M:%S',  time.gmtime(c['date_created']/1000.)))
                    if c['total_replies'] > 0:
                        parsed_comment['reply_count'] = c['total_replies']
                    else:
                        parsed_comment['reply_count'] = 0
                    if c['content_container_uuid'] != c['thread_uuid'] and c['content_container_uuid'] != c['parent_uuid']:
                        parsed_comment['reply_to'] = c['thread_uuid']
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

def parse_authors_date(data):
    if 'page' in data:
        if 'authors' in data['page'] and 'date' in data['page']:
            if data['page']['authors'] and data['page']['date']:
                try:
                    date = parse_datetime(data['page']['date']['pub'])
                except:
                    date = None

                author = ' and '.join(data['page']['authors'])
                if 'by' in author.lower() or 'special to' in author.lower():
                    author = ''.join(author.lower().split("special to")).replace('by','').strip().title()
                return author_title(author), date
    else:
        if 'author' in data and 'datePublished' in data:
            try:
                date = parse_datetime(data['datePublished'])
            except:
                date = None

            author = data['author']['name']
            if 'by' in author.lower() or 'special to' in author.lower():
                author = ''.join(author.lower().split("special to")).replace('by','').strip().title()

            return author_title(author), date

def get_content(response):
    p_content = [" ".join(response.xpath('//*[@class="article-content"]//p//text()').extract()),
        " ".join(response.xpath('//*[@class="article-content"]//div[@dir="auto"]//text()').extract()),
        " ".join(response.xpath('//*[@class="article-content"]//div/text()').extract()),
        " ".join(response.xpath('//*[@class="article-content"]/blockquote/text()').extract()),
        " ".join(response.xpath('//*[@class="article-content"]//div[@class="wide-content-host"]//text()').extract())]
    for content in sorted(p_content, key=len, reverse=True):
        content = content.replace( "We apologize, but this video has failed to load. Try refreshing your browser, or .", "")
        content = content.replace(u'\xa0', '').replace("  ", " ").strip()
        if content.strip() and 'but this video has failed to load' not in content:
            return content
    raise Exception(f"Found no content for: {response.url}")