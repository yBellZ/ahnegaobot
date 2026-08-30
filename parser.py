import httpx
import re
import random
from bs4 import BeautifulSoup

URL_LISTAGEM = 'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios'
TERMO = 'coletanea'
PADRAO_POST = re.compile(r"\d+/\d+/coletanea")


def buscar_links_de_posts(client: httpx.Client, url: str, termo: str) -> set[str]:
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    hrefs = (a.get("href") for a in soup.select(f'a[href*="{termo}"]'))

    return {
        href for href in hrefs
        if href.startswith("http")
        and "whatsapp://" not in href
        and PADRAO_POST.search(href)
    }


def buscar_imagens_de_meme(client: httpx.Client, url_post: str) -> list[str]:
    resp = client.get(url_post)
    soup = BeautifulSoup(resp.text, 'html.parser')

    return [
        img.get("src") for img in soup.find_all("img", src=True)
        if "meme" in img.get("src")
    ]


def main():
    with httpx.Client(http2=True) as client:
        links_posts = buscar_links_de_posts(client, URL_LISTAGEM, TERMO)
        post_aleatorio = random.choice(list(links_posts))
        imagens = buscar_imagens_de_meme(client, post_aleatorio)

    for src in imagens:
        print(src)


if __name__ == "__main__":
    main()