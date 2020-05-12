# -*- coding: utf-8 -*-
import dateutil.parser
import requests
import scrapy

from BlogCrawler.items import Posts, Comments, Stats, get_domain, get_links


class varvaraSpider(scrapy.Spider):
    name = '02varvara'

    allowed_domains = ['wordpress.com']
    start_urls = ['https://02varvara.wordpress.com/']

    def parse(self, response):
        #Posts on page
        posts = response.xpath('//a[@rel="bookmark"]/@href').getall()
        for url in posts: 
            yield scrapy.Request(url, self.parse_post)
        #Next page
        next_page = response.xpath('//*[@id="content"]/a/@href').getall()[-1]
        if next_page:
            yield scrapy.Request(next_page, self.parse)
    
    def parse_post(self, response):
        blog = Posts()
        blog['domain'] = get_domain(response.url)
        blog['url'] = response.url
        blog['title'] = response.xpath('/html/body/div[1]/div[1]/div/h3/text()').get().strip()
        blog['author'] = get_author(blog['domain'])
        blog['published_date']= dateutil.parser.parse(response.xpath('/html/body/div[1]/div[1]/h2/text()').get())
        blog['content'] = "".join(response.xpath('/html/body/div[1]/div[1]/div/div[2]/p/text()').getall())
        blog['content_html'] = "".join(response.xpath('/html/body/div[1]/div[1]/div/div[2]/p').getall())
        # blog['language'] = get_language(blog['content'])
        blog['links'] = get_links(blog['content_html'])
        yield blog

        #Stats requests
        stat = Stats()
        stat['domain'] = get_domain(response.url)
        stat['url'] = response.url
        stat['views'] = None
        #Getting likes
        post_class = response.xpath('/html/body/@class').get()
        post_id = post_class[post_class.find('postid-')+7 : post_class.find('postid-')+12]
        blog_id = response.xpath('//*[@id="subscribe-blog"]/p[4]/input[2]/@value').get()
        likes_response = requests.get(f"https://public-api.wordpress.com/rest/v1/batch?http_envelope=1&urls[]=/me&urls[]=/sites/{blog_id}/posts/{post_id}/likes&urls[]=/sites/{blog_id}/posts/{post_id}/reblogs/mine").json()
        stat['likes'] = likes_response['body'][f'/sites/{blog_id}/posts/{post_id}/likes']['found']
        stat['comments'] = None
        yield stat

        #Comments (Looks like they're turned off)
        if response.xpath('/html/body/div[1]/div[1]/div/div[3]/span/text()').get() !='Comments Off':
            print("comments on??")
        


def get_author(domain):
    return domain.strip('.wordpress.com')