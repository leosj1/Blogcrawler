import os
from scrapy.cmdline import execute

os.chdir(os.path.dirname(os.path.realpath(__file__)))

try:
    execute(
        [
            'scrapy',
            'crawl',
            'accidentaldeliberations',
            # '-o',
            # 'zerohedge_comments.json',
        ]
    )
except SystemExit:
    pass