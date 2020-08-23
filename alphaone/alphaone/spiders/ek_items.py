# -*- coding: utf-8 -*-
import scrapy


class EkItemsSpider(scrapy.Spider):
    name = 'ek_items'
    allowed_domains = ['ebay-kleinanzeigen.de']

    def start_requests(self):
        urls = [
            'https://www.ebay-kleinanzeigen.de/s-anzeige/1477722139',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_item)

    def parse_item(self, response):
        filename = 'ek_items.txt'
        with open(filename, 'wb') as f:
            f.write(b'1477722139')
        self.log('Saved file %s' % filename)
