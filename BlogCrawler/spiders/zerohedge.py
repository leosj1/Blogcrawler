# -*- coding: utf-8 -*-
from datetime import datetime
import scrapy
import requests
import json
import dateutil.parser

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_start_urls, get_links

class ZerohedgeSpider(scrapy.Spider):
    name = 'zerohedge'
    domain = 'zerohedge.com'
    allowed_domains = ['zerohedge.com']
    crawled_urls = get_start_urls(domain)
    start_urls = ['https://www.zerohedge.com/', 'https://www.zerohedge.com/commodities', 'https://www.zerohedge.com/crypto',
        'https://www.zerohedge.com/economics', 'https://www.zerohedge.com/energy', 'https://www.zerohedge.com/geopolitical',
        'https://www.zerohedge.com/health-0', 'https://www.zerohedge.com/markets', 'https://www.zerohedge.com/personal-finance',
        'https://www.zerohedge.com/political', 'https://www.zerohedge.com/technology'] + crawled_urls

    def parse(self, response):
        #Crawling blog posts (from db)
        if response.url in self.crawled_urls:
            yield scrapy.Request(response.url, callback=self.parse_blog)
        else:  #Going through the home pages and getting blogposts
            for article in response.css('Article'):
                blogurl = response.urljoin(article.css('a::attr(href)')[0].get())
                yield scrapy.Request(blogurl, callback=self.parse_blog) 

    def parse_blog(self, response):
        #HTML Content
        blog_id = response.xpath('/html/head/link[4]/@href').get().strip('/node/')
        blog = Posts()
        blog['domain'] = self.domain
        blog['url'] = response.url
        blog['title'] = response.xpath('//*[@id="block-zerohedge-page-title"]/h1/span/text()').get()
        blog['author'] = response.xpath('//*[@id="block-zerohedge-content"]/article/footer/div[1]/div/div[1]/span/a/text()').get()
        blog['published_date']= convert_date(response.xpath('//*[@id="block-zerohedge-content"]/article/footer/div[1]/div/div[2]/span/text()').get())
        blog['content'] = " ".join(response.xpath('//*[@id="block-zerohedge-content"]/article/div/div[1]/p//text()').getall())
        blog['content_html'] = "".join(response.xpath('//*[@id="block-zerohedge-content"]/article/div/div[1]/p').getall())
        blog['links'] = get_links(blog['content_html'])
        blog['tags'] = None
        yield blog
        
        #Stats requests
        stat = Stats()
        stat['domain'] = self.domain
        stat['url'] = response.url
        stat['views'] = requests.get('https://www.zerohedge.com/statistics-ajax?entity_ids={}'.format(blog_id)).json()[blog_id]
        stat['likes'] = None
        stat['comments'] = requests.get('https://www.zerohedge.com/coral-talk-comment-counts?nids={}'.format(blog_id)).json()[blog_id]
        yield stat

        #Comments requests
        payload = {"query":"query CoralEmbedStream_Embed($assetId: ID, $assetUrl: String, $commentId: ID!, $hasComment: Boolean!, $excludeIgnored: Boolean, $sortBy: SORT_COMMENTS_BY!, $sortOrder: SORT_ORDER!) {\n  me {\n    id\n    state {\n      status {\n        username {\n          status\n          __typename\n        }\n        banned {\n          status\n          __typename\n        }\n        suspension {\n          until\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  asset(id: $assetId, url: $assetUrl) {\n    ...CoralEmbedStream_Configure_asset\n    ...CoralEmbedStream_Stream_asset\n    ...CoralEmbedStream_AutomaticAssetClosure_asset\n    __typename\n  }\n  ...CoralEmbedStream_Stream_root\n  ...CoralEmbedStream_Configure_root\n}\n\nfragment CoralEmbedStream_Stream_root on RootQuery {\n  me {\n    state {\n      status {\n        username {\n          status\n          __typename\n        }\n        banned {\n          status\n          __typename\n        }\n        suspension {\n          until\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    ignoredUsers {\n      id\n      __typename\n    }\n    role\n    __typename\n  }\n  settings {\n    organizationName\n    __typename\n  }\n  ...TalkSlot_StreamFilter_root\n  ...CoralEmbedStream_Comment_root\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_root on RootQuery {\n  me {\n    ignoredUsers {\n      id\n      __typename\n    }\n    __typename\n  }\n  ...TalkSlot_CommentInfoBar_root\n  ...TalkSlot_CommentAuthorName_root\n  ...TalkEmbedStream_DraftArea_root\n  ...TalkEmbedStream_DraftArea_root\n  __typename\n}\n\nfragment TalkEmbedStream_DraftArea_root on RootQuery {\n  __typename\n}\n\nfragment CoralEmbedStream_Stream_asset on Asset {\n  comment(id: $commentId) @include(if: $hasComment) {\n    ...CoralEmbedStream_Stream_comment\n    parent {\n      ...CoralEmbedStream_Stream_singleComment\n      parent {\n        ...CoralEmbedStream_Stream_singleComment\n        parent {\n          ...CoralEmbedStream_Stream_singleComment\n          parent {\n            ...CoralEmbedStream_Stream_singleComment\n            parent {\n              ...CoralEmbedStream_Stream_singleComment\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  id\n  title\n  url\n  isClosed\n  created_at\n  settings {\n    moderation\n    infoBoxEnable\n    infoBoxContent\n    premodLinksEnable\n    questionBoxEnable\n    questionBoxContent\n    questionBoxIcon\n    closedTimeout\n    closedMessage\n    disableCommenting\n    disableCommentingMessage\n    charCountEnable\n    charCount\n    requireEmailConfirmation\n    __typename\n  }\n  totalCommentCount @skip(if: $hasComment)\n  comments(query: {limit: 50000, excludeIgnored: $excludeIgnored, sortOrder: $sortOrder, sortBy: $sortBy}) @skip(if: $hasComment) {\n    nodes {\n      ...CoralEmbedStream_Stream_comment\n      __typename\n    }\n    hasNextPage\n    startCursor\n    endCursor\n    __typename\n  }\n  ...TalkSlot_StreamFilter_asset\n  ...CoralEmbedStream_Comment_asset\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_asset on Asset {\n  __typename\n  id\n  ...TalkSlot_CommentInfoBar_asset\n  ...TalkSlot_CommentReactions_asset\n  ...TalkSlot_CommentAuthorName_asset\n}\n\nfragment CoralEmbedStream_Stream_comment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  ...CoralEmbedStream_Comment_comment\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_comment on Comment {\n  ...CoralEmbedStream_Comment_SingleComment\n  replies(query: {limit : 50000, excludeIgnored: $excludeIgnored}) {\n    nodes {\n      ...CoralEmbedStream_Comment_SingleComment\n      replies(query: {limit : 50000, excludeIgnored: $excludeIgnored}) {\n        nodes {\n          ...CoralEmbedStream_Comment_SingleComment\n          replies(query: {limit : 50000, excludeIgnored: $excludeIgnored}) {\n            nodes {\n              ...CoralEmbedStream_Comment_SingleComment\n              replies(query: {limit : 50000, excludeIgnored: $excludeIgnored}) {\n                nodes {\n                  ...CoralEmbedStream_Comment_SingleComment\n                  replies(query: {limit : 50000, excludeIgnored: $excludeIgnored}) {\n                    nodes {\n                      ...CoralEmbedStream_Comment_SingleComment\n                      __typename\n                    }\n                    hasNextPage\n                    startCursor\n                    endCursor\n                    __typename\n                  }\n                  __typename\n                }\n                hasNextPage\n                startCursor\n                endCursor\n                __typename\n              }\n              __typename\n            }\n            hasNextPage\n            startCursor\n            endCursor\n            __typename\n          }\n          __typename\n        }\n        hasNextPage\n        startCursor\n        endCursor\n        __typename\n      }\n      __typename\n    }\n    hasNextPage\n    startCursor\n    endCursor\n    __typename\n  }\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_SingleComment on Comment {\n  id\n  body\n  created_at\n  status\n  replyCount\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  user {\n    id\n    username\n    __typename\n  }\n  status_history {\n    type\n    __typename\n  }\n  action_summaries {\n    __typename\n    count\n    current_user {\n      id\n      __typename\n    }\n  }\n  editing {\n    edited\n    editableUntil\n    __typename\n  }\n  ...TalkSlot_CommentInfoBar_comment\n  ...TalkSlot_CommentReactions_comment\n  ...TalkSlot_CommentAvatar_comment\n  ...TalkSlot_CommentAuthorName_comment\n  ...TalkSlot_CommentContent_comment\n  ...TalkEmbedStream_DraftArea_comment\n  ...TalkEmbedStream_DraftArea_comment\n  __typename\n}\n\nfragment TalkEmbedStream_DraftArea_comment on Comment {\n  __typename\n  ...TalkSlot_DraftArea_comment\n}\n\nfragment CoralEmbedStream_Stream_singleComment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  ...CoralEmbedStream_Comment_SingleComment\n  __typename\n}\n\nfragment CoralEmbedStream_Configure_root on RootQuery {\n  __typename\n  ...CoralEmbedStream_Settings_root\n}\n\nfragment CoralEmbedStream_Settings_root on RootQuery {\n  __typename\n}\n\nfragment CoralEmbedStream_Configure_asset on Asset {\n  __typename\n  ...CoralEmbedStream_AssetStatusInfo_asset\n  ...CoralEmbedStream_Settings_asset\n}\n\nfragment CoralEmbedStream_AssetStatusInfo_asset on Asset {\n  id\n  closedAt\n  isClosed\n  __typename\n}\n\nfragment CoralEmbedStream_Settings_asset on Asset {\n  id\n  settings {\n    moderation\n    premodLinksEnable\n    questionBoxEnable\n    questionBoxIcon\n    questionBoxContent\n    __typename\n  }\n  __typename\n}\n\nfragment CoralEmbedStream_AutomaticAssetClosure_asset on Asset {\n  id\n  closedAt\n  __typename\n}\n\nfragment TalkSlot_StreamFilter_root on RootQuery {\n  ...TalkViewingOptions_ViewingOptions_root\n  __typename\n}\n\nfragment TalkViewingOptions_ViewingOptions_root on RootQuery {\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_root on RootQuery {\n  ...TalkModerationActions_root\n  __typename\n}\n\nfragment TalkModerationActions_root on RootQuery {\n  me {\n    id\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_root on RootQuery {\n  ...TalkAuthorMenu_AuthorName_root\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_root on RootQuery {\n  __typename\n  ...TalkSlot_AuthorMenuActions_root\n}\n\nfragment TalkSlot_StreamFilter_asset on Asset {\n  ...TalkViewingOptions_ViewingOptions_asset\n  __typename\n}\n\nfragment TalkViewingOptions_ViewingOptions_asset on Asset {\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_asset on Asset {\n  ...TalkModerationActions_asset\n  ...TalkPermalink_Button_asset\n  __typename\n}\n\nfragment TalkModerationActions_asset on Asset {\n  id\n  __typename\n}\n\nfragment TalkPermalink_Button_asset on Asset {\n  url\n  __typename\n}\n\nfragment TalkSlot_CommentReactions_asset on Asset {\n  ...VoteButton_asset\n  __typename\n}\n\nfragment VoteButton_asset on Asset {\n  id\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_asset on Asset {\n  ...TalkAuthorMenu_AuthorName_asset\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_asset on Asset {\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_comment on Comment {\n  ...CollapseCommentButton_comment\n  ...TalkModerationActions_comment\n  ...TalkPermalink_Button_comment\n  ...TalkInfoBar_moveReportButton_Comment\n  ...TalkInfoBar_addEdiableClass_Comment\n  __typename\n}\n\nfragment CollapseCommentButton_comment on Comment {\n  id\n  replyCount\n  __typename\n}\n\nfragment TalkModerationActions_comment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment TalkPermalink_Button_comment on Comment {\n  id\n  __typename\n}\n\nfragment TalkInfoBar_moveReportButton_Comment on Comment {\n  id\n  __typename\n}\n\nfragment TalkInfoBar_addEdiableClass_Comment on Comment {\n  id\n  editing {\n    __typename\n    editableUntil\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentReactions_comment on Comment {\n  ...TalkDisableDeepReplies_disableDeepReplies_Comment\n  ...VoteButton_comment\n  __typename\n}\n\nfragment TalkDisableDeepReplies_disableDeepReplies_Comment on Comment {\n  id\n  __typename\n}\n\nfragment VoteButton_comment on Comment {\n  id\n  action_summaries {\n    __typename\n    ... on UpvoteActionSummary {\n      count\n      current_user {\n        id\n        __typename\n      }\n      __typename\n    }\n    ... on DownvoteActionSummary {\n      count\n      current_user {\n        id\n        __typename\n      }\n      __typename\n    }\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentAvatar_comment on Comment {\n  ...UserAvatar_comment\n  __typename\n}\n\nfragment UserAvatar_comment on Comment {\n  user {\n    avatar\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_comment on Comment {\n  ...TalkAuthorMenu_AuthorName_comment\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_comment on Comment {\n  __typename\n  id\n  user {\n    username\n    __typename\n  }\n  ...TalkSlot_AuthorMenuActions_comment\n}\n\nfragment TalkSlot_CommentContent_comment on Comment {\n  ...TalkPluginRichText_CommentContent_comment\n  __typename\n}\n\nfragment TalkPluginRichText_CommentContent_comment on Comment {\n  body\n  richTextBody\n  __typename\n}\n\nfragment TalkSlot_DraftArea_comment on Comment {\n  ...TalkPluginRichText_Editor_comment\n  __typename\n}\n\nfragment TalkPluginRichText_Editor_comment on Comment {\n  body\n  richTextBody\n  __typename\n}\n\nfragment TalkSlot_AuthorMenuActions_root on RootQuery {\n  ...TalkIgnoreUser_IgnoreUserAction_root\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserAction_root on RootQuery {\n  me {\n    id\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_AuthorMenuActions_comment on Comment {\n  ...TalkIgnoreUser_IgnoreUserAction_comment\n  ...TalkDrupalUserId_DrupalProfile_comment\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserAction_comment on Comment {\n  user {\n    id\n    __typename\n  }\n  ...TalkIgnoreUser_IgnoreUserConfirmation_comment\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserConfirmation_comment on Comment {\n  user {\n    id\n    username\n    __typename\n  }\n  __typename\n}\n\nfragment TalkDrupalUserId_DrupalProfile_comment on Comment {\n  user {\n    id\n    __typename\n  }\n  __typename\n}\n","variables":{"assetId":"","assetUrl":blog['url'],"commentId":"","hasComment":False,"excludeIgnored":False,"sortBy":"CREATED_AT","sortOrder":"DESC"},"operationName":"CoralEmbedStream_Embed"}
        yield scrapy.Request('https://talk.zerohedge.com/api/v1/graph/ql',
                                    method = 'POST',
                                    body=json.dumps(payload), 
                                    headers={'Content-Type':'application/json'},
                                    callback=self.process_comments)

    def process_comments(self, response):
        #Processing responses
        post_comments = json.loads(response.body)
        data = post_comments['data']['asset']['comments']['nodes']
        comments = process_comment(data, post_comments['data']['asset']['url']) 
        for comment in comments:
            yield comment


