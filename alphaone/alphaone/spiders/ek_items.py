# -*- coding: utf-8 -*-
import scrapy


class EkItemsSpider(scrapy.Spider):
    name = 'ek_items'
    allowed_domains = ['ebay-kleinanzeigen.de']
    start_urls = ['http://ebay-kleinanzeigen.de/']

    def parse(self, response):
        pass
