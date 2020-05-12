# -*- coding: utf-8 -*-
import re
import scrapy
from dateutil.parser import parse

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links


class AccidentaldeliberationsSpider(scrapy.Spider):
    name = 'accidentaldeliberations'
    domain = "accidentaldeliberations.blogspot.com"
    allowed_domains = ['accidentaldeliberations.blogspot.com']
    db_urls = get_start_urls(domain)
    start_urls = ['http://accidentaldeliberations.blogspot.com//'] + db_urls

    def parse(self, response):
        #Running db urls
        if response.url in self.db_urls:
            yield scrapy.Request(response.url, self.parse_blog, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
        else: #Scrapying from site
            links = response.xpath("//h3[contains(@class, 'post-title entry-title')]/a/@href").getall()
            for link in links:
                yield scrapy.Request(link, self.parse_blog, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
            #Getting blog archive links
            archive_links = response.xpath("//a[contains(@class, 'post-count-link')]/@href").getall()
            for archive in archive_links:
                yield scrapy.Request(archive, self.parse, headers = {"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})


    def parse_blog(self, response):
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath('//*[@id="Blog1"]/div[1]/div/div/div/div[1]/h3/text()').get().strip()
        blog['author'] = response.xpath('//*[@id="Blog1"]/div[1]/div/div/div/div[1]/div[3]/div[1]/span[1]/span/text()').get()
        blog['published_date']= parse(response.xpath('//*[@id="Blog1"]/div[1]/div/div/div/div[1]/div[3]/div[1]/span[2]/a/abbr/@title').get())
        blog['content'] = " ".join(response.xpath("//div[contains(@class, 'post-body entry-content')]//text()").getall()).replace('\n', '')
        blog['content_html'] = response.xpath("//div[contains(@class, 'post-body entry-content')]").get()
        blog['links'] = get_links(response.xpath("//div[contains(@class, 'post-body entry-content')]").get())
        blog['tags'] = None
        yield blog

        #Stats
        stat = Stats()  
        stat['domain'] = self.domain
        stat['url'] = response.url
        stat['views'] = None
        stat['likes'] = None
        comment_num = response.xpath('//div[@id="comments"]/h4/text()').get()
        if "No" not in comment_num:
            stat['comments'] = int(re.search(r'\d+', comment_num).group())
        else: 
            stat['comments'] = None
            
        yield stat

        #Comments
        if "No" not in comment_num:
            for c in response.xpath('//*[@id="top-ra"]//li'):
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = response.url
                parsed_comment['comment_id'] = c.xpath('//li[contains(@class, "comment")]/@id').get()
                if c.xpath('//li[contains(@class, "comment")]/div[2]/div/cite/a/text()').get() is not None: 
                    parsed_comment['username'] = c.xpath('//li[contains(@class, "comment")]/div[2]/div/cite/a/text()').get()
                    parsed_comment['user_id'] = c.xpath('//li[contains(@class, "comment")]/div[2]/div/cite/a/@href').get().replace('https://www.blogger.com/profile/', "")
                else: 
                    parsed_comment['username'] = c.xpath('//li[contains(@class, "comment")]/div[2]/div/cite/text()').get() 
                    parsed_comment['user_id'] = None                
                parsed_comment['comment'] = " ".join(c.xpath('//li[contains(@class, "comment")]/div[2]/p//text()').getall())
                parsed_comment['comment_original'] = c.xpath('//li[contains(@class, "comment")]/div[2]/p').get()
                parsed_comment['links'] = get_links(c.xpath('//li[contains(@class, "comment")]/div[2]/p').get())
                parsed_comment['upvotes'] = None
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = None
                parsed_comment['reply_count'] = None 
                parsed_comment['reply_to'] = None
                yield parsed_comment

        #Getting other blog posts
        # next_link = response.xpath("//a[contains(@class, 'blog-pager-older-link')]/@href").get()
        # if next_link: yield scrapy.Request(next_link, self.parse_blog)
