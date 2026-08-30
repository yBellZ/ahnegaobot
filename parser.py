from dotenv import load_dotenv
import httpx
import re
import random
import os
from bs4 import BeautifulSoup

load_dotenv()

COLETANEAS = {
    'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios': 'Coletânea de memes aleatórios',
    'https://www.ahnegao.com.br/t/coletanea-de-imagens-aleatorias': 'Coletânea de imagens aleatórias',
    'https://www.ahnegao.com.br/t/coletanea-de-memes-peculiares': 'Coletânea de memes peculiares',
}

URL_LISTAGEM = list(COLETANEAS.keys())
COLETANEA_URL = random.choice(URL_LISTAGEM)
COLETANEA_NOME = COLETANEAS[COLETANEA_URL]

TERMO = 'coletanea'
PADRAO_POST = re.compile(r"\d+/\d+/coletanea")
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


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
        if re.search(r"/uploads/\d{4}/\d{2}/(meme|imgaleat|pec)", img.get("src"))
    ]


def montar_payload(url_imagem: str, url_post: str) -> dict:
    return {
        "embeds": [
            {
                "title": "Meme do dia",
                "image": {"url": url_imagem},
                "footer": {"text": f"Ahnegao.com.br — {COLETANEA_NOME}"},
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
        links_posts = buscar_links_de_posts(client, COLETANEA_URL, TERMO)
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