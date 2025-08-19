# 🏠 Buscador de Casas - São João del Rei

Programa Python para buscar casas à venda no centro e bairro Segredo de São João del Rei, com preço máximo de R$ 350.000.

## 🎯 Funcionalidades

- ✅ Busca automatizada em múltiplos sites de imóveis
- 🎯 Foco no centro e bairro Segredo de São João del Rei
- 💰 Filtro por preço máximo (R$ 350.000)
- 📊 Exportação em JSON, CSV e HTML
- 🔄 Remoção automática de duplicatas
- 📝 Log detalhado das operações

## 🌐 Sites Suportados

- **VivaReal** - Portal nacional de imóveis
- **ZapImóveis** - Plataforma de anúncios imobiliários
- **OLX** - Classificados online

## 📋 Pré-requisitos

- Python 3.7 ou superior
- Conexão com internet

## 🚀 Instalação e Uso

### 1. Clone ou baixe os arquivos

```bash
git clone <seu-repositorio>
cd house-finder-sjdr
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Execute o programa

```bash
python house_finder.py
```

## 📁 Arquivos Gerados

O programa gera automaticamente:

- **`casas_sjdr.json`** - Dados em formato JSON
- **`casas_sjdr.csv`** - Planilha para Excel/Google Sheets  
- **`casas_sjdr.html`** - Relatório visual navegável
- **`house_finder.log`** - Log das operações

## ⚙️ Configuração

Para personalizar a busca, edite as variáveis no arquivo `house_finder.py`:

```python
class HouseFinder:
    def __init__(self):
        self.max_price = 350000  # Preço máximo em R$
        self.target_neighborhoods = ['centro', 'segredo', 'bairro segredo']
        self.city = 'são joão del rei'
```

## 📊 Exemplo de Saída

```
🏠 RESUMO DA BUSCA
============================================================

1. Casa 3 quartos - Centro Histórico
   💰 R$ 280.000,00
   📍 Rua Getúlio Vargas, Centro - São João del Rei
   🌐 Vivareal
   🔗 https://...

2. Sobrado 2 quartos - Bairro Segredo
   💰 R$ 320.000,00
   📍 Rua das Flores, Segredo - São João del Rei
   🌐 Zapimoveis
   🔗 https://...
```

## 🛠️ Personalização

### Adicionar Novos Sites

Para adicionar um novo site, inclua a configuração no dicionário `self.sites`:

```python
'novo_site': {
    'base_url': 'https://exemplo.com.br',
    'search_url': 'https://exemplo.com.br/busca/',
    'selectors': {
        'property': '.card-imovel',
        'title': '.titulo',
        'price': '.preco',
        'address': '.endereco',
        'link': 'a'
    }
}
```

### Modificar Critérios de Busca

- **Preço máximo**: Altere `self.max_price`
- **Bairros**: Modifique `self.target_neighborhoods`
- **Cidade**: Ajuste `self.city`

## 🚨 Considerações Importantes

- **Rate Limiting**: O programa inclui pausas entre requisições para evitar bloqueios
- **Sites Dinâmicos**: Alguns sites podem usar JavaScript para carregar conteúdo
- **Estrutura HTML**: Sites podem alterar sua estrutura, necessitando ajustes nos seletores
- **Termos de Uso**: Respeite sempre os termos de uso dos sites

## 📈 Possíveis Melhorias

- [ ] Integração com APIs oficiais dos sites
- [ ] Notificações via email/WhatsApp
- [ ] Interface web com Flask/Django
- [ ] Banco de dados para histórico
- [ ] Análise de preços e tendências
- [ ] Filtros adicionais (área, quartos, etc.)

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

## ⚖️ Disclaimer

Este programa é apenas para fins educacionais e de pesquisa. Sempre respeite os termos de uso dos sites e considere usar APIs oficiais quando disponíveis.

---

**Desenvolvido para facilitar a busca de imóveis em São João del Rei, MG** 🏡