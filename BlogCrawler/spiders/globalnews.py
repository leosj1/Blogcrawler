# -*- coding: utf-8 -*-
import scrapy
import re
import json

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, get_start_urls, get_matching_links, tags_to_json, parse_datetime, author_title
from BlogCrawler.comments_api import facebook_comments


class GlobalnewsSpider(scrapy.Spider):
    name = 'globalnews'
    domain = 'globalnews.ca'
    current_page = 1
    allowed_domains = ['globalnews.ca']
    start_urls = ['https://globalnews.ca/']
    user_agent = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


    def parse(self, response):
        # Getting post links
        for url in response.css('.c-posts__details').xpath('@href').extract():
            if 'https://globalnews.ca/video/' not in url and 'https://globalnews.ca/ice-caves/' not in url:#Ignoring video and ice-caves pages
                yield scrapy.Request(url, self.parse_blog, meta={'dont_redirect': True})

        for url in response.css('.c-posts__item').xpath('a/@href').extract():
            if url != '#' and 'https://globalnews.ca/video/' not in url and 'https://globalnews.ca/ice-caves/' not in url: #Ignoring video and ice-caves pages
                yield scrapy.Request(url, self.parse_blog, meta={'dont_redirect': True})

        # Getting next page
        post_id = response.xpath('//li//@data-post-id').extract()
        if post_id:
            next_page = f"https://globalnews.ca/gnca-ajax-redesign/latest-stories/%7B%22trackRegion%22:%22home-latestStories%22,%22version%22:%222%22,%22adEnabled%22:%221%22,%22adPosition%22:%7B%22mobile%22:9,%22desktop%22:9%7D,%22adOffset%22:%7B%22mobile%22:8,%22desktop%22:8%7D,%22adFrequency%22:%7B%22mobile%22:6,%22desktop%22:6%7D,%22number%22:%2224%22,%22action%22:%22latest-stories%22,%22loadMoreTarget%22:%22home-latestStories%22,%22queryType%22:%22latest-posts%22,%22queryValue%22:%22gnca-national%22,%22region%22:%22gnca-national%22,%22loadMoreButton%22:%22%22,%22lastPostId%22:%22{post_id[-1]}%22,%22page%22:%22{str(self.current_page)}%22%7D"
            self.current_page += 1
            yield scrapy.Request(next_page, self.parse)
            

    def parse_blog(self, response):
        # Posts
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = parse_title(response) 

        date, author = parse_author_date(response)    
        author = parse_author(response)
        blog['author'] = str(author)[0:99] if author else None
        blog['published_date'] = parse_datetime(date) if date else None

        content, content_html = parse_content(response)
        if content_html:
            blog['content'] = content
            blog['content_html'] = content_html
            blog['links'] = get_links(content_html)
            tags = response.xpath('//*[@id="article-tags"]/div//text()').extract()
            blog['tags'] = tags_to_json(list(filter(lambda x: '\n' not in x and '\t' not in x, tags))) if tags else None
            yield blog

            # Comments
            comment_data = facebook_comments(response.url, 318812448281278)
            comments = comment_data['comments']
            authors = comment_data['authors']
            reply_dic = comment_data['reply_dic']
            if comments: #Catches no comments
                for c in comments: 
                    parsed_comment = Comments()
                    parsed_comment['domain'] = self.domain
                    parsed_comment['url'] = response.url
                    parsed_comment['comment_id'] = c['id']
                    parsed_comment['username'] = [x['name'] for x in authors if c['authorID'] == x['id']][0]
                    parsed_comment['user_id'] = c['authorID']
                    parsed_comment['comment'] = c['body']['text']
                    parsed_comment['comment_original'] = None
                    parsed_comment['links'] = get_links(c['body']['text'])
                    parsed_comment['upvotes'] = c['likeCount']
                    parsed_comment['downvotes'] = None
                    parsed_comment['published_date'] = parse_datetime(c['timestamp']['text'])
                    if 'public_replies' in c:
                        parsed_comment['reply_count'] = len([x for x in comments if 'targetID' in x and x['targetID'] == c['id']])
                    else:
                        parsed_comment['reply_count'] = 0
                    if c['id'] in reply_dic:
                        parsed_comment['reply_to'] = reply_dic[c['id']]
                    else:
                        parsed_comment['reply_to'] = None
                    yield parsed_comment

            # #Stats
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


