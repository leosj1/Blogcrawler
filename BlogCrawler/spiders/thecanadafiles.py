# -*- coding: utf-8 -*-
import scrapy
from dateutil.parser import parse

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, tags_to_json, get_start_urls


class ThecanadafilesSpider(scrapy.Spider):
    name = 'thecanadafiles'
    domain = 'thecanadafiles.com'
    allowed_domains = ['thecanadafiles.com']
    start_urls = ["https://www.thecanadafiles.com/articles?category=Africa", "https://www.thecanadafiles.com/articles?category=Asia", "https://www.thecanadafiles.com/articles?category=Europe", "https://www.thecanadafiles.com/articles?category=North%20%26%20Central%20America", "https://www.thecanadafiles.com/articles?category=South%20America", "https://www.thecanadafiles.com/articles?category=The%20Middle%20East", "https://www.thecanadafiles.com/articles?category=Toronto", "https://www.thecanadafiles.com/articles?category=Queen%27s%20Park", "https://www.thecanadafiles.com/articles?category=Indigenous%20Nations", "https://www.thecanadafiles.com/articles?category=Canada", "https://www.thecanadafiles.com/articles?category=Federal%20Politics", "https://www.thecanadafiles.com/articles?category=Adam%20Riggio", "https://www.thecanadafiles.com/articles?category=Other%20Contributors", "https://www.thecanadafiles.com/articles?category=Dustin%20Olson", "https://www.thecanadafiles.com/articles?category=Alienor%20Rougeot", "https://www.thecanadafiles.com/articles?category=John%20Clarke", "https://www.thecanadafiles.com/articles?category=Mohammed%20Shafi", "https://www.thecanadafiles.com/articles?category=Tyler%20Shipley", "https://www.thecanadafiles.com/articles?category=Yves%20Engler"]

    def parse(self, response):
        #blogs from page
        for blog in response.xpath("//a[contains(@class, 'BlogList-item-title')]/@href").getall():
            yield scrapy.Request("https://www.thecanadafiles.com" + blog, self.parse_blog)
        next_page = response.xpath("//a[contains(@class, 'BlogList-pagination-link')]/@href").get()
        if next_page:
            n_page_text = response.xpath("//*[contains(@class, 'BlogList-pagination-link-label')]/text()").get()
            if n_page_text and n_page_text == "Older":
                yield scrapy.Request("https://www.thecanadafiles.com" + next_page, self.parse)
        
    def parse_blog(self, response):
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath("//*[contains(@class, 'BlogItem-title')]/text()").get()
        blog['author'] = response.xpath("//*[contains(@class, 'Blog-meta-item Blog-meta-item--author')]/text()").get()
        blog['published_date']= parse(response.xpath("//*[contains(@class, 'Blog-meta-item Blog-meta-item--date')]/text()").get())
        content = " ".join(response.xpath('//*[contains(@class, "col sqs-col-12 span-12")]//p//text()').getall()).replace('More Articles Subscribe to receive exclusive news and content from The Canada Files! Enter your email address powered by TinyLetter', '').replace('Subscribe to receive exclusive news and content from The Canada Files! Enter your email address powered by TinyLetter', '')
        blog['content'] = ' '.join(content.split())
        blog['content_html'] = response.xpath('//*[contains(@class, "col sqs-col-12 span-12")]').get()
        blog['links'] = get_links(response.xpath('//*[contains(@class, "col sqs-col-12 span-12")]').get())
        blog['tags'] = None
        yield blog