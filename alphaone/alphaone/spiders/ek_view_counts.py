# -*- coding: utf-8 -*-
import scrapy


class EkViewCountsSpider(scrapy.Spider):
    name = 'ek_view_counts'
    allowed_domains = ['ebay-kleinanzeigen.de']
    start_urls = ['http://ebay-kleinanzeigen.de/']

    def start_requests(self):
        urls = [
            'https://m.ebay-kleinanzeigen.de/s-vac/?adId=1467230923&userId=67461734',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_count)

    def parse_count(self, response):
        # https://stackoverflow.com/questions/55658640/how-to-know-which-user-agent-is-currently-used-in-the-scrapy-spider
        print("\n\ncurrent user-agent:{}\n\n".format(response.request.headers['User-Agent']))
        filename = 'ek_view_counts.txt'
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log('Saved file %s' % filename)
