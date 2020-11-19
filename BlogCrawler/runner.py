import os
from scrapy.cmdline import execute

os.chdir(os.path.dirname(os.path.realpath(__file__)))

try:
    execute(
        [
            'scrapy',
            'crawl',
            'tnc',
            # '-o',
            # 'zerohedge_comments.json',
        ]
    )
except SystemExit:
    pass

# from scrapy.crawler import CrawlerProcess
# from scrapy.utils.project import get_project_settings
# process = CrawlerProcess(get_project_settings())

# # process.crawl('buffalochronicles')
# process.crawl('torontosun')
# # process.crawl('globalnews')
# # process.crawl('tnc')
# process.start()