import scrapy
import os
from scrapy import signals
from scrapy_playwright.page import PageMethod
from google.items import GoogleItem


class GoogleSpiderSpider(scrapy.Spider):
    name = "google_spider"

    def __init__(self, start_url=None, *args, **kwargs):
        super(GoogleSpiderSpider, self).__init__(*args, **kwargs)
        self.start_url = start_url
        self.total_found = 0
        self.total_scraped = 0

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(GoogleSpiderSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(spider.engine_stopped, signal=signals.engine_stopped)
        return spider

    def send_progress(self):
        """Send progress to GUI via stdout"""
        print(f"@@PROGRESS@@{self.total_found}@@{self.total_scraped}", flush=True)

    def item_scraped(self, item, spider):
        """Called whenever an item is scraped"""
        if spider.name == self.name:
            self.total_scraped += 1
            self.send_progress()

    def spider_closed(self, spider):
        """Send final stats when spider closes"""
        print(f"@@FINAL@@{self.total_found}@@{self.total_scraped}", flush=True)
        self.logger.info(f"Final stats - Found: {self.total_found}, Scraped: {self.total_scraped}")

    def engine_stopped(self):
        """Force exit to prevent IocpProactor hanging on Windows"""
        self.logger.info("Engine stopped, forcing exit to avoid asyncio hang...")
        os._exit(0)

    def start_requests(self):
        url = self.start_url or "https://www.google.com/maps/search/photographers+uk/@51.5541852,-0.5023449,10z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI2MDQwNy4wIKXMDSoASAFQAw%3D%3D"
        yield scrapy.Request(
            url=url, 
            callback=self.parse, 
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "a.hfpxzc", state="attached", timeout=15000),
                    PageMethod("wait_for_timeout", 2000),
                ],
                "playwright_include_page": True,
            },
            errback=self.errback_close_page,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        try:
            previous_count = 0
            scroll_attempts = 0
            max_scrolls = 50
            
            while scroll_attempts < max_scrolls:
                # Get current count of listings
                current_links = await page.query_selector_all("a.hfpxzc")
                current_count = len(current_links)
                
                self.logger.info(f"Scroll {scroll_attempts + 1}: Found {current_count} listings")
                
                # Update found count and send to GUI
                self.total_found = current_count
                self.send_progress()
                
                # Scroll the results panel
                await page.evaluate('''
                    () => {
                        const panel = document.querySelector('div[role="feed"]');
                        if (panel) {
                            panel.scrollTo(0, panel.scrollHeight);
                        }
                    }
                ''')
                
                # Wait for new results to load
                await page.wait_for_timeout(2000)
                
                # Check if we've loaded new results
                if current_count == previous_count:
                    self.logger.info("No new listings loaded, reached end")
                    break
                
                previous_count = current_count
                scroll_attempts += 1
            
            # Get the updated HTML after all scrolling
            updated_html = await page.content()
            updated_response = response.replace(body=updated_html)
            
            # Extract all links and remove duplicates
            links = updated_response.css('a.hfpxzc::attr(href)').getall()
            unique_links = list(dict.fromkeys(links))
            
            self.total_found = len(unique_links)
            self.send_progress()
            self.logger.info(f"Total unique listings found: {len(unique_links)}")
            
            for link in unique_links:
                yield scrapy.Request(
                    url=link, 
                    callback=self.parse_details,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "h1.DUwDvf", state="attached", timeout=15000),
                            PageMethod("wait_for_timeout", 2000),
                        ],
                    }
                )
        
        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                except Exception as e:
                    self.logger.warning(f"Error closing page: {e}")

    async def errback_close_page(self, failure):
        """Close page on error to prevent leaks"""
        page = failure.request.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass

    async def parse_details(self, response):
        page = response.meta.get("playwright_page")
        try:
            item = GoogleItem()
            item['name'] = response.css('h1.DUwDvf::text').get()
            self.logger.info(f"Scraped details for: {item['name']}")
            
            address_label = response.css('button[data-item-id="address"]::attr(aria-label)').get()
            item['address'] = address_label 
            self.logger.info(f"Address: {item['address']}")
            
            phone_label = response.css('button[data-item-id^="phone:tel:"]::attr(aria-label)').get()
            item['phone'] = phone_label
            self.logger.info(f"Phone: {item['phone']}")

            website_label = response.css('a[data-item-id^="authority"]::attr(href)').get()
            item['website'] = website_label
            self.logger.info(f"Website: {item['website']}")

            rating = response.css('div.F7nice span::text').get()
            item['rating'] = rating 
            self.logger.info(f"Rating: {item['rating']}/5.0")


            yield item

        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                except:
                    pass