def convert_date(date_string):
    try:
        return datetime.strptime(date_string.split(', ')[-1], '%m/%d/%Y - %H:%M')
    except:
        return dateutil.parser.parse(date_string)

def process_comment(data, blog_url, parent_comment=None):
    parsed_comments = []
    #Parser for response & replies
    for comment in data:
        c = Comments()
        c['domain'] = 'zerohedge.com'
        c['url'] = blog_url
        c['comment_id'] = comment['id']
        c['username'] = comment['user']['username']
        c['user_id'] = comment['user']['id']
        c['comment'] = comment['body']
        c['comment_original'] = comment['richTextBody']
        c['links'] = get_links(comment['richTextBody'])
        #Setting defulat values for votes
        c['upvotes'] = 0
        c['downvotes'] = 0
        #Seeing if there are any votes, overwritting defaults
        for action in comment['action_summaries']:
            if action['__typename'] == 'UpvoteActionSummary': c['upvotes'] = action['count']
            if action['__typename'] == 'DownvoteActionSummary': c['downvotes'] = action['count']
        c['published_date'] = convert_date(comment['created_at'])
        c['reply_count'] = comment['replyCount']
        c['reply_to'] = parent_comment
        parsed_comments.append(c)
        #Managing replies
        try: 
            replies = comment['replies']['nodes']
        except:
            #Sometimes with no replies, there is no replies field
            replies = None
        if replies: 
            parsed_comments += process_comment(replies, blog_url, parent_comment=comment['id'])
    #Finished
    return parsed_comments