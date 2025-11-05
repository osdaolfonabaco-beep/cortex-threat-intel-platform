import scrapy
from scrapy.crawler import CrawlerProcess
import feedparser
from bs4 import BeautifulSoup

class ThreatIntelSpider(scrapy.Spider):
    """
    Un Spider HÍBRIDO de Scrapy. Sabe cómo extraer de feeds 
    directos (SANS, Unit42) y cómo scrapear feeds de resumen (Google).
    """
    name = "threat_intel_spider"

    # URLs corregidas y verificadas.
    start_urls = [
        'https://isc.sans.edu/rssfeed.xml',
        'https://unit42.paloaltonetworks.com/feed/', 
        'https://cloudblog.withgoogle.com/topics/threat-intelligence/rss/'
    ]

    # Fuentes de las que podemos extraer texto directamente del feed
    direct_extract_feeds = [
        'isc.sans.edu',
        'unit42.paloaltonetworks.com'
    ]
    
    # Fuentes que solo tienen resúmenes y requieren scraping
    # Mapeamos el dominio al selector CSS que contiene el artículo
    follow_link_feeds = {
        'cloudblog.withgoogle.com': 'article' # <-- ¡CORRECCIÓN APLICADA! Selector más robusto.
    }
    # -------------------------

    def parse(self, response):
        """
        Método principal. Determina qué lógica de parsing usar
        basándose en el dominio del feed.
        """
        feed = feedparser.parse(response.text)
        self.logger.info(f"Encontrados {len(feed.entries)} artículos en el feed: {response.url}")

        feed_domain = response.url.split('/')[2] 
        
        if feed_domain in self.direct_extract_feeds:
            # --- LÓGICA 1: Extracción Directa (SANS, Palo Alto) ---
            self.logger.info(f"Usando método de EXTRACCIÓN DIRECTA para {feed_domain}")
            for entry in feed.entries:
                text = self.extract_direct_text(entry)
                if text:
                    yield {
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else 'N/A',
                        'raw_text': text
                    }
        
        elif feed_domain in self.follow_link_feeds:
            # --- LÓGICA 2: Seguir Enlace (Google/Mandiant) ---
            self.logger.info(f"Usando método de SEGUIR ENLACE para {feed_domain}")
            selector = self.follow_link_feeds[feed_domain]
            for entry in feed.entries:
                if entry.link:
                    yield response.follow(
                        entry.link, 
                        self.parse_report,
                        meta={
                            'selector': selector, 
                            'title': entry.title, 
                            'link': entry.link,
                            'published': entry.published if hasattr(entry, 'published') else 'N/A'
                        }
                    )

    def extract_direct_text(self, entry):
        """
        Helper para la Lógica 1: Extrae texto de entry.content o entry.summary.
        """
        html_content = ""
        if hasattr(entry, 'content'):
            html_content = entry.content[0].value
        elif hasattr(entry, 'summary'):
            html_content = entry.summary
        else:
            self.logger.warning(f"La entrada (directa) '{entry.title}' no tiene 'content' ni 'summary'. Saltando.")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        raw_text = soup.get_text(separator='\n', strip=True)
        
        if not raw_text:
            self.logger.warning(f"Texto vacío (directo) después de limpiar HTML para '{entry.title}'. Saltando.")
            return None
        
        self.logger.info(f"EXTRAÍDO (Directo): {entry.title[:100]}...")
        return raw_text

    def parse_report(self, response):
        """
        Helper para la Lógica 2: Este es nuestro método de scraping,
        que se llama después de seguir un enlace.
        """
        selector = response.meta['selector']
        title = response.meta['title']
        link = response.meta['link']
        published = response.meta['published']
        
        self.logger.info(f"Procesando (Scraping): {title}")

        soup = BeautifulSoup(response.body, 'html.parser')
        
        # Usamos el selector CSS específico para este sitio
        content_block = soup.select_one(selector) 
        
        if content_block:
            raw_text = content_block.get_text(separator='\n', strip=True)
            self.logger.info(f"EXTRAÍDO (Scraping): {title[:100]}...")
            yield {
                'title': title,
                'link': link,
                'published': published,
                'raw_text': raw_text
            }
        else:
            self.logger.warning(f"No se pudo encontrar el selector '{selector}' en {response.url}")

# --- Bloque para ejecutar el Spider (sin cambios) ---
if __name__ == "__main__":
    process = CrawlerProcess(settings={
        "FEEDS": {
            "items_extraidos.json": {"format": "json", "overwrite": True},
        },
        "DOWNLOAD_DELAY": 0.5,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "INFO", 
    })

    process.crawl(ThreatIntelSpider)
    process.start()

    