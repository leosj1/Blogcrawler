# -*- coding: utf-8 -*-
import json
import scrapy
import requests
import dateutil
from urllib.parse import unquote
from dateutil.parser import parse

from BlogCrawler.items import Posts, Stats, Comments
from BlogCrawler.utils import get_links, tags_to_json, get_start_urls

class InfowarsSpider(scrapy.Spider):
    name = 'infowars'
    domain = 'infowars.com'
    allowed_domains = ['infowars.com']
    home_pages = ['https://www.infowars.com/category/8/', 'https://www.infowars.com/category/5/', 'https://www.infowars.com/category/2/',
     'https://www.infowars.com/category/18/', 'https://www.infowars.com/category/10/', 'https://www.infowars.com/category/3/',
     'https://www.infowars.com/category/11/', 'https://www.infowars.com/category/14/', 'https://www.infowars.com/category/4/']
    start_urls = home_pages + get_start_urls(domain)

    def parse(self, response):
        return
        #Parsing home pages
        if any(x for x in self.home_pages if x in response.url):
            #Getting articles from page
            for blog_url in response.xpath('//a[contains(@class, "css-1xjmleq")]/@href').getall():
                yield scrapy.Request('https://www.infowars.com' + blog_url, self.parse_blog,
                    meta={'dont_redirect': True}, headers={'accept':"text/html", "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"})
        #Processsing articles in db
        else:
            yield scrapy.Request(response.url, self.parse_blog,
                meta={'dont_redirect': True}, headers={'accept':"text/html", "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"})


    def parse_blog(self, response):
        url = unquote(response.url)
        blog = Posts()
        try:
            blog['domain'] = self.domain
            blog['url'] = url
            blog['title'] = response.xpath('//h1[contains(@class, "css-1ln1egd")]/text()').get()
            blog['author'] = get_author(response)
            blog['published_date']= parse(response.xpath('//*[contains(@class, "css-1fboxhy")]/a/text()').get())
            blog['content'] = " ".join(response.xpath('//*[contains(@class, "css-118w07p")]/p//text()').getall()).strip().replace('\n','')
            blog['content_html'] = response.xpath('//*[contains(@class, "css-118w07p")]').get()
            blog['links'] = get_links(response.xpath('//*[contains(@class, "css-118w07p")]').get())
            blog['tags'] = None
            if blog['title']: yield blog
        except Exception as e:
            print(":here")

        #Stats
        stat = Stats()
        stat['domain'] = self.domain
        stat['url'] = url
        stat['views'] = None
        stat['likes'] = None
        comments = get_comments(response.url)
        stat['comments'] =  comments['total'] if comments else None
        yield stat

        #Comments
        for comment in comments['comments']:
            if comment['body'] != None: #sometimes there are empty reply comments
                parsed_comment = Comments()
                parsed_comment['domain'] = self.domain
                parsed_comment['url'] = url
                parsed_comment['comment_id'] = comment['id']
                parsed_comment['username'] = comment['user']['username']
                parsed_comment['user_id'] = comment['user']['id']
                parsed_comment['comment'] = comment['body']
                original_comment = comment['richTextBody'] if comment['richTextBody'] is not None else comment['body']
                parsed_comment['comment_original'] = original_comment
                parsed_comment['links'] = get_links(original_comment)
                parsed_comment['upvotes'] = comment['action_summaries'][0]['count'] if comment['action_summaries'] else None
                parsed_comment['downvotes'] = None
                parsed_comment['published_date'] = parse(comment['created_at'])
                parsed_comment['reply_count'] = comment['replyCount']
                parsed_comment['reply_to'] = comments['replies'][parsed_comment['comment_id']] if  parsed_comment['comment_id'] in comments['replies'] else None
                yield parsed_comment

def get_views(post_id):
    url = "https://api.infowars.com/graphql" 
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    body = {"query":"mutation IncreaseViewCountMutation($postId:Int){increaseViewCount(input:{clientMutationId:\"viewCount\",isViewed:1,postId:$postId}){viewCount clientMutationId}}", 
            "variables":{"postId":post_id}}
    r = requests.post(url, json=body, headers=headers)
    d = r.json()
    return d['data']['increaseViewCount']['viewCount']

