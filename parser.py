import httpx
import re
from bs4 import BeautifulSoup

link = 'https://www.ahnegao.com.br/t/coletanea-de-memes-aleatorios'
termo = 'coletanea'

with httpx.Client(http2=True) as client:
    resp = client.get(link)

soup = BeautifulSoup(resp.text, 'html.parser')
todos_links = soup.select(f'a[href*="{termo}"]')

links_filtrados = [
    a.get("href") for a in todos_links
    if a.get("href").startswith("http")
    and "whatsapp://" not in a.get("href")
    and "#comments" not in a.get("href")
]

padrao = re.compile(r"\d+/\d+/coletanea")

links_filtrados = [link for link in links_filtrados if padrao.search(link)]

print(dict.fromkeys(links_filtrados))

# links_filtrados = list(dict.fromkeys(links_filtrados))

# for l in links_filtrados:
#     print(l)