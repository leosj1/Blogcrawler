# -*- coding: utf-8 -*-
import scrapy
from dateutil.parser import parse

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links


class TherussophileSpider(scrapy.Spider):
    name = 'therussophile'
    domain = 'therussophile.org'
    address = "https://therussophile.org/"
    allowed_domains = ['therussophile.org']
    start_urls = ['https://therussophile.org/']
    user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"

    def parse(self, response):
        for url in response.xpath('//h2[contains(@class, "post-title entry-title")]/a/@href').getall():
            yield scrapy.Request(url, self.parse_blog)


    def parse_blog(self, response):
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath('//*[contains(@class, "post-title entry-title")]/a/text()').get()
        blog['author'] = None
        blog['published_date']= None
        blog['content'] = "".join(response.xpath('//*[contains(@class, "entry-content")]//text()').getall()).replace("\n", " ")
        blog['content_html'] = response.xpath('//*[contains(@class, "entry-content")]').get()
        blog['links'] = get_links(response.xpath('//*[contains(@class, "entry-content")]').get())
        yield blog