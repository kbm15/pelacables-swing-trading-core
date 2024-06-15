import requests
from bs4 import BeautifulSoup

class ZacksScraper:
    def __init__(self, ticker):
        self.ticker = ticker
        self.url = f"https://www.zacks.com/stock/quote/{ticker}"
        self.soup = None
        self._get_soup()

    def _get_soup(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',  # Do Not Track Request Header
        }
        response = requests.get(self.url, headers=headers)
        if response.status_code == 200:
            self.soup = BeautifulSoup(response.content, 'html.parser')
        else:
            raise Exception(f"Failed to fetch data for ticker {self.ticker}, return code {response.status_code}")

    def get_composite_values(self):
        composite_values = {}
        composite_group = self.soup.find('div', class_='zr_rankbox composite_group')
        if composite_group:
            rank_view = composite_group.find('p', class_='rank_view')
            if rank_view:
                spans = rank_view.find_all('span', class_='composite_val')
                if len(spans) >= 4:
                    composite_values['Value'] = spans[0].text.strip()
                    composite_values['Growth'] = spans[1].text.strip()
                    composite_values['Momentum'] = spans[2].text.strip()
                    composite_values['VGM'] = spans[3].text.strip()
        return composite_values

    def get_key_earnings_data(self):
        earnings_data = {}
        key_earnings_section = self.soup.find('section', id='stock_key_earnings')
        if key_earnings_section:
            dls = key_earnings_section.find_all('dl', class_='abut_bottom')
            for dl in dls:
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd:
                    a_tag = dt.find('a')
                    key = a_tag.text.strip() if a_tag else dt.text.strip()
                    value = dd.text.strip()
                    earnings_data[key] = value
        return earnings_data

    def get_all_data(self):
        data = {
            'composite_values': self.get_composite_values(),
            'key_earnings_data': self.get_key_earnings_data()
        }
        return data

# Example usage
if __name__ == "__main__":
    scraper = ZacksScraper('NVDA')
    data = scraper.get_all_data()
    print(data)
