import requests
from bs4 import BeautifulSoup as BS
from PIL import Image
import os, json
from io import BytesIO
def get_tarot_img(idx):
    idx = 150
    os.mkdir(str(idx))
    url = f'https://www.tarot5.cn/photo/tarot/tarot_{idx}_%d.htm'
    img_urls = []
    for page in range(1, 5):
        page = BS(requests.get(url%page).text, 'lxml')
        img_urls += [p.get('src') for p in page.find_all('img')]
    for img_url in img_urls:
        im = Image.open(BytesIO(requests.get(img_url).content))
        im_name = os.path.join(f'./{idx}/', os.path.basename(img_url))
        im.save(im_name)
def gen_json():
    result = {}
    for f_name in os.listdir('./'):
        if os.path.isfile(f_name): continue
        files = [os.path.join(f_name, f) for f in sorted(os.listdir(f_name))]
        result[f_name] = files
    json.dump(result, open('tarot.json', 'w'))
if __name__ == '__main__':
    gen_json()
    # get_tarot_img(170)