# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import pymysql

from BlogCrawler.items import Posts, Stats, Comments

class DbPipeline(object):

    def get_daily_stats(self, item):
        connection = get_connection()
        with connection.cursor() as cursor: 
            cursor.execute("select views, comments, likes from stats where url = %s and crawled_time = (select max(crawled_time) from stats where url = %s)", (item['url'], item['url']))
            record = cursor.fetchall()
            try: 
                daily_views = int(item['views']) - record[0]['views']
            except IndexError: #Not found in database
                daily_views = 0
            except TypeError: #Not found in blog post
                daily_views = None
            try: 
                daily_comments = int(item['comments']) - record[0]['comments']
            except IndexError: #Not found in database
                daily_comments = 0
            except TypeError: #Not found in blog post
                daily_comments = None
            try: 
                daily_likes = int(item['likes']) - record[0]['likes']
            except IndexError: #Not found in database
                daily_likes = 0
            except TypeError: #Not found in blog post
                daily_likes = None     
        connection.close()
        return daily_views, daily_comments, daily_likes

    def process_item(self, item, spider):
        #Posts
        if isinstance(item, Posts):
            sql_query = """INSERT INTO posts (domain, url,  author, title, published_date, content, content_html, links) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            sql_data = (item['domain'], item['url'], item['author'],item['title'],item['published_date'],item['content'], item['content_html'],item['links'])
            commit_to_db(sql_query, sql_data)
            return item
        #Stats
        elif isinstance(item, Stats):
            item['daily_views'], item['daily_comments'], item['daily_likes'] = self.get_daily_stats(item)
            sql_query = """INSERT INTO stats (domain, url, views, likes, daily_views, comments, daily_comments) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            sql_data = (item['domain'], item['url'], item['views'], item['likes'],item['daily_views'],item['comments'],item['daily_comments'])
            commit_to_db(sql_query, sql_data)
            return item
        #Comments
        elif isinstance(item, Comments):
            sql_query = """INSERT INTO comments (domain, url, comment_id, username, user_id, comment, comment_original, links, upvotes, downvotes, published_date, reply_count, reply_to ) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE upvotes = %s, downvotes = %s, reply_count = %s, crawled_time = CURRENT_TIMESTAMP()"""
            sql_data = (item['domain'], item['url'], item['comment_id'], item['username'], item['user_id'], item['comment'], item['comment_original'], item['links'], item['upvotes'], item['downvotes'], item['published_date'], item['reply_count'], item['reply_to'], item['upvotes'], item['downvotes'], item['reply_count']) #NOTE the last 3 items are updated if duplicate
            commit_to_db(sql_query, sql_data)
            return item

#SQL Functions

def get_connection():
    connection = pymysql.connect(host='localhost',
                                user='scrapy',
                                password='Cosmos1',
                                db='blogs',
                                charset='utf8mb4',
                                use_unicode=True,
                                cursorclass=pymysql.cursors.DictCursor)
    return connection

def commit_to_db(query, data):
    # while True: 
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
                cursor.execute(query, data)
                connection.commit()
                connection.close()
                return 
    #Error handeling
    except Exception as e:
        if isinstance(e, pymysql.err.IntegrityError) and e.args[0]==1062:
            # Duplicate Entry, already in DB
            if 'INTO posts' in query:
                pass #Duplicate posts will happen, they don't need to be udpated
            else: 
                print("There is already duplicate entry in the DB, check the quary: {}".format(query))
            connection.close() 
            return
        elif e.args[0] == 1406:
            # Data too long for column
            print(e)
            print("Good API request, but data is Too Long for DB Column")
            connection.close()
            return 
        else: 
            # Uncaught errors
            raise Exception("We aren't catching this mySql commit_to_db Error: {}".format(e))
