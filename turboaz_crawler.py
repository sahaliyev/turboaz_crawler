import pdb
import traceback

import requests
from bs4 import BeautifulSoup

from mongo_connection import MongoConnection
from datetime import datetime
from user_agents import user_agents
import random


class Turbo:
    def __init__(self):
        self.client = MongoConnection.get_connected()
        self.db = self.client.analitika
        self.collection = self.db.turbo
        self.base_url = 'https://turbo.az'

    @staticmethod
    def get_beautiful_soup(link):
        headers = {'user-agent': random.choice(user_agents)}
        response = requests.get(link, headers=headers)
        if response.status_code != 200:
            raise Exception(f'Request error. {response.status_code} {response.text}')
        response.encoding = "utf8"
        html = response.text
        bs = BeautifulSoup(html, 'lxml')
        return bs

    def get_partial_parsed_items(self):
        res = self.collection.find({'status': 0})
        return res

    def update_collection(self, data):
        item_id = data['_id']
        query = {"_id": item_id}
        new_values = {"$set": data}
        self.collection.update_one(query, new_values)

    def insert_to_collection(self, data):
        """
        Inserting single item into mongodb.
        """
        try:
            self.collection.insert_one(data)
            print("Inserted")
        except Exception as e:
            url = data['item_url']
            item_id = data['_id']
            info = f"Item with {item_id} already exists! url: {url}"
            print(info)
            with open('turbo_errors.txt', 'a') as file:
                print(info, file=file)

    def bs_and_next_url(self, url):
        bs = self.get_beautiful_soup(url)
        pagination = bs.find('nav', class_='pagination')
        current = pagination.find('span', class_='current')
        next_item = current.find_next_sibling('span', class_='page')
        if next_item:
            link = next_item.a['href']
            link = self.base_url + link
            return bs, link
        return bs, None

    def parse_inner(self, url):
        try:
            bs = self.get_beautiful_soup(url)
            car = {}
            container = bs.find('div', class_='product')

            # Below code takes images
            slider = container.find('div', class_='product-photos')
            images_list = []
            if slider:
                images_container = slider.find('div', class_='product-photos-thumbnails')
                images = images_container.find_all('a')
                for image in images:
                    src = image['href']
                    images_list.append(src)
            car['inner_images'] = images_list

            # Below code takes statistics such as view count, update time and product id
            statistics = container.find('div', class_='product-statistics')
            items = statistics.find_all('p')
            for item in items:
                label = item.find('label')
                if label.has_attr('for'):
                    name = label['for']
                    label.decompose()
                    car[name] = item.text.replace(':', '').strip()

            # product-properties all info about product
            product_properties = container.find('ul', class_='product-properties')
            items = product_properties.find_all('li')
            for item in items:
                name = item.find('label')
                if name:
                    ignore_list = ['Qiymət', 'Şəhər']
                    name = name.text.strip()
                    if name in ignore_list:
                        continue
                    value = item.find('div', class_='product-properties-value').text.strip()
                    car[name] = value

            # Barter
            barter = product_properties.find('li', class_='product-properties-i_barter')
            if barter:
                car['barter'] = 'Yes'

            # extra info
            extras = []
            product_extras = container.find('div', class_='product-extras')
            if product_extras:
                items = product_extras.find_all('p', class_='product-extras-i')
                for item in items:
                    value = item.text.strip()
                    extras.append(value)
                car['extras'] = extras

            # description
            text = ""
            desc = container.find('h2', class_='product-text')
            while desc:
                desc = desc.find_next_sibling('p')
                if desc:
                    text += desc.text.strip()
            car['description'] = text

            # seller contact (person)
            seller = container.find('div', class_='seller-contacts')
            if seller:
                seller_name = seller.find('div', class_='seller-name').text.strip()
                phones = []
                phones_container = container.find('div', class_='seller-phone')
                items = phones_container.find_all('a', class_='phone')
                for item in items:
                    phone = item.text.strip()
                    phones.append(phone)
                car['seller'] = seller_name
                car['phones'] = phones
            # seller contact (shop)
            seller_shop = container.find('div', class_='shop-contact')
            if seller_shop:
                seller_name = seller_shop.find('a', class_='shop-contact--shop-name').text.strip()
                phones = []
                items = seller_shop.find_all('div', class_='shop-contact--phones-i')
                for item in items:
                    item = item.find('a', class_='shop-contact--phones-number')
                    phone = item.text.strip()
                    phones.append(phone)
                car['seller'] = seller_name
                car['phones'] = phones
            car['status'] = 1  # when inner page parsed change status to 1, so that you did not send request to it

            return car

        except Exception as e:
            info = {'exception_info': f"{type(e)}:{e.args}",
                    'traceback_info': str(traceback.format_exc()),
                    'date': datetime.now()}
            with open('turbo_errors.txt', 'a') as file:
                print(info, file=file)

    def extract_item(self, items):
        car = {}
        for item in items:
            try:
                url = item.a['href']
                item_id = url.replace('/autos/', '').split('-')[0]
                car['_id'] = int(item_id)
                car['status'] = 0  # means inner page is not parsed yet.
                car['item_url'] = self.base_url + url
                print(car['item_url'])
                outer_image = item.find('img')
                if outer_image:
                    car['main_image'] = outer_image['src']
                price_container = item.find('div', class_='product-price')
                currency_span = price_container.find('span')
                car['currency'] = currency_span.text.strip()
                currency_span.decompose()
                car['price'] = price_container.text.strip()
                car['name'] = item.find('p', class_='products-name').text.strip()
                place_date = item.find('div', class_='products-bottom').text.strip()
                place, date = place_date.split(',')  # date still has empty space at the beginning
                car['city'] = place
                car['posted_date'] = date.strip()  # this solves that problem
                car['parse_date'] = datetime.now().strftime("%d.%m.%Y %H:%M")
                self.insert_to_collection(car)

            except Exception as e:
                link = car.get('item_url', 'N/A')
                info = {'link': link, 'exception_info': f"{type(e)}:{e.args}",
                        'traceback_info': str(traceback.format_exc()),
                        'date': datetime.now()}
                with open('turbo_errors.txt', 'a') as file:
                    print(info, file=file)

    @staticmethod
    def parse_turbo_az(bs):
        titles = bs.find_all('p', class_='section-title_name')
        title_parent = None
        for title in titles:
            if title.text.strip() == 'ELANLAR':
                title_parent = title.parent
        if title_parent:
            items_container = title_parent.find_next_sibling('div', class_='products')
            items = items_container.find_all('div', class_='products-i')
            return items

    def parse_outer(self):
        url = 'https://turbo.az/autos?page=1'  # starting point
        while url:  # util there is next page url this will work
            print(url)  # printing out current pagination page
            bs, url = self.bs_and_next_url(url)  #
            items = self.parse_turbo_az(bs)
            self.extract_item(items)

    def parse_inner_main(self):
        items = self.get_partial_parsed_items()
        for item in items:
            url = item['item_url']
            res = self.parse_inner(url)
            res['view'] = res.pop('ad_hits')  # rename dict key
            res['_id'] = int(res.pop('ad_id'))  # rename dict key
            res['update_date'] = res.pop('ad_updated_at')  # rename dict key
            item.update(res)
            self.update_collection(item)

    def main(self):
        """
        You can call two functiona.
        First one is parse_outer() function that walks on  full site and collects some data.
        You can see what they are by looking at extract_items() since it is called by parse_outer().

        Second one is parse_inner_main() function that parse items that you are already collected and stored somewhere.
        In my case, I stored data in mongodb for flexibility.

        It is better for your understanding not to use these function at the same time.
        """
        # self.parse_outer()
        self.parse_inner_main()


if __name__ == '__main__':
    Turbo().parse_inner_main()
