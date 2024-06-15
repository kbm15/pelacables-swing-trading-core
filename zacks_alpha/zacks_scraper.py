import requests
from bs4 import BeautifulSoup
import time

class ZacksScraper:
    def __init__(self, ticker):
        self.ticker = ticker
        self.url1 = f"https://www.zacks.com/stock/quote/{ticker}"
        self.url2 = f"https://www.zacks.com/stock/research/{ticker}/price-target-stock-forecast"
        self.soup1 = None
        self.soup2 = None
        self._get_soups()

    def _get_soups(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
        }
        for _ in range(3):  # Retry up to 3 times
            response1 = requests.get(self.url1, headers=headers, allow_redirects=True)
            response2 = requests.get(self.url2, headers=headers, allow_redirects=True)
            if response1.status_code == 200 and response2.status_code == 200:
                self.soup1 = BeautifulSoup(response1.content, 'html.parser')
                self.soup2 = BeautifulSoup(response2.content, 'html.parser')
                return
            elif response1.status_code == 500 or response2.status_code == 500:
                time.sleep(2)  # Wait for 2 seconds before retrying
        raise Exception(f"Failed to fetch data for ticker {self.ticker}, Status Codes: {response1.status_code}, {response2.status_code}")

    def check_escaped_input(self, text):
        # Remove trailing escape characters such as '\n', '\r' and whitespace
        cleaned_text = text.strip().splitlines()[0].strip()
        return cleaned_text

    def get_composite_values(self):
        composite_values = {}
        composite_group = self.soup1.find('div', class_='zr_rankbox composite_group')
        if composite_group:
            rank_view = composite_group.find('p', class_='rank_view')
            if rank_view:
                spans = rank_view.find_all('span', class_='composite_val')
                if len(spans) >= 4:
                    composite_values['Value'] = self.check_escaped_input(spans[0].text)
                    composite_values['Growth'] = self.check_escaped_input(spans[1].text)
                    composite_values['Momentum'] = self.check_escaped_input(spans[2].text)
                    composite_values['VGM'] = self.check_escaped_input(spans[3].text)
        return composite_values

    def get_key_earnings_data(self):
        earnings_data = {}
        key_earnings_section = self.soup1.find('section', id='stock_key_earnings')
        if key_earnings_section:
            dls = key_earnings_section.find_all('dl', class_='abut_bottom')
            for dl in dls:
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd:
                    a_tag = dt.find('a')
                    key = self.check_escaped_input(a_tag.text.strip()) if a_tag else self.check_escaped_input(dt.text.strip())
                    value = self.check_escaped_input(dd.text.strip())
                    earnings_data[key] = value
        return earnings_data

    def get_key_expected_earnings(self):
        expected_earnings = {}
        earnings_module = self.soup2.find('div', class_='key-expected-earnings-data-module price-targets')
        if earnings_module:
            thead = earnings_module.find('thead')
            tbody = earnings_module.find('tbody')
            if thead:
                headers = [self.check_escaped_input(th.text.strip()) for th in thead.find_all('th', scope='col')]
                if tbody:
                    values = [self.check_escaped_input(td.text.strip()) for td in tbody.find_all(['th', 'td'], class_='align_center')]
                    if len(headers) == len(values):
                        expected_earnings = dict(zip(headers, values))
        return expected_earnings

    def get_all_data(self):
        data = {
            'composite_values': self.get_composite_values(),
            'key_earnings_data': self.get_key_earnings_data(),
            'key_expected_earnings': self.get_key_expected_earnings()
        }
        return data

# Example usage
if __name__ == "__main__":
    scraper = ZacksScraper('NVDA')
    data = scraper.get_all_data()
    print(data)
