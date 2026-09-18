"""
Kauar Fish & Plant Scraper (v2)
================================

Extrai a ficha técnica de peixes, camarões e plantas vendidos em
kauar.com.br para alimentar uma base de conhecimento (RAG) sobre
parâmetros e compatibilidade de aquário.

CORREÇÃO NA V2
--------------
A Kauar usa pelo menos DOIS formatos de descrição de produto:
  - Template A (lista): "- **Nome popular:** Tetra Blue Devil"
  - Template B (prosa): "**Origem:** o peixe Abelhinha é..." com pH e
    temperatura embutidos numa frase só, ex: "mantenha a temperatura por
    volta de 26ºC e pH 7 a 8.5"
A v1 exigia achar o rótulo exato "Nome científico:" pra aceitar a página,
o que descartava todo o Template B. A v2:
  1. Detecta página de produto pela presença de "Ref:" (existe em toda
     página de produto da loja, incluindo peixes, plantas e substratos).
  2. Extrai nome popular / nome científico a partir do título da página
     (padrão observado: "Nome Popular | tamanho | Nome Científico").
  3. Extrai os demais campos varrendo linha a linha (funciona nos dois
     templates, já que cada rótulo aparece dentro de uma linha/parágrafo).
  4. Tem um fallback específico para pH e temperatura quando vêm
     embutidos em frase corrida (Template B), buscando os números perto
     das palavras "pH" e "temperatura" em todo o texto.

COMO FUNCIONA
-------------
1. Descoberta de URLs de produtos:
   - Tenta primeiro o sitemap.xml (padrão em lojas Tray Commerce).
   - Se não encontrar, faz fallback varrendo as páginas de categoria
     (peixes, camarões e agora também plantas/aquapaisagismo).
2. Para cada URL, baixa o HTML e extrai os campos da ficha técnica.
3. Salva em kauar_peixes.json (estruturado) e kauar_peixes.csv (planilha).

USO
---
    pip install requests beautifulsoup4 lxml
    python kauar_scraper.py --limit 10      # teste rápido
    python kauar_scraper.py --delay 1.5     # roda tudo, delay maior

AVISOS
------
- Delay entre requisições pra não sobrecarregar o servidor.
- Confira https://www.kauar.com.br/robots.txt e use os dados para fins
  pessoais/educacionais (seu RAG), não para republicar o catálogo.
- Extração "best effort": revise o CSV antes de usar em produção — nem
  toda página segue exatamente os padrões mapeados aqui.
"""

import argparse
import csv
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict, field
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kauar.com.br"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AquaRAG-Bot/1.0; "
        "+educational-research-fish-compatibility-dataset)"
    )
}

# Categorias de peixes/camarões + plantas/aquapaisagismo (para o fallback
# de descoberta por categoria, caso o sitemap falhe)
CATEGORY_URLS = [
    "/agua-doce/asiaticos",
    "/agua-doce/barbos-e-danios",
    "/peixes-agua-doce/botias",
    "/peixes-agua-doce/bettas",
    "/agua-doce/camaroes",
    "/agua-doce/cascudos-e-coridoras",
    "/agua-doce/ciclideos-africanos/aulonocaras",
    "/agua-doce/ciclideos-africanos/mbunas",
    "/peixes-agua-doce/ciclideos-africanos/malawi-haps",
    "/agua-doce/ciclideos-africanos/tanganika",
    "/peixes-agua-doce/ciclideos-africanos/lago-vitoria",
    "/agua-doce/ciclideos-anoes",
    "/agua-doce/ciclideos-americanos/discos-selvagens",
    "/agua-doce/ciclideos-americanos/bandeiras",
    "/agua-doce/comedores-de-algas",
    "/agua-doce/jumbos",
    "/peixes-agua-doce/killifish",
    "/agua-doce/kinguios",
    "/agua-doce/poecilideos",
    "/agua-doce/tetras-e-rasboras",
    "/peixes-de-agua-doce/peixes-para-lagos",
    "/peixes-de-agua-doce/platis-espadas-e-molinesias",
    # Plantas / aquapaisagismo (adicionado a pedido)
    "/aquapaisagismo",
    "/aquascaping/botanicos",
    "/aquascaping/substratos",
]

