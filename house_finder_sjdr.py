def search_all_sites(self) -> List[Dict]:
        """Busca em todos os sites configurados (apenas sites ativos)"""
        all_results = []
        local_sites = []
        national_sites = []
        
        # Separa sites locais dos nacionais (apenas ativos)
        for site_name, site_config in self.sites.items():
            if not site_config.get('active', True):  # Pula sites desabilitados
                logging.info(f"⏭️ Pulando {site_name} (desabilitado)")
                continue
                
            if site_name in ['vivareal', 'zapimoveis', 'olx']:
                national_sites.append((site_name, site_config))
            else:
                local_sites.append((site_name, site_config))
        
        # Busca nos portais nacionais primeiro (mais confiáveis)
        logging.info("🌐 Iniciando busca nos PORTAIS NACIONAIS...")
        for site_name, site_config in national_sites:
            site_results = self.scrape_site(site_name, site_config)
            all_results.extend(site_results)
            # Pausa entre sites nacionais
            time.sleep(3)
        
        logging.info(f"📊 Encontrados {len(all_results)} imóveis nos portais nacionais")
        
        # Depois tenta as imobiliárias locais (se houver sites ativos)
        if local_sites:
            logging.info("🏢 Tentando IMOBILIÁRIAS LOCAIS...")
            for site_name, site_config in local_sites:
                site_results = self.scrape_site(site_name, site_config)
                all_results.extend(site_results)
                # Pausa mais longa para sites locais (mais sensíveis)
                time.sleep(5)
        else:
            logging.info("ℹ️ Todas as imobiliárias locais estão desabilitadas no momento")
        
        return all_results#!/usr/bin/env python3
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
        
        # Headers mais realistas para evitar bloqueios
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        self.results = []
        
        # Sites de imobiliárias (portais nacionais + locais de SJDR)
        self.sites = {
            # SITES MAIS CONFIÁVEIS (menos propensos a bloqueios)
            'vivareal': {
                'base_url': 'https://www.vivareal.com.br',
                'search_url': 'https://www.vivareal.com.br/venda/minas-gerais/sao-joao-del-rei/casa_residencial/',
                'selectors': {
                    'property': '.property-card__container, .result-card',
                    'title': '.property-card__title, .result-card__title',
                    'price': '.property-card__price, .result-card__price',
                    'address': '.property-card__address, .result-card__address',
                    'link': 'a'
                },
                'active': True
            },
            'zapimoveis': {
                'base_url': 'https://www.zapimoveis.com.br',
                'search_url': 'https://www.zapimoveis.com.br/venda/casas/mg+sao-joao-del-rei/',
                'selectors': {
                    'property': '[data-testid="property-card"], .card-container',
                    'title': '[data-testid="property-card-title"], .card__title',
                    'price': '[data-testid="property-card-price"], .card__price',
                    'address': '[data-testid="property-card-address"], .card__address',
                    'link': 'a'
                },
                'active': True
            },
            
            # SITES COM POSSÍVEL BLOQUEIO (tentar com cuidado)
            'olx': {
                'base_url': 'https://mg.olx.com.br',
                'search_url': 'https://mg.olx.com.br/regiao-de-sao-joao-del-rei/imoveis/casas-venda',
                'selectors': {
                    'property': '[data-ds-component="DS-NEW-VERTICAL-LIST-ITEM"]',
                    'title': 'h2',
                    'price': '[data-testid="ad-price"]',
                    'address': '[data-testid="location"]',
                    'link': 'a'
                },
                'active': False  # Desabilitado por enquanto devido a bloqueios
            },
            
            # IMOBILIÁRIAS LOCAIS DE SÃO JOÃO DEL REI (URLs genéricas - podem não existir)
            'zanfer_imoveis': {
                'base_url': 'https://www.zanferimoveis.com.br',
                'search_url': 'https://www.zanferimoveis.com.br/imoveis/casas',
                'selectors': {
                    'property': '.imovel-item, .property-item, .card-imovel',
                    'title': 'h2, h3, .titulo, .title',
                    'price': '.preco, .price, .valor',
                    'address': '.endereco, .address, .localizacao',
                    'link': 'a'
                },
                'active': False  # Desabilitado - site pode não existir
            },
            'lc_imoveis': {
                'base_url': 'https://lcimobiliaria.com.br',
                'search_url': 'https://lcimobiliaria.com.br/imoveis',
                'selectors': {
                    'property': '.imovel, .property, .listing',
                    'title': 'h2, h3, .titulo',
                    'price': '.preco, .price',
                    'address': '.endereco, .address',
                    'link': 'a'
                },
                'active': False  # Desabilitado - site pode não existir
            },
            'maxima_imoveis': {
                'base_url': 'https://www.maximaimobiliaria.com.br',
                'search_url': 'https://www.maximaimobiliaria.com.br/imoveis/venda/casas',
                'selectors': {
                    'property': '.imovel-card, .property-card, .listing-card',
                    'title': 'h2, h3, .title, .titulo',
                    'price': '.preco, .price, .valor',
                    'address': '.endereco, .address, .local',
                    'link': 'a'
                },
                'active': False  # Desabilitado - site pode não existir
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
        """Faz scraping de um site específico com proteção contra bloqueios"""
        results = []
        
        try:
            logging.info(f"Buscando em {site_name}...")
            
            # Headers específicos para cada site
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            }
            
            # Timeout maior para evitar erros de conexão
            try:
                response = self.session.get(
                    site_config['search_url'], 
                    headers=headers, 
                    timeout=20, 
                    allow_redirects=True
                )
                response.raise_for_status()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logging.warning(f"❌ {site_name}: Acesso bloqueado (403 Forbidden) - site protege contra bots")
                    return results
                elif e.response.status_code == 404:
                    logging.warning(f"❌ {site_name}: Página não encontrada (404) - URL pode estar incorreta")
                    return results
                else:
                    logging.warning(f"❌ {site_name}: Erro HTTP {e.response.status_code}")
                    return results
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tenta múltiplos seletores para propriedades
            properties = []
            selectors = site_config['selectors']['property'].split(', ')
            for selector in selectors:
                props = soup.select(selector.strip())
                if props:
                    properties = props
                    logging.info(f"✅ {site_name}: Usando seletor '{selector}' - encontradas {len(props)} propriedades")
                    break
            
            if not properties:
                # Fallback: busca por padrões comuns
                fallback_selectors = [
                    '.property', '.imovel', '.listing', '.card',
                    '[class*="property"]', '[class*="imovel"]', 
                    '[class*="listing"]', '[class*="card"]',
                    '.result-card', '.search-result'
                ]
                for selector in fallback_selectors:
                    props = soup.select(selector)
                    if props:
                        properties = props[:10]  # Limita para teste
                        logging.info(f"🔄 {site_name}: Fallback seletor '{selector}' - {len(props)} elementos")
                        break
            
            if not properties:
                logging.info(f"⚠️ {site_name}: Nenhuma propriedade encontrada - site pode ter mudado estrutura")
                return results
            
            logging.info(f"📊 {site_name}: Processando {len(properties)} propriedades...")
            
            for i, prop in enumerate(properties[:10]):  # Reduzido para 10 por site
                try:
                    # Tenta múltiplos seletores para cada campo
                    title = self.extract_text_multi_selectors(prop, site_config['selectors']['title'])
                    price_text = self.extract_text_multi_selectors(prop, site_config['selectors']['price'])
                    address = self.extract_text_multi_selectors(prop, site_config['selectors']['address'])
                    
                    # Se não conseguiu extrair título, tenta alternativas
                    if not title:
                        title = self.extract_text_multi_selectors(prop, 'h1, h2, h3, h4, .title, .titulo, .nome, [title]')
                    
                    # Se não conseguiu extrair preço, tenta alternativas
                    if not price_text:
                        price_text = self.extract_text_multi_selectors(prop, '.valor, .price, .preco, [class*="price"], [class*="preco"], [class*="valor"]')
                    
                    # Se não conseguiu extrair endereço, tenta alternativas
                    if not address:
                        address = self.extract_text_multi_selectors(prop, '.local, .localizacao, .endereco, .address, [class*="endereco"], [class*="address"], [class*="local"]')
                    
                    # Valores padrão se não encontrou
                    title = title or f'Casa {i+1} - {site_name.replace("_", " ").title()}'
                    price_text = price_text or '0'
                    address = address or 'São João del Rei, MG'
                    
                    # Processa preço
                    price = self.clean_price(price_text)
                    
                    # Verifica se atende aos critérios
                    if price and price <= self.max_price and price > 50000:  # Preço mínimo para evitar erros
                        # Para sites nacionais, verifica localização; para locais, assume que são da região
                        is_local_site = site_name not in ['vivareal', 'zapimoveis', 'olx']
                        location_ok = is_local_site or self.is_target_neighborhood(address)
                        
                        if location_ok:
                            # Constrói URL do imóvel
                            link_url = ''
                            link_selectors = site_config['selectors']['link'].split(', ')
                            for link_sel in link_selectors:
                                link_elem = prop.select_one(link_sel.strip())
                                if link_elem and link_elem.get('href'):
                                    href = link_elem.get('href')
                                    if href.startswith('http'):
                                        link_url = href
                                    else:
                                        link_url = urljoin(site_config['base_url'], href)
                                    break
                            
                            # Se não encontrou link, usa o site base
                            if not link_url:
                                link_url = site_config['base_url']
                            
                            property_data = {
                                'site': site_name.replace('_', ' ').title(),
                                'title': title,
                                'price': price,
                                'price_formatted': f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                                'address': address,
                                'url': link_url,
                                'is_local': is_local_site
                            }
                            
                            results.append(property_data)
                            logging.info(f"✅ {site_name}: {title} - {property_data['price_formatted']}")
                
                except Exception as e:
                    logging.debug(f"Erro ao processar propriedade {i+1} de {site_name}: {e}")
                    continue
                    
        except requests.exceptions.Timeout:
            logging.warning(f"⏰ {site_name}: Timeout - site muito lento")
        except requests.exceptions.ConnectionError:
            logging.warning(f"🌐 {site_name}: Erro de conexão - site pode estar fora do ar")
        except requests.exceptions.RequestException as e:
            logging.warning(f"❌ {site_name}: Erro de requisição: {e}")
        except Exception as e:
            logging.error(f"💥 {site_name}: Erro inesperado: {e}")
        
        return results

    def extract_text_multi_selectors(self, element, selectors_string: str) -> str:
        """Tenta extrair texto usando múltiplos seletores"""
        if not selectors_string:
            return ''
        
        selectors = selectors_string.split(', ')
        for selector in selectors:
            try:
                elem = element.select_one(selector.strip())
                if elem:
                    text = elem.get_text(strip=True)
                    if text:
                        return text
            except:
                continue
        return ''

    def search_all_sites(self) -> List[Dict]:
        """Busca em todos os sites configurados"""
        all_results = []
        local_sites = []
        national_sites = []
        
        # Separa sites locais dos nacionais
        for site_name, site_config in self.sites.items():
            if site_name in ['vivareal', 'zapimoveis', 'olx']:
                national_sites.append((site_name, site_config))
            else:
                local_sites.append((site_name, site_config))
        
        # Busca primeiro nas imobiliárias locais
        logging.info("🏢 Iniciando busca nas IMOBILIÁRIAS LOCAIS de São João del Rei...")
        for site_name, site_config in local_sites:
            site_results = self.scrape_site(site_name, site_config)
            all_results.extend(site_results)
            # Pausa mais longa para sites locais (mais sensíveis)
            time.sleep(3)
        
        logging.info(f"📊 Encontrados {len(all_results)} imóveis nas imobiliárias locais")
        
        # Depois busca nos portais nacionais
        logging.info("🌐 Buscando nos PORTAIS NACIONAIS...")
        for site_name, site_config in national_sites:
            site_results = self.scrape_site(site_name, site_config)
            all_results.extend(site_results)
            # Pausa menor para portais nacionais
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
        local_results = [r for r in results if r.get('is_local', False)]
        national_results = [r for r in results if not r.get('is_local', False)]
        
        html = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Casas Encontradas - São João del Rei</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .section-title {{ background-color: #34495e; color: white; padding: 15px; border-radius: 5px; margin: 20px 0 10px 0; }}
                .property {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .property.local {{ border-left: 5px solid #e74c3c; }}
                .property.national {{ border-left: 5px solid #3498db; }}
                .price {{ color: #27ae60; font-weight: bold; font-size: 18px; }}
                .site {{ padding: 5px 10px; border-radius: 3px; font-size: 12px; color: white; display: inline-block; margin-bottom: 5px; }}
                .site.local {{ background-color: #e74c3c; }}
                .site.national {{ background-color: #3498db; }}
                .address {{ color: #7f8c8d; margin: 5px 0; }}
                a {{ color: #2980b9; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .no-results {{ text-align: center; color: #7f8c8d; padding: 40px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏠 Casas Encontradas - São João del Rei</h1>
                <p>Centro e Bairro Segredo - Até R$ 350.000</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>{len(results)}</h3>
                    <p>Total de Imóveis</p>
                </div>
                <div class="stat-box">
                    <h3>{len(local_results)}</h3>
                    <p>Imobiliárias Locais</p>
                </div>
                <div class="stat-box">
                    <h3>{len(national_results)}</h3>
                    <p>Portais Nacionais</p>
                </div>
                <div class="stat-box">
                    <h3>R$ {min([r['price'] for r in results]):,.0f}</h3>
                    <p>Menor Preço</p>
                </div>
            </div>
        """
        
        if local_results:
            html += f"""
            <div class="section-title">
                🏢 IMOBILIÁRIAS LOCAIS DE SÃO JOÃO DEL REI ({len(local_results)} imóveis)
            </div>
            """
            for prop in sorted(local_results, key=lambda x: x['price']):
                html += f"""
                <div class="property local">
                    <span class="site local">{prop['site'].upper()}</span>
                    <h3>{prop['title']}</h3>
                    <div class="price">{prop['price_formatted']}</div>
                    <div class="address">📍 {prop['address']}</div>
                    {f'<a href="{prop["url"]}" target="_blank">🔗 Ver no site da imobiliária</a>' if prop['url'] else ''}
                </div>
                """
        
        if national_results:
            html += f"""
            <div class="section-title">
                🌐 PORTAIS NACIONAIS ({len(national_results)} imóveis)
            </div>
            """
            for prop in sorted(national_results, key=lambda x: x['price']):
                html += f"""
                <div class="property national">
                    <span class="site national">{prop['site'].upper()}</span>
                    <h3>{prop['title']}</h3>
                    <div class="price">{prop['price_formatted']}</div>
                    <div class="address">📍 {prop['address']}</div>
                    {f'<a href="{prop["url"]}" target="_blank">🔗 Ver detalhes</a>' if prop['url'] else ''}
                </div>
                """
        
        if not results:
            html += """
            <div class="no-results">
                <h3>❌ Nenhum imóvel encontrado</h3>
                <p>Tente ajustar os critérios de busca ou verificar novamente mais tarde.</p>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        return html

    def enable_site(self, site_name: str):
        """Habilita um site específico para teste"""
        if site_name in self.sites:
            self.sites[site_name]['active'] = True
            logging.info(f"✅ Site {site_name} habilitado")
        else:
            logging.warning(f"⚠️ Site {site_name} não encontrado")

    def disable_site(self, site_name: str):
        """Desabilita um site específico"""
        if site_name in self.sites:
            self.sites[site_name]['active'] = False
            logging.info(f"❌ Site {site_name} desabilitado")
        else:
            logging.warning(f"⚠️ Site {site_name} não encontrado")

    def list_sites_status(self):
        """Lista status de todos os sites"""
        logging.info("📋 STATUS DOS SITES:")
        for site_name, config in self.sites.items():
            status = "✅ ATIVO" if config.get('active', True) else "❌ INATIVO"
            logging.info(f"  {site_name}: {status}")

    def run(self):
        """Executa a busca completa com tratamento de erros melhorado"""
        logging.info("🏠 Iniciando busca de casas em São João del Rei...")
        logging.info(f"Critérios: Centro e Bairro Segredo, até R$ {self.max_price:,.2f}")
        
        # Mostra status dos sites
        self.list_sites_status()
        
        results = self.search_all_sites()
        
        if results:
            logging.info(f"✅ Encontradas {len(results)} propriedades que atendem aos critérios!")
            
            # Remove duplicatas baseado na URL
            unique_results = []
            seen_urls = set()
            seen_titles = set()
            
            for result in results:
                # Remove duplicatas por URL ou título similar
                url_key = result['url'] if result['url'] else f"no-url-{len(unique_results)}"
                title_key = result['title'].lower()
                
                if url_key not in seen_urls and title_key not in seen_titles:
                    unique_results.append(result)
                    seen_urls.add(url_key)
                    seen_titles.add(title_key)
            
            logging.info(f"📊 {len(unique_results)} propriedades únicas após remoção de duplicatas")
            
            self.save_results(unique_results)
            
            # Exibe resumo melhorado
            print("\n" + "="*70)
            print("🏠 RESUMO DA BUSCA - SÃO JOÃO DEL REI")
            print("="*70)
            print(f"📍 Localização: Centro e Bairro Segredo")
            print(f"💰 Orçamento: Até R$ {self.max_price:,.2f}")
            print(f"🏘️ Imóveis encontrados: {len(unique_results)}")
            
            if unique_results:
                min_price = min(r['price'] for r in unique_results)
                max_price = max(r['price'] for r in unique_results)
                avg_price = sum(r['price'] for r in unique_results) / len(unique_results)
                
                print(f"💵 Menor preço: R$ {min_price:,.2f}")
                print(f"💰 Maior preço: R$ {max_price:,.2f}")
                print(f"📊 Preço médio: R$ {avg_price:,.2f}")
                
                # Agrupa por site
                sites_count = {}
                for result in unique_results:
                    site = result['site']
                    sites_count[site] = sites_count.get(site, 0) + 1
                
                print(f"\n🌐 Por site:")
                for site, count in sorted(sites_count.items(), key=lambda x: x[1], reverse=True):
                    print(f"  • {site}: {count} imóveis")
            
            print("\n" + "="*70)
            print("🏘️ IMÓVEIS ENCONTRADOS:")
            print("="*70)
            
            for i, prop in enumerate(sorted(unique_results, key=lambda x: x['price']), 1):
                print(f"\n{i:2d}. {prop['title']}")
                print(f"    💰 {prop['price_formatted']}")
                print(f"    📍 {prop['address']}")
                print(f"    🌐 {prop['site']}")
                if prop['url'] and prop['url'] != prop.get('base_url', ''):
                    print(f"    🔗 {prop['url']}")
                
        else:
            logging.info("❌ Nenhuma propriedade encontrada com os critérios especificados.")
            print("\n" + "="*50)
            print("❌ NENHUM IMÓVEL ENCONTRADO")
            print("="*50)
            print("\n💡 Possíveis motivos:")
            print("• Sites bloquearam o acesso (erro 403)")
            print("• Estrutura dos sites mudou")
            print("• Não há imóveis disponíveis nos critérios")
            print("• Sites estão temporariamente inacessíveis")
            print("\n🔧 Sugestões:")
            print("• Tente novamente em alguns minutos")
            print("• Verifique se os sites estão funcionando no navegador")
            print("• Considere aumentar o valor máximo")
            print("• Execute: finder.enable_site('olx') para tentar sites desabilitados")

def main():
    """Função principal com opções avançadas"""
    import sys
    
    finder = HouseFinder()
    
    # Opções via linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == '--enable-all':
            for site_name in finder.sites.keys():
                finder.enable_site(site_name)
            print("🔓 Todos os sites habilitados (incluindo os com possíveis bloqueios)")
        elif sys.argv[1] == '--list-sites':
            finder.list_sites_status()
            return
        elif sys.argv[1] == '--help':
            print("🏠 Buscador de Casas - São João del Rei")
            print("\nOpções:")
            print("  --enable-all    Habilita todos os sites (inclusive bloqueados)")
            print("  --list-sites    Lista status de todos os sites")
            print("  --help          Mostra esta ajuda")
            return
    
    finder.run()

if __name__ == "__main__":
    main()
