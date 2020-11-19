# -*- coding: utf-8 -*-
import scrapy
import re

from BlogCrawler.items import Posts, Stats
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json, parse_datetime

class TncSpider(scrapy.Spider):
    name = 'tnc'
    domain = 'tnc.news'
    current_page = 1
    start_urls =   ['https://tnc.news/breaking/',
                    'https://tnc.news/category/covid19/',
                    'https://tnc.news/category/immigration/',
                    'https://tnc.news/category/culture/',
                    'https://tnc.news/category/free-speech/',
                    'https://tnc.news/category/economy/',
                    'https://tnc.news/videos/',
                    'https://tnc.news/podcasts/']
    allowed_domains = ['tnc.news']
    user_agent = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    download_delay = 4

    def parse(self, response):
        # Getting post_urls
        for url in response.css('.entry-title a').xpath('@href').extract():
            yield scrapy.Request(url, self.parse_blog)

        # Getting next page
        next_page = response.xpath('//*[@id="td-outer-wrap"]/div[4]/div/div/div/div/div[5]//@href').extract()
        if next_page: yield scrapy.Request(next_page[-1], self.parse)

    def parse_blog(self, response):
        # Post
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.css('.entry-title::text').extract_first()   
        blog['author'] = response.xpath('//*[contains(@id,"post-")]/div[1]/div/div/header/div/div/a//text()').extract_first()
        date = response.css('.updated::text').extract_first()
        blog['published_date'] = parse_datetime(date) if date else None
        #-Cleaning Post
        posts = "".join(response.xpath("//div[contains(@class, 'td-post-content')]//text()").extract()).strip().replace('\n', ' ').replace('\t', ' ')
        posts = str(re.sub(' +', ' ',posts))
        blog['content'] = posts.replace('Facebook Twitter reddit LinkedIn','').replace('We’re asking readers, like you, to make a contribution in support of True North’s fact-based, independent journalism.\r Unlike the mainstream media, True North isn’t getting a government bailout. Instead, we depend on the generosity of Canadians like you.\r How can a media outlet be trusted to remain neutral and fair if they’re beneficiaries of a government handout? We don’t think they can.\r This is why independent media in Canada is more important than ever. If you’re able, please make a tax-deductible donation to True North today. Thank you so much.','').replace('\r', ' ')
        blog['content_html'] = "".join(response.xpath("//div[contains(@class, 'td-post-content')]").extract())
        blog['links'] = get_links("".join(response.xpath("//div[contains(@class, 'td-post-content')]").extract()))
        blog['tags'] = None
        yield blog

    
