import httpx
import re
import random
from bs4 import BeautifulSoup

URL_LISTAGEM = 'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios'
TERMO = 'coletanea'
PADRAO_POST = re.compile(r"\d+/\d+/coletanea")

with httpx.Client(http2=True) as client:
    resp = client.get(URL_LISTAGEM)
    soup = BeautifulSoup(resp.text, 'html.parser')

    hrefs = (a.get("href") for a in soup.select(f'a[href*="{TERMO}"]'))

    links_posts = {
        href for href in hrefs
        if href.startswith("http")
        and "whatsapp://" not in href
        and PADRAO_POST.search(href)
    }

    coletanea_aleatoria = random.choice(list(links_posts))

    resp = client.get(coletanea_aleatoria)
    soup = BeautifulSoup(resp.text, 'html.parser')

    imagens_meme = [
        img.get("src") for img in soup.find_all("img", src=True)
        if "meme" in img.get("src")
    ]

for src in imagens_meme:
    print(src)