# Fragmentos de URL que NÃO queremos (páginas institucionais, ração,
# equipamentos, cuidados com água, arte). Note que aquapaisagismo /
# aquascaping NÃO estão mais aqui, pois agora queremos plantas também.
EXCLUDE_URL_FRAGMENTS = [
    "/blog", "/racoes", "/equipamentos", "/cuidados-com-a-agua",
    "/arte", "/lifestyle",
    "/my-account", "/cadastro", "/contato", "/central-do-cliente",
    "/trocasedevolucoes", "/segurancaeprivacidade", "/trabalheconosco",
    "/conheca-a-kauar", "/depoimentos-de-clientes", "/frete",
    "/compra-de-peixes-online-e-entrega", "/peixes-com-garantia-de-vida",
    "/servicos-kauar-lab", "/lagoseaquarios", "/cardume",
]

# Rótulos como aparecem nas fichas técnicas (peixes e plantas).
# Cada chave pode ter múltiplas variações de rótulo observadas no site.
FIELD_LABELS = {
    "nome_cientifico": ["Nome científico", "Nome cientifico"],
    "ordem": ["Ordem"],
    "familia": ["Família", "Familia"],
    "origem": ["Origem"],
    "alimentacao": ["Alimentação", "Alimentacao"],
    "sociabilidade": ["Sociabilidade", "Comportamento"],
    "ph": ["PH", "pH"],
    "temperatura_ideal": ["Temperatura ideal", "Temperatura"],
    "expectativa_vida": ["Expectativa de vida"],
    "manutencao": ["Manutenção", "Manutencao", "Dificuldade de cultivo", "Dificuldade"],
    "tamanho_adulto": ["Tamanho adulto"],
    # Campos específicos de plantas/aquapaisagismo
    "iluminacao": ["Iluminação", "Iluminacao"],
    "co2": ["CO2", "Gás carbônico", "Gas carbonico"],
    "crescimento": ["Crescimento", "Taxa de crescimento"],
    "posicionamento": ["Posicionamento", "Posição no aquário"],
}

# Segunda palavra pode vir maiúscula ou minúscula: a Kauar às vezes
# escreve "Microgeophagus Ramirezi" (fora do padrão binomial científico
# tradicional, que seria "Microgeophagus ramirezi", mas é o que o site usa)
BINOMIAL_RE = re.compile(r"^[A-ZÀ-Ú][a-zà-ÿ]+\s+[A-Za-zà-ÿ]{2,}(\s*\(.*\))?$")


@dataclass
class Fish:
    url: str
    tipo: Optional[str] = None  # "peixe/camarão" ou "planta" (heurística)
    nome_popular: Optional[str] = None
    nome_cientifico: Optional[str] = None
    ordem: Optional[str] = None
    familia: Optional[str] = None
    origem: Optional[str] = None
    alimentacao: Optional[str] = None
    sociabilidade: Optional[str] = None
    ph: Optional[str] = None
    ph_min: Optional[float] = None
    ph_max: Optional[float] = None
    temperatura_ideal: Optional[str] = None
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    expectativa_vida: Optional[str] = None
    manutencao: Optional[str] = None
    tamanho_adulto: Optional[str] = None
    iluminacao: Optional[str] = None
    co2: Optional[str] = None
    crescimento: Optional[str] = None
    posicionamento: Optional[str] = None
    companheiros_sugeridos: list = field(default_factory=list)
    imagem_principal_url: Optional[str] = None
    imagens_galeria: list = field(default_factory=list)
    raw_description_snippet: Optional[str] = None