def parse_author_date(response):
    author = ''
    date = ''

    script_pub = response.xpath("//script[contains(., 'datePublished')]/text()").extract_first()
    if script_pub:
        data_script = script_pub.replace('\n', '').replace('\t', '')
        date_data = str(re.search('\"datePublished\"(.*?)\",', data_script).group(0))
        author_data = str(re.search('\"author\"(.*)},', data_script).group(0))
        try:
            if date_data:
                date_data = '{' + date_data[:-1] + '}'
                script_data = json.loads(date_data)
                date = script_data['datePublished']
            if author_data:
                author_data = author_data.replace('\\',' ').replace('\'',' ')
                script_data = json.loads('{' + author_data[:-1] + '}')       
                author = script_data['author']['name']
        except Exception as e:
            print('error here1 --',e,'----',response.url)
            # pass

    script_upl = response.xpath("//script[contains(., 'uploadDate')]/text()").extract_first()
    if script_upl:
        script_upl = script_upl.replace('\n', '').replace('\t', '').replace('\'',' ').replace('\\',' ')
        try:
            script_data = json.loads(script_upl)
            date = script_data['uploadDate']
            author = script_data['author']['name']
        except Exception as e:
            print('error here2 --',e,'----',response.url)
            # pass

    result_author = author if author else None
    result_date = date if date else None

    return result_date, result_author

def parse_author(response):
    result = response.xpath("//div[contains(@class, 'c-byline__attribution')]//text()").extract()
    if result:
        staff = ' '.join(result).replace('\n','').replace('\t', '').replace('\r','')
        if ' staff' in staff.lower():
            return author_title(staff.replace('By','').strip() if staff.startswith('By') else staff)

        result_ = ''.join(result[:-2]).replace('\n','').replace('\t','').strip()
        result_ = result_.replace('By','').strip() if result_.startswith('By') else result
        if result_:
            result = result_
            result = author_title(result)
            return result
        else:
            return result[1]
    
    else:
        result = response.xpath("//span[contains(@class, 'story-author')]//text()").extract()
        if result:
            result = ''.join(result[:-1]).replace('\n','').replace('\t','').strip()
            result = result.replace('By','').strip() if result.startswith('By') else result
            result = author_title(result)
            return result
        

def parse_title(response):
    result = response.xpath("//h1[contains(@class, 'l-article__title')]//text()").extract_first()
    if result:
        return result
    else:
        result = response.xpath("//h1[contains(@class, 'lf-title')]//text()").extract_first()
        if result:
            return result
    
def parse_content(response):
    result = response.xpath("//div[contains(@class, 'l-main__story')]/article//*[not(self::script)]/text()[not(ancestor::*[@class='l-article__copyright'])][not(ancestor::*[@class=' is-hidden'])][not(ancestor::section)]").extract()
    result_html = response.xpath("//div[contains(@class, 'l-main__story')]").extract()

    def replace_text(text):
        return text.replace('comments Leave a comment facebook Share this item on Facebook whatsapp Share this item via WhatsApp twitter Share this item on Twitter email Send this page to someone via email more Share this item more Share this item Smaller font Descrease article font size -A Larger font Increase article font size A+ Share this item on Facebook facebook Share this item via WhatsApp whatsapp Share this item on Twitter twitter Send this page to someone via email email Share this item on Pinterest pinterest Share this item on LinkedIn linkedin Share this item on Reddit reddit Copy article link Copy link','').replace('facebook Share this item on Facebook whatsapp Share this item via WhatsApp twitter Share this item on Twitter email Send this page to someone via email copy Copy article link more Share this item more Share this item Smaller font Descrease article font size -A Larger font Increase article font size A+ Share this item on Facebook facebook Share this item via WhatsApp whatsapp Share this item on Twitter twitter Send this page to someone via email email Share this item on Pinterest pinterest Share this item on LinkedIn linkedin Share this item on Reddit reddit Copy article link Copy link','')

    def remove_read_more(text_array):
        length_of_string = len(text_array)
        for i, x in enumerate(text_array):
            if 'read more:' in x.lower():
                if i == length_of_string - 1:
                    del text_array[i]
                else:
                    del text_array[i]
                    del text_array[i]
        return text_array

    if result:
        result = remove_read_more(result)
        result = str(re.sub(' +', ' '," ".join(result).strip().replace('\n','').replace('\t', '').replace('\r', '')))
        result = replace_text(result)
        result_html = " ".join(result_html)
        return result, result_html
    else:
        result = response.xpath("//section[contains(@class, 'story-txt')]/span//p//text()").extract()
        result_html = response.xpath("//section[contains(@class, 'story-txt')]").extract()
        if result:
            result = remove_read_more(result)
            result = str(re.sub(' +', ' '," ".join(result).strip().replace('\n','').replace('\t', '').replace('\r', '')))
            result = replace_text(result)   
            result_html = "".join(result_html)
            return result, result_html
        else:
            return None, None
    





    
    