def get_author(response):
    author_lst = [x for x in response.xpath('//*[contains(@class, "css-kl31lu")]//a/text()').getall() if "by " not in x]
    if len(author_lst) > 1:
        author = author_lst[0] 
    elif [x for x in response.xpath('//*[contains(@class, "css-kl31lu")]/a/u/text()').getall() if x.strip()]:
        author = [x for x in response.xpath('//*[contains(@class, "css-kl31lu")]/a/u/text()').getall() if x.strip()][0]
    else:
        author = response.xpath('//*[contains(@class, "css-kl31lu")]/div/text()').get()
    if not author:
        print("asdfsdf")
    return author

def get_comments(blog_url):
    #Data Format
    return_data = {
        'total':0,
        'comments':[],
        'replies': {}
    }
    endpoint = 'https://platform.cmmtr.com/api/v1/graph/ql'
    payload = {"query":"query CoralEmbedStream_Embed($assetId: ID, $assetUrl: String, $commentId: ID!, $hasComment: Boolean!, $excludeIgnored: Boolean, $sortBy: SORT_COMMENTS_BY!, $sortOrder: SORT_ORDER!) {\n  me {\n    id\n    state {\n      status {\n        username {\n          status\n          __typename\n        }\n        banned {\n          status\n          __typename\n        }\n        alwaysPremod {\n          status\n          __typename\n        }\n        suspension {\n          until\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  asset(id: $assetId, url: $assetUrl) {\n    ...CoralEmbedStream_Configure_asset\n    ...CoralEmbedStream_Stream_asset\n    ...CoralEmbedStream_AutomaticAssetClosure_asset\n    __typename\n  }\n  ...CoralEmbedStream_Stream_root\n  ...CoralEmbedStream_Configure_root\n}\n\nfragment CoralEmbedStream_Stream_root on RootQuery {\n  me {\n    state {\n      status {\n        username {\n          status\n          __typename\n        }\n        banned {\n          status\n          __typename\n        }\n        alwaysPremod {\n          status\n          __typename\n        }\n        suspension {\n          until\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    ignoredUsers {\n      id\n      __typename\n    }\n    role\n    __typename\n  }\n  settings {\n    organizationName\n    __typename\n  }\n  ...TalkSlot_StreamTabPanes_root\n  ...TalkSlot_StreamFilter_root\n  ...TalkSlot_Stream_root\n  ...CoralEmbedStream_Comment_root\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_root on RootQuery {\n  me {\n    ignoredUsers {\n      id\n      __typename\n    }\n    __typename\n  }\n  ...TalkSlot_CommentInfoBar_root\n  ...TalkSlot_CommentAuthorName_root\n  ...TalkEmbedStream_DraftArea_root\n  ...TalkEmbedStream_DraftArea_root\n  __typename\n}\n\nfragment TalkEmbedStream_DraftArea_root on RootQuery {\n  __typename\n}\n\nfragment CoralEmbedStream_Stream_asset on Asset {\n  comment(id: $commentId) @include(if: $hasComment) {\n    ...CoralEmbedStream_Stream_comment\n    parent {\n      ...CoralEmbedStream_Stream_singleComment\n      parent {\n        ...CoralEmbedStream_Stream_singleComment\n        parent {\n          ...CoralEmbedStream_Stream_singleComment\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  id\n  title\n  url\n  isClosed\n  created_at\n  settings {\n    moderation\n    infoBoxEnable\n    infoBoxContent\n    premodLinksEnable\n    questionBoxEnable\n    questionBoxContent\n    questionBoxIcon\n    closedTimeout\n    closedMessage\n    disableCommenting\n    disableCommentingMessage\n    charCountEnable\n    charCount\n    requireEmailConfirmation\n    __typename\n  }\n  totalCommentCount @skip(if: $hasComment)\n  comments(query: {limit: 100000, excludeIgnored: $excludeIgnored, sortOrder: $sortOrder, sortBy: $sortBy}) @skip(if: $hasComment) {\n    nodes {\n      ...CoralEmbedStream_Stream_comment\n      __typename\n    }\n    hasNextPage\n    startCursor\n    endCursor\n    __typename\n  }\n  ...TalkSlot_StreamTabsPrepend_asset\n  ...TalkSlot_StreamTabPanes_asset\n  ...TalkSlot_StreamFilter_asset\n  ...CoralEmbedStream_Comment_asset\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_asset on Asset {\n  __typename\n  id\n  ...TalkSlot_CommentInfoBar_asset\n  ...TalkSlot_CommentActions_asset\n  ...TalkSlot_CommentReactions_asset\n  ...TalkSlot_CommentAuthorName_asset\n}\n\nfragment CoralEmbedStream_Stream_comment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  ...CoralEmbedStream_Comment_comment\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_comment on Comment {\n  ...CoralEmbedStream_Comment_SingleComment\n  replies(query: {limit: 3000000, excludeIgnored: $excludeIgnored}) {\n    nodes {\n      ...CoralEmbedStream_Comment_SingleComment\n      replies(query: {limit: 30000000, excludeIgnored: $excludeIgnored}) {\n        nodes {\n          ...CoralEmbedStream_Comment_SingleComment\n          replies(query: {limit: 300000000, excludeIgnored: $excludeIgnored}) {\n            nodes {\n              ...CoralEmbedStream_Comment_SingleComment\n              __typename\n            }\n            hasNextPage\n            startCursor\n            endCursor\n            __typename\n          }\n          __typename\n        }\n        hasNextPage\n        startCursor\n        endCursor\n        __typename\n      }\n      __typename\n    }\n    hasNextPage\n    startCursor\n    endCursor\n    __typename\n  }\n  __typename\n}\n\nfragment CoralEmbedStream_Comment_SingleComment on Comment {\n  id\n  body\n  created_at\n  status\n  replyCount\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  user {\n    id\n    username\n    __typename\n  }\n  status_history {\n    type\n    __typename\n  }\n  action_summaries {\n    __typename\n    count\n    current_user {\n      id\n      __typename\n    }\n  }\n  editing {\n    edited\n    editableUntil\n    __typename\n  }\n  ...TalkSlot_CommentInfoBar_comment\n  ...TalkSlot_CommentActions_comment\n  ...TalkSlot_CommentReactions_comment\n  ...TalkSlot_CommentAuthorName_comment\n  ...TalkSlot_CommentContent_comment\n  ...TalkEmbedStream_DraftArea_comment\n  ...TalkEmbedStream_DraftArea_comment\n  __typename\n}\n\nfragment TalkEmbedStream_DraftArea_comment on Comment {\n  __typename\n  ...TalkSlot_DraftArea_comment\n}\n\nfragment CoralEmbedStream_Stream_singleComment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  ...CoralEmbedStream_Comment_SingleComment\n  __typename\n}\n\nfragment CoralEmbedStream_Configure_root on RootQuery {\n  __typename\n  ...CoralEmbedStream_Settings_root\n}\n\nfragment CoralEmbedStream_Settings_root on RootQuery {\n  __typename\n}\n\nfragment CoralEmbedStream_Configure_asset on Asset {\n  __typename\n  ...CoralEmbedStream_AssetStatusInfo_asset\n  ...CoralEmbedStream_Settings_asset\n}\n\nfragment CoralEmbedStream_AssetStatusInfo_asset on Asset {\n  id\n  closedAt\n  isClosed\n  __typename\n}\n\nfragment CoralEmbedStream_Settings_asset on Asset {\n  id\n  settings {\n    moderation\n    premodLinksEnable\n    questionBoxEnable\n    questionBoxIcon\n    questionBoxContent\n    __typename\n  }\n  __typename\n}\n\nfragment CoralEmbedStream_AutomaticAssetClosure_asset on Asset {\n  id\n  closedAt\n  __typename\n}\n\nfragment TalkSlot_StreamTabPanes_root on RootQuery {\n  ...TalkFeaturedComments_TabPane_root\n  __typename\n}\n\nfragment TalkFeaturedComments_TabPane_root on RootQuery {\n  __typename\n  ...TalkFeaturedComments_Comment_root\n}\n\nfragment TalkFeaturedComments_Comment_root on RootQuery {\n  __typename\n  ...TalkSlot_CommentAuthorName_root\n}\n\nfragment TalkSlot_StreamFilter_root on RootQuery {\n  ...TalkViewingOptions_ViewingOptions_root\n  __typename\n}\n\nfragment TalkViewingOptions_ViewingOptions_root on RootQuery {\n  __typename\n}\n\nfragment TalkSlot_Stream_root on RootQuery {\n  ...TalkPluginLocalAuth_AddEmailAddressDialog_root\n  ...Talk_AccountDeletionRequestedSignIn_root\n  __typename\n}\n\nfragment TalkPluginLocalAuth_AddEmailAddressDialog_root on RootQuery {\n  me {\n    id\n    email\n    state {\n      status {\n        username {\n          status\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  settings {\n    requireEmailConfirmation\n    __typename\n  }\n  __typename\n}\n\nfragment Talk_AccountDeletionRequestedSignIn_root on RootQuery {\n  me {\n    scheduledDeletionDate\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_root on RootQuery {\n  ...TalkModerationActions_root\n  __typename\n}\n\nfragment TalkModerationActions_root on RootQuery {\n  me {\n    id\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_root on RootQuery {\n  ...TalkAuthorMenu_AuthorName_root\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_root on RootQuery {\n  __typename\n  ...TalkSlot_AuthorMenuActions_root\n}\n\nfragment TalkSlot_StreamTabsPrepend_asset on Asset {\n  ...TalkFeaturedComments_Tab_asset\n  __typename\n}\n\nfragment TalkFeaturedComments_Tab_asset on Asset {\n  featuredCommentsCount: totalCommentCount(tags: [\"FEATURED\"]) @skip(if: $hasComment)\n  __typename\n}\n\nfragment TalkSlot_StreamTabPanes_asset on Asset {\n  ...TalkFeaturedComments_TabPane_asset\n  __typename\n}\n\nfragment TalkFeaturedComments_TabPane_asset on Asset {\n  id\n  featuredComments: comments(query: {tags: [\"FEATURED\"], sortOrder: $sortOrder, sortBy: $sortBy, excludeIgnored: $excludeIgnored}, deep: true) @skip(if: $hasComment) {\n    nodes {\n      ...TalkFeaturedComments_Comment_comment\n      __typename\n    }\n    hasNextPage\n    startCursor\n    endCursor\n    __typename\n  }\n  ...TalkFeaturedComments_Comment_asset\n  __typename\n}\n\nfragment TalkFeaturedComments_Comment_comment on Comment {\n  id\n  body\n  created_at\n  replyCount\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  user {\n    id\n    username\n    __typename\n  }\n  ...TalkSlot_CommentReactions_comment\n  ...TalkSlot_CommentAuthorName_comment\n  ...TalkSlot_CommentContent_comment\n  __typename\n}\n\nfragment TalkFeaturedComments_Comment_asset on Asset {\n  __typename\n  ...TalkSlot_CommentReactions_asset\n  ...TalkSlot_CommentAuthorName_asset\n}\n\nfragment TalkSlot_StreamFilter_asset on Asset {\n  ...TalkViewingOptions_ViewingOptions_asset\n  __typename\n}\n\nfragment TalkViewingOptions_ViewingOptions_asset on Asset {\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_asset on Asset {\n  ...TalkModerationActions_asset\n  __typename\n}\n\nfragment TalkModerationActions_asset on Asset {\n  id\n  __typename\n}\n\nfragment TalkSlot_CommentActions_asset on Asset {\n  ...TalkPermalink_Button_asset\n  __typename\n}\n\nfragment TalkPermalink_Button_asset on Asset {\n  url\n  __typename\n}\n\nfragment TalkSlot_CommentReactions_asset on Asset {\n  ...RespectButton_asset\n  __typename\n}\n\nfragment RespectButton_asset on Asset {\n  id\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_asset on Asset {\n  ...TalkAuthorMenu_AuthorName_asset\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_asset on Asset {\n  __typename\n}\n\nfragment TalkSlot_CommentInfoBar_comment on Comment {\n  ...TalkFeaturedComments_Tag_comment\n  ...TalkModerationActions_comment\n  __typename\n}\n\nfragment TalkFeaturedComments_Tag_comment on Comment {\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment TalkModerationActions_comment on Comment {\n  id\n  status\n  user {\n    id\n    __typename\n  }\n  tags {\n    tag {\n      name\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentActions_comment on Comment {\n  ...TalkPermalink_Button_comment\n  __typename\n}\n\nfragment TalkPermalink_Button_comment on Comment {\n  id\n  __typename\n}\n\nfragment TalkSlot_CommentReactions_comment on Comment {\n  ...RespectButton_comment\n  __typename\n}\n\nfragment RespectButton_comment on Comment {\n  id\n  action_summaries {\n    __typename\n    ... on RespectActionSummary {\n      count\n      current_user {\n        id\n        __typename\n      }\n      __typename\n    }\n  }\n  __typename\n}\n\nfragment TalkSlot_CommentAuthorName_comment on Comment {\n  ...TalkAuthorMenu_AuthorName_comment\n  __typename\n}\n\nfragment TalkAuthorMenu_AuthorName_comment on Comment {\n  __typename\n  id\n  user {\n    username\n    __typename\n  }\n  ...TalkSlot_AuthorMenuInfos_comment\n  ...TalkSlot_AuthorMenuActions_comment\n}\n\nfragment TalkSlot_CommentContent_comment on Comment {\n  ...TalkPluginRichText_CommentContent_comment\n  __typename\n}\n\nfragment TalkPluginRichText_CommentContent_comment on Comment {\n  body\n  richTextBody\n  __typename\n}\n\nfragment TalkSlot_DraftArea_comment on Comment {\n  ...TalkPluginRichText_Editor_comment\n  __typename\n}\n\nfragment TalkPluginRichText_Editor_comment on Comment {\n  body\n  richTextBody\n  __typename\n}\n\nfragment TalkSlot_AuthorMenuActions_root on RootQuery {\n  ...TalkIgnoreUser_IgnoreUserAction_root\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserAction_root on RootQuery {\n  me {\n    id\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_AuthorMenuInfos_comment on Comment {\n  ...TalkMemberSince_MemberSinceInfo_comment\n  __typename\n}\n\nfragment TalkMemberSince_MemberSinceInfo_comment on Comment {\n  user {\n    username\n    created_at\n    __typename\n  }\n  __typename\n}\n\nfragment TalkSlot_AuthorMenuActions_comment on Comment {\n  ...TalkIgnoreUser_IgnoreUserAction_comment\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserAction_comment on Comment {\n  user {\n    id\n    __typename\n  }\n  ...TalkIgnoreUser_IgnoreUserConfirmation_comment\n  __typename\n}\n\nfragment TalkIgnoreUser_IgnoreUserConfirmation_comment on Comment {\n  user {\n    id\n    username\n    __typename\n  }\n  __typename\n}\n","variables":{"assetId":"","assetUrl":blog_url,"commentId":"","hasComment":False,"excludeIgnored":False,"sortBy":"CREATED_AT","sortOrder":"DESC"},"operationName":"CoralEmbedStream_Embed"}
    try:
        data = requests.post( endpoint, json=payload, headers={'Content-Type':'application/json'})
        data = data.json()
    except (requests.exceptions.ConnectionError, requests.exceptions.SSLError, json.decoder.JSONDecodeError):
        return return_data


    #Processing comments
    return_data['total'] = data['data']['asset']['totalCommentCount']
    #removing nested nodes
    return_data['comments'], return_data['replies'] = denest_comments(data['data']['asset']['comments']['nodes'])
    #Has Next page
    if data['data']['asset']['comments']['hasNextPage']:
        raise Exception("Comments says it has a next page, and I didn't build that funcationality...")

    return return_data

def denest_comments(comments):
    comment_list = []
    reply_dic = {}
    for comment in comments:
        comment_list.append(comment)
        if 'replies' in comment and comment['replies']['nodes']:
            nested_comments, nested_replies = denest_comments(comment['replies']['nodes'])
            comment_list += nested_comments
            reply_dic = dict(reply_dic, ** nested_replies)
            for reply in comment['replies']['nodes']:
                reply_dic[reply['id']] = comment['id']
    return comment_list, reply_dic
