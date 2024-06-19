import asyncio
import csv
import os
import re
import ssl
import time
from bs4 import BeautifulSoup
import certifi
from playwright.async_api import async_playwright
from typing import List
import uuid
import aiohttp
import aiofiles


def read_csv(csv_filename: str) -> List[dict]:
    """
    Function to read a csv file into an list of objects (dictionaries)
    - params: csv_filename: string

    """
    with open(csv_filename, "r") as csv_file:
        reader = csv.reader(csv_file)

        result = []
        for i, v in enumerate(reader):
            obj = {}
            # Skip the row that contains column names
            if i == 0:
                continue
            else:
                obj["VendorID"] = v[0]
                obj["LinkToSource"] = v[-1]
                result.append(obj)
        return result


async def save_image(review_id: str, filename: str, url: str, ext="png") -> None:
    folder_name = os.path.join("..", "images", review_id) 
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url, ssl_context=ssl_context) as response:
            if response.status == 200:
                content = await response.read()
                async with aiofiles.open(os.path.join(folder_name, f"{filename}.{ext}"), "wb") as f:
                    await f.write(content)


async def scrape_review_image(review_id: str, review_url:str) -> bool:
    async with async_playwright() as pw:
        # Create an instance of a Chromium browser
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})

        """
        Two cases to consider:
        - Whether there is an image section (Google map stored as list of button)
        - Whether there is an expand button (+k images)
        """
        start_time = time.time()
        try:

            print("Starting to scrape...")
            page = await context.new_page()
            await page.goto(review_url, timeout=0)

            await page.wait_for_selector(".KtCyie", timeout=0)
            
            image_section = await page.query_selector(".KtCyie")
            # First case: there is an image section
            if image_section:
                expand_button = await page.query_selector(".Tap5If")
                # Second case: there is an expand section
                if expand_button:
                    await page.click('div.Tap5If')
                # Doesn't matter if there is a expand button, we gonna crawl all 
                # images, but the expand button need to be clicked if it appear.
                images_container = await page.query_selector(".KtCyie")
                inner_html = await images_container.inner_html()
                soup = BeautifulSoup(inner_html, 'html.parser')
            
                # Find all buttons with the class Tya61d
                buttons = soup.find_all('button', class_='Tya61d')
                
                tasks = [process_button(button, review_id) for button in buttons]
                await asyncio.gather(*tasks)

                            
            await page.close()
            print(f"The time to scrape one vendor: {time.time() - start_time}")

        except Exception as e:
            await browser.close()
            print(f"An error occurred when setting up Playwright: {e}")
            return False    
        
        await browser.close()
        return True


async def process_button(button, review_id):
    style = button.get('style')
    if style:
        # Extract URL from the style attribute
        url_start = style.find("url(")
        image_url = style[url_start:]
        # Regex pattern to extract URL
        pattern = r'url\("([^"]+)"\)'

        # Find the URL using the regex pattern
        match = re.search(pattern, image_url)

        # Extracted URL
        if match:
            url = match.group(1)
            await save_image(review_id=review_id, filename=str(uuid.uuid4())[:8], url=url)

"""
# For testing purpose
async def main():
    vendor_data = read_csv("data.csv")
    async with async_playwright() as pw:
        # Create an instance of a Chromium browser
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})

        """"""
        Two cases to consider:
        - Whether there is an image section (Google map stored as list of button)
        - Whether there is an expand button (+k images)
        """"""
        start_time = time.time()
        try:
            for obj in vendor_data:
                vendor_id = obj["VendorID"]
                vendor_source = obj["LinkToSource"]
                print("Starting to scrape...")
                page = await context.new_page()
                await page.goto(vendor_source, timeout=0)

                await page.wait_for_selector(".KtCyie", timeout=0)
                
                image_section = await page.query_selector(".KtCyie")
                # First case: there is an image section
                if image_section:
                    expand_button = await page.query_selector(".Tap5If")
                    # Second case: there is an expand section
                    if expand_button:
                        await page.click('div.Tap5If')
                    # Doesn't matter if there is a expand button, we gonna crawl all 
                    # images, but the expand button need to be clicked if it appear.
                    images_container = await page.query_selector(".KtCyie")
                    inner_html = await images_container.inner_html()
                    soup = BeautifulSoup(inner_html, 'html.parser')
                
                    # Find all buttons with the class Tya61d
                    buttons = soup.find_all('button', class_='Tya61d')
                    
                    tasks = [process_button(button, vendor_id) for button in buttons]
                    await asyncio.gather(*tasks)

                                
                await page.close()
                break

            print(f"The time to scrape one vendor: {time.time() - start_time}")
        except Exception as e:
            print(f"An error occurred when setting up Playwright: {e}")
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
"""