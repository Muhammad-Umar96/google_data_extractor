import scrapy
from scrapy_playwright.page import PageMethod
from google.items import GoogleItem


class GoogleSpiderSpider(scrapy.Spider):
    name = "google_spider"

    def start_requests(self):
        url = "https://www.google.com/maps/search/real+estate+agent+uk/@52.6199242,-3.9167784,7z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI2MDMyMi4wIKXMDSoASAFQAw%3D%3D"
        yield scrapy.Request(url=url, callback=self.parse, 
                            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "a.hfpxzc", state="attached", timeout=15000),
                    PageMethod("wait_for_timeout", 2000),
                ],
            }
        )

    def parse(self, response):
        links = response.css('a.hfpxzc::attr(href)').getall()
        for link in links:
            yield scrapy.Request(url=link, callback=self.parse_details, meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "h1.DUwDvf", state="attached", timeout=15000),
                            PageMethod("wait_for_timeout", 2000),
                        ],
                    }
                )

    def parse_details(self, response):
        item = GoogleItem()
        item['name'] = response.css('h1.DUwDvf::text').get()
        
        address_label = response.css('button[data-item-id="address"]::attr(aria-label)').get()
        item['address'] = address_label if address_label else response.css('button[aria-label*="Address"]::attr(aria-label)').get()
        
        phone_label = response.css('button[data-item-id^="phone:tel:"]::attr(aria-label)').get()
        item['phone'] = phone_label if phone_label else response.css('button[aria-label*="Phone"]::attr(aria-label)').get()

        yield item