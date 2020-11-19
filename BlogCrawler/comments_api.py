import json
import requests
import urllib
import re

from .utils import find_json

def facebook_comments(post_url, app_id):
    feed_url = urllib.parse.quote(post_url, safe='')
    url = f"https://www.facebook.com/plugins/feedback.php?app_id={app_id}&href={feed_url}"

    verify = True
    count = 0
    while True and count < 5:
        try:
            r1 = requests.get(url, verify)
            verify=True
            break
        except requests.exceptions.SSLError:
            verify=False  
            count += 1
            if count >= 5:
                print('Request failed')

    # Getting count of original comments
    commentcount = 0
    comment_json = [x for x in find_json(r1.text) if 'require' in x and 'instances' in x]
    comment_json = comment_json[0] if comment_json else []
    commentcount = comment_json['require'][2][3][0]['props']['meta']['totalCount'] if comment_json else 0
    if not commentcount: 
        #No comments on the page
        return {"comments":[], "authors":[], "reply_dic":{}}
    

    #Getting the main comment id for the article
    pos = r1.text.find("commentIDs") + len("commentIDs") + 4
    comment_id = r1.text[pos:pos+16].replace('_', '')
    if comment_id == ',"idMap":{}},"me': 
        print(f"Error getting comment_id for {post_url} ")
        return {"comments":[], "authors":[], "reply_dic":{}} 
    url = f'https://www.facebook.com/plugins/comments/async/{comment_id}/pager/social/'

    form_data = {
        'limit': 500000,
        '__a': 1}

    session = requests.Session()
    count = 0
    while True and count < 5:
        try:
            r2 = session.post(url, data=form_data, verify = verify)
            verify=True
            break
        except requests.exceptions.SSLError:
            verify=False  
            count += 1 
            if count >= 5:
                print('Request failed')

    error = False
    if len(r2.content) <= 13:
        #No comments on the page
        return {"comments":[], "authors":[], "reply_dic":{}}
    else:
        if r2.status_code==200: data = json.loads(r2.content[9:])
        else: 
            print(f"Error downloading {post_url} {r2.status_code}:{r2.reason}")
            return {"comments":[], "authors":[], "reply_dic":{}}

    # If only one original comment
    if (error and commentcount == 1) or data['payload']==None:  
        if comment_json: comments = comment_json['require'][2][3][0]['props']['comments']['idMap']
    else:
        comments = data['payload']['idMap']


    #Parsing the comments
    comment_list = []
    author_list = []
    
    for item in comments:
        # Checking if it's a comment, comments have a longer id than just the comment id, checking that is comment type
        if comment_id in item and comment_id != item and comments[item]['type'] == 'comment':
            comment_list.append(comments[item])
            #Sending additional requests for replies
            if 'public_replies' in comments[item] and 'afterCursor' in comments[item]['public_replies']:
                replies, authors = _get_facebook_replies(item, comments[item]['public_replies']['afterCursor'])
                comment_list += replies
                author_list += authors
        else:
            author_list.append(comments[item])
    #Filtering out duplicates
    unique_comment_ids = []
    for x in comment_list:
        if x['id'] not in set([y['id'] for y in unique_comment_ids]):
            unique_comment_ids.append(x)
    comment_list = unique_comment_ids

    #reply dictionary
    reply_dic = _get_facebook_reply_dic(comment_list)

    return {"comments":comment_list, "authors":author_list, "reply_dic":reply_dic}

def _get_facebook_replies(comment_id, after_cursor):
    #Sending replies request, loading data
    url = f'https://www.facebook.com/plugins/comments/async/comment/{comment_id}/pager/'
    form_data = {
    'after_cursor': after_cursor,
    'limit': 500000,
    '__a': 1
    }
    
    session = requests.Session()
    r = session.post(url, data=form_data)
    data = json.loads(r.content[9:])

    #Resettign comment id, parsing replies
    comment_list = []
    author_list = []
    original_id = comment_id
    comment_id = comment_id[:16]
    comments = data['payload']['idMap']
    for item in comments:
        # Checking if it's a comment, comments have a longer id than just the comment id, checking that it is comment type
        if comment_id in item and comment_id != item and comments[item]['type'] == 'comment':
            comment_list.append(comments[item])
            #Sending additional requests for replies
            if 'public_replies' in comments[item] and 'afterCursor' in comments[item]['public_replies']:
                replies, authors = _get_facebook_replies(item, comments[item]['public_replies']['afterCursor'])
                comment_list += replies
                author_list += authors
        elif item != original_id:
            author_list.append(comments[item])
    return comment_list, author_list

def _get_facebook_reply_dic(comments):
    if comments:
        dic = {}
        for comment in comments:
            if 'public_replies' in comment:
                try:
                    for cid in comment['public_replies']['commentIDs']:
                        dic[cid] = comment['id']
                except KeyError:
                    # This does not seem to effect the reply author lookup dic (duplicate comments in data but not in blog)
                    # raise Exception(f"Facebook API missing reply id's in this blog: {comment['ogURL']}")
                    pass
        return dic
    else: #No comments
        return None

def get_torontosun_comments(article_id):
    limit = 100
    result = []
    while True:
        end_point = f'https://livecomments.viafoura.co/v4/livecomments/00000000-0000-4000-8000-d11b93482c8b?limit={limit}&container_id={article_id}&reply_limit=100&sorted_by=newest'
        response = requests.get(end_point)
        if response.status_code == 200:
            response = response.json()
            if 'contents' in response:
                if response['contents']:
                    result+= response['contents']
            if 'more_available' in response:
                if response['more_available']: 
                    limit += 100
                else:
                    break
        else:
            break
    return result

            

