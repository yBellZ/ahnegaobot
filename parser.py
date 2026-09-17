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
    'https://www.ahnegao.com.br/t/coletanea-de-videos-bestas': 'Coletânea de vídeos bestas'
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
        and "#comments" not in href
        and PADRAO_POST.search(href)
    }

# <div data-id="kqoZ6wnKCTU" data-query="" data-src="https://www.youtube.com/embed/kqoZ6wnKCTU"><img

def buscar_midias_de_meme(client: httpx.Client, url_post: str) -> list[str]:
    resp = client.get(url_post)
    soup = BeautifulSoup(resp.text, 'html.parser')

    if 'Coletânea de vídeos bestas' in COLETANEA_NOME:
        return [
            elem.get("data-src")
            for elem in soup.find_all(attrs={"data-src": True})
            if elem.get("data-src")
        ]

    return [
        img.get("src") for img in soup.find_all("img", src=True)
        if re.search(r"/uploads/\d{4}/\d{2}/(meme|imgaleat|pec)", img.get("src"))
    ]


def baixar_video(url_video: str) -> tuple[bytes, str]:
    """Baixa o vídeo direto pra memória, sem salvar em disco (fora do TemporaryDirectory)."""
    with tempfile.TemporaryDirectory() as tmpdir:  # some sozinho ao sair do bloco
        caminho_temp = os.path.join(tmpdir, "video.mp4")
        ydl_opts = {
            "quiet": True,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": caminho_temp,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_video])

        with open(caminho_temp, "rb") as f:
            video_bytes = f.read()

    return video_bytes, "video.mp4"


def processar_video(url_video: str) -> tuple[io.BytesIO, str]:
    video_bytes, video_nome = baixar_video(url_video)
    return io.BytesIO(video_bytes), video_nome


def montar_payload(url_post: str, midia_url: str) -> dict:
    """
    url_post: link do post no ahnegao.com.br (vai só no rodapé do embed).
    midia_url: URL final da mídia a exibir — já pronta pro Media Gallery,
               seja um link externo (imagem) ou "attachment://<nome>" (vídeo).
    """
    return {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "components": [
                    {"type": 12, "items": [{"media": {"url": midia_url}}]},
                    {
                        "type": 10,
                        "content": f"-# [Ah Negão! — {COLETANEA_NOME}]({url_post})"
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
    payload = montar_payload(url_post, midia_url)

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
    with httpx.Client(http2=True) as client:
        links_posts = buscar_links_de_posts(client, COLETANEA_URL, TERMO)
        post_aleatorio = random.choice(list(links_posts))
        midias = buscar_midias_de_meme(client, post_aleatorio)

        if not midias:
            print("Nenhum conteúdo encontrado nesse post.")
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

        print(midia_aleatoria)
        print(post_aleatorio)

if __name__ == "__main__":
    main()