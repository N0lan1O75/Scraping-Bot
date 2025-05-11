import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import cssutils
import os
from datetime import datetime
import socket
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def clean_text(text):
    return text.strip().replace('\n', ' ') if text else ''

def extract_domain_info(url):
    try:
        domain = url.split("//")[-1].split("/")[0]
        ip = socket.gethostbyname(domain)
        return domain, ip
    except Exception as e:
        return "Inconnu", f"Erreur IP: {e}"

def scrape_page(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')

    title = clean_text(soup.title.string) if soup.title else "Aucun titre"
    h1_tags = [clean_text(h.text) for h in soup.find_all('h1')]
    h2_tags = [clean_text(h.text) for h in soup.find_all('h2')]
    paragraphs = [clean_text(p.text) for p in soup.find_all('p')][:15]
    links = [(clean_text(a.text), a['href']) for a in soup.find_all('a', href=True)]
    images = [(img.get('alt', ''), img['src']) for img in soup.find_all('img', src=True)]
    stylesheets = [link['href'] for link in soup.find_all('link', rel='stylesheet') if 'href' in link.attrs]
    scripts = [script['src'] for script in soup.find_all('script', src=True)]

    colors = set()
    for style_tag in soup.find_all('style'):
        try:
            css = cssutils.parseString(style_tag.string)
            for rule in css:
                if rule.type == rule.STYLE_RULE:
                    for property in rule.style:
                        if 'color' in property.name:
                            colors.add(property.value)
        except Exception:
            continue

    metas = {
        (meta.get('name') or meta.get('property')): meta.get('content')
        for meta in soup.find_all('meta') if meta.get('content')
    }

    domain, ip = extract_domain_info(url)

    return {
        "title": title,
        "h1": h1_tags,
        "h2": h2_tags,
        "paragraphs": paragraphs,
        "links": links,
        "images": images,
        "stylesheets": stylesheets,
        "scripts": scripts,
        "colors": list(colors),
        "metas": metas,
        "domain": domain,
        "ip": ip
    }

def save_to_txt(data, filename):
    os.makedirs("scrapes", exist_ok=True)
    filepath = os.path.join("scrapes", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Titre : {data['title']}\n")
        f.write(f"🌐 Domaine : {data['domain']} — IP : {data['ip']}\n\n")

        f.write("## 🟦 H1 :\n" + "\n".join(f"- {h}" for h in data["h1"]) + "\n\n")
        f.write("## 🔷 H2 :\n" + "\n".join(f"- {h}" for h in data["h2"]) + "\n\n")
        f.write("## 📄 Paragraphes :\n" + "\n".join(f"- {p}" for p in data["paragraphs"]) + "\n\n")
        f.write("## 🔗 Liens :\n" + "\n".join(f"- {text} → {href}" for text, href in data["links"]) + "\n\n")
        f.write("## 🖼️ Images :\n" + "\n".join(f"- {alt or '[aucun alt]'} → {src}" for alt, src in data["images"]) + "\n\n")
        f.write("## 🎨 Couleurs CSS :\n" + "\n".join(f"- {c}" for c in data["colors"]) + "\n\n")
        f.write("## 📜 Scripts :\n" + "\n".join(f"- {s}" for s in data["scripts"]) + "\n\n")
        f.write("## 📂 Stylesheets :\n" + "\n".join(f"- {s}" for s in data["stylesheets"]) + "\n\n")
        f.write("## 🧩 Metas :\n" + "\n".join(f"- {k}: {v}" for k, v in data["metas"].items()) + "\n\n")

    return filepath

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot prêt : {bot.user}")

@tree.command(name="scrape_url", description="Scrape tout d'un site web")
@app_commands.describe(url="L'URL du site à analyser")
async def scrape_url(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)

    try:
        data = scrape_page(url)
        filename = f"scrape_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        filepath = save_to_txt(data, filename)

        preview = (
            f"**📰 Titre :** {data['title']}\n"
            f"🌐 Domaine : `{data['domain']}`\n"
            f"🔹 H1: {len(data['h1'])} | 🔗 Liens: {len(data['links'])} | 🎨 Couleurs: {len(data['colors'])}\n"
        )

        await interaction.followup.send(content=preview, file=discord.File(filepath))

    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors du scraping : `{e}`")

bot.run(TOKEN)
