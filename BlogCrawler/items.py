# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import scrapy

class Posts(scrapy.Item):
    domain = scrapy.Field()
    url = scrapy.Field()
    author = scrapy.Field()
    title = scrapy.Field()
    published_date = scrapy.Field()
    content = scrapy.Field()
    content_html = scrapy.Field()
    links = scrapy.Field()
    tags = scrapy.Field()

    #modifying the print output
    def __repr__(self):
        """only print out attr1 after exiting the Pipeline"""
        return repr({"Blog URL": self._values['url']})
  
class Stats(scrapy.Item):
    domain = scrapy.Field()
    url = scrapy.Field()
    views = scrapy.Field()
    likes = scrapy.Field()
    daily_likes = scrapy.Field()
    daily_views = scrapy.Field()
    comments = scrapy.Field()
    daily_comments = scrapy.Field()
    
    #No print output
    def __str__(self):
        return ""

class Comments(scrapy.Item):
    domain = scrapy.Field()
    url = scrapy.Field()
    comment_id = scrapy.Field()
    username = scrapy.Field()
    user_id = scrapy.Field()
    comment = scrapy.Field()
    comment_original = scrapy.Field()
    links = scrapy.Field()
    upvotes = scrapy.Field()
    downvotes = scrapy.Field()
    published_date = scrapy.Field()
    reply_count = scrapy.Field()
    reply_to = scrapy.Field()

    #No print output
    def __str__(self):
        return ""

