import httpx
import re
import random
from bs4 import BeautifulSoup

URL_LISTAGEM = 'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios'
TERMO = 'coletanea'
PADRAO_POST = re.compile(r"\d+/\d+/coletanea")
WEBHOOK_URL = "https://discord.com/api/webhooks/1543569018601078904/aa-T5wxbEHevg9qK5NENqdD8Op9N0RE2xJGNs4TIfnHK9HZgUxr5tltossJ3XCMm7dkF"


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


def montar_payload(url_imagem: str, url_post: str) -> dict:
    return {
        "embeds": [
            {
                "image": {"url": url_imagem},
                "footer": {"text": "Meme pego em Ahnegao.com.br"},
                "color": 8927205
            }
        ]
    }


def enviar_imagem_discord(client: httpx.Client, url_imagem: str, url_post: str):
    payload = montar_payload(url_imagem, url_post)
    resp = client.post(WEBHOOK_URL, json=payload)

    if resp.status_code >= 400:
        print(resp.status_code, resp.text)

    resp.raise_for_status()


def main():
    with httpx.Client(http2=True) as client:
        links_posts = buscar_links_de_posts(client, URL_LISTAGEM, TERMO)
        post_aleatorio = random.choice(list(links_posts))
        imagens = buscar_imagens_de_meme(client, post_aleatorio)

        if not imagens:
            print("Nenhuma imagem encontrada nesse post.")
            return

        imagem_aleatoria = random.choice(imagens)
        print(imagem_aleatoria)

        enviar_imagem_discord(client, imagem_aleatoria, post_aleatorio)


if __name__ == "__main__":
    main()