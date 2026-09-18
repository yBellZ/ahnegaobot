from dotenv import load_dotenv
import io
import os
import re
import json
import httpx
import yt_dlp
import random
import tempfile
import mimetypes
from bs4 import BeautifulSoup

load_dotenv()

COLETANEAS = {
    'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios': 'Coletânea de memes aleatórios',
    'https://www.ahnegao.com.br/t/coletanea-de-imagens-aleatorias': 'Coletânea de imagens aleatórias',
    'https://www.ahnegao.com.br/t/coletanea-de-videos-bestas': 'Coletânea de vídeos bestas',
    'https://www.ahnegao.com.br/c/videos': 'videos'
}

URL_LISTAGEM = list(COLETANEAS.keys())
COLETANEA_URL = random.choice(URL_LISTAGEM)
COLETANEA_NOME = COLETANEAS[COLETANEA_URL]

# Padrão genérico ahnegao.com.br/AAAA/MM/ em vez de mês fixo — não expira todo mês.
PADRAO_DATA_POST = re.compile(r"ahnegao\.com\.br/\d{4}/\d{2}/")
TERMO = 'ahnegao.com.br/'
PADRAO_POST = re.compile(r"\d+/\d+/.*")
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def buscar_links_de_posts(client: httpx.Client, url: str, termo: str) -> set[str]:
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    hrefs = (a.get("href") for a in soup.select(f'a[href*="{termo}"]'))

    EH_COLETANEA = 'https://www.ahnegao.com.br/c/videos' in COLETANEA_URL
    IGNORAR_COLETANEA = re.compile(r"\d+/\d+/coletanea.*")

    return {
        href for href in hrefs
        if href.startswith("http")
        and "whatsapp://" not in href
        and "#comments" not in href
        and not (EH_COLETANEA and IGNORAR_COLETANEA.search(href))
        and PADRAO_DATA_POST.search(href)
        and PADRAO_POST.search(href)
    }


def titulo_post(client: httpx.Client, url_post: str):
    resp = client.get(url_post)
    soup = BeautifulSoup(resp.text, 'html.parser')

    titulo = soup.find('h1', class_='entry-title')

    if titulo:
        return titulo.text.strip()

def buscar_midias_de_meme(client: httpx.Client, url_post: str) -> list[str]:
    resp = client.get(url_post)
    soup = BeautifulSoup(resp.text, 'html.parser')

    midias = []

    # Vídeos do YouTube incorporados
    for elem in soup.select('.rll-youtube-player[data-src]'):
        src = elem.get('data-src')
        if src:
            midias.append(src)

    # Imagens de meme / imagem aleatória
    for img in soup.find_all('img', src=True):
        src = img.get('src')
        if src and re.search(r"/uploads/\d{4}/\d{2}/(meme|imgaleat|pec)", src):
            midias.append(src)

    return list(dict.fromkeys(midias))


def baixar_video(url_video: str) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        caminho_temp = os.path.join(tmpdir, "video.mp4")
        ydl_opts = {
            "quiet": True,
            "format": (
                "bestvideo[filesize<18M][height<=1080]+bestaudio"
                "/bestvideo[height<=480]+bestaudio"
                "/best[height<=480]"
                "/bestvideo+bestaudio"
                "/best"
            ),
            "merge_output_format": "mp4",
            "outtmpl": caminho_temp,
            "remote_components": ["ejs:github"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_video])

        with open(caminho_temp, "rb") as f:
            video_bytes = f.read()

    return video_bytes, "video.mp4"


def processar_video(url_video: str) -> tuple[io.BytesIO, str]:
    video_bytes, video_nome = baixar_video(url_video)
    return io.BytesIO(video_bytes), video_nome


def montar_payload(url_post: str, midia_url: str, titulo: str) -> dict:
    return {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "components": [
                    {
                        "type": 10,
                        "content": f"### Ah Negão!\n[{titulo}]({url_post})"
                    },
                    {
                        "type": 12,
                        "items": [
                            {
                                "media": {
                                    "url": midia_url
                                }
                            }
                        ]
                    },
                    {
                        "type": 10,
                        "content": "-# [GitHub do bot Ah Negão!](https://github.com/yBellZ/ahnegaobot)"
                    }
                ],
                "accent_color": 8927205
            }
        ]
    }


def enviar_content_discord(
    client: httpx.Client,
    url_post: str,
    midia_url: str,
    midia_bytes: io.BytesIO | None = None,
    midia_nome: str | None = None,
):
    titulo = titulo_post(client, url_post)
    payload = montar_payload(url_post, midia_url, titulo)

    if midia_bytes is not None:
        midia_bytes.seek(0)
        mime_type, _ = mimetypes.guess_type(midia_nome)
        mime_type = mime_type or "application/octet-stream"
        arquivos = {"files[0]": (midia_nome, midia_bytes, mime_type)}
        data = {"payload_json": json.dumps(payload)}
        resp = client.post(WEBHOOK_URL, data=data, files=arquivos)
    else:
        resp = client.post(WEBHOOK_URL, json=payload)

    if resp.status_code >= 400:
        print(resp.status_code, resp.text)

    resp.raise_for_status()


def main():
    timeout = httpx.Timeout(30.0, connect=10.0)
    with httpx.Client(http2=True, timeout=timeout) as client:
        links_posts = buscar_links_de_posts(client, COLETANEA_URL, TERMO)
        post_aleatorio = random.choice(list(links_posts))
        midias = buscar_midias_de_meme(client, post_aleatorio)

        if not post_aleatorio or not midias:
            print("Nenhum post com mídia encontrada nessa coletânea")
            return

        midia_aleatoria = random.choice(midias)

        if 'youtube.com' in midia_aleatoria:
            midia_bytes, midia_nome = processar_video(midia_aleatoria)
            enviar_content_discord(
                client, post_aleatorio,
                midia_url=f"attachment://{midia_nome}",
                midia_bytes=midia_bytes,
                midia_nome=midia_nome
            )
        else:
            enviar_content_discord(
                client, post_aleatorio,
                midia_url=midia_aleatoria
            )


        print("Link dos posts:")
        for i in links_posts:
            print("|— " + i)
        
        print("\nPost aleatório: - " + post_aleatorio)
        for i in midias:
            print("|— " + i)

        print("\nMídia aleatória: " + midia_aleatoria)

        if 'youtube.com' in midia_aleatoria:
            tamanho_bytes = midia_bytes.getbuffer().nbytes
            tamanho_mb = tamanho_bytes / (1024 * 1024)
            print(f"Tamanho vídeo: {tamanho_mb:.2f} MB")


if __name__ == "__main__":
    main()