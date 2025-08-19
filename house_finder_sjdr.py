#!/usr/bin/env python3
"""
Buscador de Casas - São João del Rei
Programa para buscar imóveis no centro e bairro Segredo
Preço máximo: R$ 350.000
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('house_finder.log'),
        logging.StreamHandler()
    ]
)

class HouseFinder:
    def __init__(self):
        self.max_price = 350000
        self.target_neighborhoods = ['centro', 'segredo', 'bairro segredo']
        self.city = 'são joão del rei'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.results = []
        
        # Sites de imobiliárias locais conhecidos
        self.sites = {
            'vivareal': {
                'base_url': 'https://www.vivareal.com.br',
                'search_url': 'https://www.vivareal.com.br/venda/minas-gerais/sao-joao-del-rei/casa_residencial/',
                'selectors': {
                    'property': '.property-card__container',
                    'title': '.property-card__title',
                    'price': '.property-card__price',
                    'address': '.property-card__address',
                    'link': 'a.property-card__labels-container'
                }
            },
            'zapimoveis': {
                'base_url': 'https://www.zapimoveis.com.br',
                'search_url': 'https://www.zapimoveis.com.br/venda/casas/mg+sao-joao-del-rei/',
                'selectors': {
                    'property': '[data-testid="property-card"]',
                    'title': '[data-testid="property-card-title"]',
                    'price': '[data-testid="property-card-price"]',
                    'address': '[data-testid="property-card-address"]',
                    'link': 'a'
                }
            },
            'olx': {
                'base_url': 'https://mg.olx.com.br',
                'search_url': 'https://mg.olx.com.br/regiao-de-sao-joao-del-rei/imoveis/casas-venda',
                'selectors': {
                    'property': '[data-ds-component="DS-NEW-VERTICAL-LIST-ITEM"]',
                    'title': 'h2',
                    'price': '[data-testid="ad-price"]',
                    'address': '[data-testid="location"]',
                    'link': 'a'
                }
            }
        }

    def clean_price(self, price_text: str) -> Optional[float]:
        """Limpa e converte texto de preço para float"""
        if not price_text:
            return None
        
        # Remove caracteres não numéricos exceto pontos e vírgulas
        price_clean = re.sub(r'[^\d.,]', '', price_text)
        
        # Trata formato brasileiro (vírgula decimal, ponto milhares)
        if ',' in price_clean and '.' in price_clean:
            # Formato: 123.456,78
            price_clean = price_clean.replace('.', '').replace(',', '.')
        elif ',' in price_clean:
            # Formato: 123456,78 ou 123,45
            if len(price_clean.split(',')[1]) <= 2:
                price_clean = price_clean.replace(',', '.')
            else:
                price_clean = price_clean.replace(',', '')
        
        try:
            return float(price_clean)
        except ValueError:
            return None

    def is_target_neighborhood(self, address: str) -> bool:
        """Verifica se o endereço está nos bairros alvo"""
        if not address:
            return False
        
        address_lower = address.lower()
        return any(neighborhood in address_lower for neighborhood in self.target_neighborhoods)

    def scrape_site(self, site_name: str, site_config: Dict) -> List[Dict]:
        """Faz scraping de um site específico"""
        results = []
        
        try:
            logging.info(f"Buscando em {site_name}...")
            response = self.session.get(site_config['search_url'], timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            properties = soup.select(site_config['selectors']['property'])
            
            logging.info(f"Encontradas {len(properties)} propriedades em {site_name}")
            
            for prop in properties[:20]:  # Limita a 20 propriedades por site
                try:
                    # Extrai informações
                    title_elem = prop.select_one(site_config['selectors']['title'])
                    price_elem = prop.select_one(site_config['selectors']['price'])
                    address_elem = prop.select_one(site_config['selectors']['address'])
                    link_elem = prop.select_one(site_config['selectors']['link'])
                    
                    title = title_elem.get_text(strip=True) if title_elem else 'Título não encontrado'
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    address = address_elem.get_text(strip=True) if address_elem else 'Endereço não encontrado'
                    
                    # Processa preço
                    price = self.clean_price(price_text)
                    
                    # Verifica se atende aos critérios
                    if price and price <= self.max_price and self.is_target_neighborhood(address):
                        # Constrói URL completa
                        link_url = ''
                        if link_elem and link_elem.get('href'):
                            link_url = urljoin(site_config['base_url'], link_elem.get('href'))
                        
                        property_data = {
                            'site': site_name,
                            'title': title,
                            'price': price,
                            'price_formatted': f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                            'address': address,
                            'url': link_url
                        }
                        
                        results.append(property_data)
                        logging.info(f"Propriedade encontrada: {title} - {property_data['price_formatted']}")
                
                except Exception as e:
                    logging.warning(f"Erro ao processar propriedade: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Erro ao acessar {site_name}: {e}")
        
        return results

    def search_all_sites(self) -> List[Dict]:
        """Busca em todos os sites configurados"""
        all_results = []
        
        for site_name, site_config in self.sites.items():
            site_results = self.scrape_site(site_name, site_config)
            all_results.extend(site_results)
            
            # Pausa entre sites para evitar bloqueios
            time.sleep(2)
        
        return all_results

    def save_results(self, results: List[Dict], filename: str = 'casas_sjdr'):
        """Salva os resultados em diferentes formatos"""
        if not results:
            logging.info("Nenhum resultado encontrado para salvar.")
            return
        
        # Salva em JSON
        with open(f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Salva em CSV
        df = pd.DataFrame(results)
        df.to_csv(f'{filename}.csv', index=False, encoding='utf-8')
        
        # Salva em HTML (relatório visual)
        html_content = self.generate_html_report(results)
        with open(f'{filename}.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logging.info(f"Resultados salvos em {filename}.json, {filename}.csv e {filename}.html")

    def generate_html_report(self, results: List[Dict]) -> str:
        """Gera relatório HTML dos resultados"""
        html = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Casas Encontradas - São João del Rei</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .property {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .price {{ color: #27ae60; font-weight: bold; font-size: 18px; }}
                .site {{ background-color: #3498db; color: white; padding: 5px 10px; border-radius: 3px; font-size: 12px; }}
                .address {{ color: #7f8c8d; margin: 5px 0; }}
                a {{ color: #2980b9; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏠 Casas Encontradas - São João del Rei</h1>
                <p>Centro e Bairro Segredo - Até R$ 350.000</p>
                <p>Total encontrado: {len(results)} propriedades</p>
            </div>
        """
        
        for prop in sorted(results, key=lambda x: x['price']):
            html += f"""
            <div class="property">
                <span class="site">{prop['site'].upper()}</span>
                <h3>{prop['title']}</h3>
                <div class="price">{prop['price_formatted']}</div>
                <div class="address">📍 {prop['address']}</div>
                {f'<a href="{prop["url"]}" target="_blank">Ver detalhes</a>' if prop['url'] else ''}
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        return html

    def run(self):
        """Executa a busca completa"""
        logging.info("🏠 Iniciando busca de casas em São João del Rei...")
        logging.info(f"Critérios: Centro e Bairro Segredo, até R$ {self.max_price:,.2f}")
        
        results = self.search_all_sites()
        
        if results:
            logging.info(f"✅ Encontradas {len(results)} propriedades que atendem aos critérios!")
            
            # Remove duplicatas baseado na URL
            unique_results = []
            seen_urls = set()
            for result in results:
                if result['url'] not in seen_urls and result['url']:
                    unique_results.append(result)
                    seen_urls.add(result['url'])
                elif not result['url']:  # Inclui propriedades sem URL
                    unique_results.append(result)
            
            logging.info(f"📊 {len(unique_results)} propriedades únicas após remoção de duplicatas")
            
            self.save_results(unique_results)
            
            # Exibe resumo
            print("\n" + "="*60)
            print("🏠 RESUMO DA BUSCA")
            print("="*60)
            for i, prop in enumerate(sorted(unique_results, key=lambda x: x['price']), 1):
                print(f"\n{i}. {prop['title']}")
                print(f"   💰 {prop['price_formatted']}")
                print(f"   📍 {prop['address']}")
                print(f"   🌐 {prop['site'].capitalize()}")
                if prop['url']:
                    print(f"   🔗 {prop['url']}")
        else:
            logging.info("❌ Nenhuma propriedade encontrada com os critérios especificados.")
            print("\n💡 Sugestões:")
            print("- Verifique se os sites estão acessíveis")
            print("- Considere aumentar o valor máximo")
            print("- Tente novamente mais tarde")

def main():
    """Função principal"""
    finder = HouseFinder()
    finder.run()

if __name__ == "__main__":
    main()