def get_soup(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        print(f"  [erro] {url} -> {e}")
        return None


def discover_urls_from_sitemap(session: requests.Session) -> list:
    urls = []
    try:
        resp = session.get(SITEMAP_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        sub_sitemaps = [loc.text for loc in root.findall(".//sm:sitemap/sm:loc", ns)]
        loc_nodes = root.findall(".//sm:url/sm:loc", ns)

        if sub_sitemaps:
            for sm_url in sub_sitemaps:
                sub_resp = session.get(sm_url, headers=HEADERS, timeout=20)
                sub_root = ET.fromstring(sub_resp.content)
                for loc in sub_root.findall(".//sm:url/sm:loc", ns):
                    urls.append(loc.text)
                time.sleep(0.3)
        else:
            urls = [loc.text for loc in loc_nodes]

    except Exception as e:
        print(f"[sitemap] não disponível ou falhou ({e}); usando fallback por categorias.")
        return []

    return _filter_product_urls(urls)


def _filter_product_urls(urls: list) -> list:
    filtered = []
    for u in urls:
        if not u.startswith(BASE_URL):
            continue
        path = u.replace(BASE_URL, "")
        if any(frag in path for frag in EXCLUDE_URL_FRAGMENTS):
            continue
        if path.count("/") >= 2:
            filtered.append(u)
    return sorted(set(filtered))


def discover_urls_from_categories(session: requests.Session, delay: float) -> list:
    product_urls = set()
    for cat_path in CATEGORY_URLS:
        cat_url = urljoin(BASE_URL, cat_path)
        print(f"[categoria] {cat_url}")
        soup = get_soup(cat_url, session)
        if not soup:
            continue
        for a in soup.select("a[href]"):
            href = a["href"]
            if not href.startswith("http"):
                href = urljoin(BASE_URL, href)
            if not href.startswith(BASE_URL):
                continue
            path = href.replace(BASE_URL, "")
            if any(frag in path for frag in EXCLUDE_URL_FRAGMENTS):
                continue
            if path.count("/") >= 2:
                product_urls.add(href)
        time.sleep(delay)
    return sorted(product_urls)


def parse_range(raw: Optional[str]):
    """Extrai (min, max) de uma string com números, ex: 'pH 6.0 a 7.5'."""
    if not raw:
        return None, None
    nums = re.findall(r"\d+[.,]?\d*", raw)
    nums = [float(n.replace(",", ".")) for n in nums]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def is_product_page(text: str) -> bool:
    """Heurística: toda página de produto Tray tem 'Ref: <codigo>' visível."""
    return bool(re.search(r"\bRef:\s*\S+", text)) and len(text) > 300


BINOMIAL_STOPWORDS = {
    "linhagem", "selvagem", "hibrido", "híbrido", "importada", "importado",
    "nacional", "reproduzido", "reproduzida", "macho", "femea", "fêmea",
    "casal", "albino", "super", "jumbo", "sexado", "sexada", "adulto",
    "adulta", "juvenil", "extra",
}


def extract_name_from_title(soup: BeautifulSoup) -> tuple:
    """Título costuma seguir o padrão 'Nome Popular | tamanho | Nome
    Científico | qualificadores extras' (ex: 'Ramirezi Super Dark Knight |
    2 a 4 cm | Microgeophagus Ramirezi | Linhagem importada').
    Retorna (nome_popular, nome_cientifico_ou_None).

    Percorre os segmentos em ORDEM (não invertida) e pega o primeiro que
    parece um binômio científico, ignorando falsos positivos comuns como
    'Linhagem importada' (duas palavras capitalizadas também batem no
    regex, mas não são nomes científicos)."""
    title_tag = soup.find("h1") or soup.title
    if not title_tag:
        return None, None
    raw_title = title_tag.get_text(" ", strip=True)
    parts = [p.strip() for p in raw_title.split("|") if p.strip()]
    if not parts:
        return None, None

    nome_popular = parts[0]
    nome_cientifico = None
    for p in parts[1:]:
        if not BINOMIAL_RE.match(p):
            continue
        first_word = p.split()[0].lower()
        if first_word in BINOMIAL_STOPWORDS:
            continue
        nome_cientifico = p
        break
    return nome_popular, nome_cientifico


def extract_field_from_lines(lines: list, labels: list, max_len: int = 400) -> Optional[str]:
    """Procura, linha a linha, por 'Label: valor' (tolera marcações
    markdown como **, ###, - antes/depois do rótulo)."""
    for line in lines:
        for label in labels:
            pattern = rf"{re.escape(label)}\*{{0,2}}\s*[:;]\s*\*{{0,2}}\s*(.+)"
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                value = m.group(1)
                value = value.replace("**", "").replace("###", "")
                value = re.sub(r"\s+", " ", value).strip(" .;-")
                if value:
                    return value[:max_len]
    return None


def _find_number_near_keyword(text: str, keyword_pattern: str, window: int = 100,
                               allow_degree: bool = False) -> Optional[str]:
    """Acha a 1ª ocorrência da palavra-chave que tenha número(s) por perto
    (numa janela de texto depois dela) e retorna o trecho numérico bruto.

    Lida com formatos como 'pH 4.5 a 7', 'pH de 4.5 a 7', 'temperatura
    24°C a 30°C' (nota: o símbolo de grau gruda no número, então o
    conector 'a' fica DEPOIS do °C, não direto entre os dois números).

    IMPORTANTE: a Kauar mistura dois caracteres visualmente parecidos mas
    Unicode diferentes: '°' (grau, U+00B0) e 'º' (indicador ordinal
    masculino, U+00BA). O regex precisa aceitar os dois ([°º])."""
    degree = r"\s*[°º]?\s*[Cc]?" if allow_degree else ""
    range_pattern = rf"(\d+[.,]?\d*){degree}\s*(?:a|à|-|~|e)\s*(\d+[.,]?\d*){degree}"
    single_pattern = rf"(\d+[.,]?\d*){degree}"

    for m in re.finditer(keyword_pattern, text, re.IGNORECASE):
        window_text = text[m.end():m.end() + window]
        range_match = re.search(range_pattern, window_text)
        if range_match:
            return range_match.group(0).strip()
        single_match = re.search(single_pattern, window_text)
        if single_match:
            return single_match.group(0).strip()
    return None


def extract_ph_temp_fallback(full_text: str):
    """Quando pH/temperatura vêm embutidos numa frase corrida (ex:
    'temperatura por volta de 26ºC e pH 7 a 8.5', ou 'temperatura ideal
    varia entre 24°C a 30°C'), busca os números próximos das
    palavras-chave em todo o texto."""
    ph_raw = _find_number_near_keyword(full_text, r"\bpH\b", window=30, allow_degree=False)
    temp_raw = _find_number_near_keyword(full_text, r"\btemperatura\b", window=60, allow_degree=True)
    return ph_raw, temp_raw


def extract_images(soup: BeautifulSoup) -> tuple:
    """Retorna (imagem_principal, [galeria]). Estratégia: og:image como
    principal (confiável) + seletores comuns de galeria Tray como extra."""
    main_image = None
    og_image_tag = soup.find("meta", attrs={"property": "og:image"})
    if og_image_tag and og_image_tag.get("content"):
        main_image = og_image_tag["content"].strip()

    gallery = []
    gallery_selectors = [
        ".produto-imagens img",
        ".galeria-produto img",
        "#galeria img",
        ".carousel-produto img",
        "[data-zoom-image]",
        "a.thumb img",
    ]
    seen = set()
    for sel in gallery_selectors:
        for img in soup.select(sel):
            src = img.get("data-zoom-image") or img.get("data-src") or img.get("src")
            if not src:
                continue
            src = urljoin(BASE_URL, src)
            if any(bad in src.lower() for bad in ["empty.png", "loading.gif", "whatsapp"]):
                continue
            if src not in seen:
                seen.add(src)
                gallery.append(src)

    if not main_image and gallery:
        main_image = gallery[0]

    return main_image, gallery


def extract_fish_data(url: str, soup: BeautifulSoup) -> Optional[Fish]:
    # IMPORTANTE: "Ref:" (usado para detectar se é página de produto) e
    # trechos curtos com pH/temperatura costumam ficar FORA da div de
    # descrição (ex: div.product-form, div.product-additional-message).
    # Por isso a detecção e os fallbacks numéricos usam o texto da
    # PÁGINA INTEIRA, não só da descrição.
    full_text = soup.get_text("\n", strip=True)

    if not is_product_page(full_text):
        return None

    desc_container = (
        soup.select_one("#descricao")
        or soup.select_one(".descricao-produto")
        or soup.select_one("[id*=descricao]")
    )
    # Se achou uma div de descrição específica, usa ela para os rótulos
    # (Nome popular, Origem etc); senão, cai para o texto da página toda.
    desc_text = desc_container.get_text("\n", strip=True) if desc_container else full_text

    fish = Fish(url=url)
    lines = desc_text.split("\n")

    nome_popular, nome_cientifico_title = extract_name_from_title(soup)
    fish.nome_popular = nome_popular
    fish.nome_cientifico = nome_cientifico_title

    for field_name, labels in FIELD_LABELS.items():
        value = extract_field_from_lines(lines, labels)
        if value:
            current = getattr(fish, field_name, None)
            if not current:
                setattr(fish, field_name, value)

    # Fallback pH / temperatura embutidos em frase corrida — busca no
    # texto da PÁGINA INTEIRA, pois esses dados às vezes aparecem num
    # resumo curto fora da div de descrição (ex: "Ficarão muito bem em
    # pH 4.5 a 7 ... e temperatura 24°C a 30°C").
    if not fish.ph or not re.search(r"\d", fish.ph):
        ph_fb, _ = extract_ph_temp_fallback(full_text)
        if ph_fb:
            fish.ph = ph_fb
    if not fish.temperatura_ideal or not re.search(r"\d", fish.temperatura_ideal):
        _, temp_fb = extract_ph_temp_fallback(full_text)
        if temp_fb:
            fish.temperatura_ideal = temp_fb

    fish.ph_min, fish.ph_max = parse_range(fish.ph)
    fish.temp_min_c, fish.temp_max_c = parse_range(fish.temperatura_ideal)

    # Heurística simples de tipo: planta/substrato vs peixe/camarão
    path = url.replace(BASE_URL, "")
    if any(seg in path for seg in ["/aquapaisagismo", "/aquascaping"]):
        fish.tipo = "planta_ou_aquascape"
    else:
        fish.tipo = "peixe_ou_camarao"

    # Companheiros sugeridos (best effort)
    comp_match = re.search(
        r"(?:companheiros de aquário|conviver com|convive[m]? (?:bem )?com)"
        r"[^.]*?((?:[A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú]?[a-zà-ú]+)*,?\s*)+)\.",
        desc_text,
    )
    if comp_match:
        raw_names = comp_match.group(1)
        names = [n.strip(" .") for n in raw_names.split(",") if n.strip()]
        fish.companheiros_sugeridos = names

    fish.raw_description_snippet = desc_text[:600]
    fish.imagem_principal_url, fish.imagens_galeria = extract_images(soup)
    return fish


def scrape(limit: Optional[int], delay: float):
    session = requests.Session()

    print("Descobrindo URLs de produtos (tentando sitemap.xml primeiro)...")
    urls = discover_urls_from_sitemap(session)

    if not urls:
        urls = discover_urls_from_categories(session, delay)

    if limit:
        urls = urls[:limit]

    print(f"\n{len(urls)} URLs candidatas encontradas. Iniciando extração...\n")

    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        soup = get_soup(url, session)
        if not soup:
            continue
        fish = extract_fish_data(url, soup)
        if fish:
            results.append(fish)
            print(f"   -> OK: {fish.nome_popular or '(sem nome extraído)'}")
        else:
            print("   -> ignorado (não parece página de produto)")
        time.sleep(delay)

    return results


def save_results(results: list):
    data = [asdict(f) for f in results]

    with open("kauar_peixes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if data:
        fieldnames = list(data[0].keys())
        with open("kauar_peixes.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                row = row.copy()
                row["companheiros_sugeridos"] = "; ".join(row["companheiros_sugeridos"])
                row["imagens_galeria"] = "; ".join(row["imagens_galeria"])
                writer.writerow(row)

    print(f"\nSalvo: kauar_peixes.json e kauar_peixes.csv ({len(data)} itens)")


def main():
    parser = argparse.ArgumentParser(description="Scraper de fichas técnicas da Kauar (peixes e plantas)")
    parser.add_argument("--limit", type=int, default=None, help="Limitar número de produtos (teste)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay em segundos entre requisições")
    args = parser.parse_args()

    results = scrape(limit=args.limit, delay=args.delay)
    save_results(results)


if __name__ == "__main__":
    main()