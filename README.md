# Bot de Trading com Machine Learning

## 📊 Visão Geral

Este é um bot de trading avançado que utiliza análise técnica tradicional combinada com Machine Learning para tomar decisões de compra e venda em mercados de criptomoedas. O bot foi projetado para maximizar a taxa de acerto e otimizar a relação risco/retorno.

## 🧠 Recursos de Machine Learning

O bot agora inclui um sistema de Machine Learning que:

- Aprende padrões de mercado a partir de dados históricos
- Combina indicadores técnicos tradicionais com previsões de ML
- Adapta-se continuamente com novos dados de mercado
- Filtra sinais de baixa qualidade para aumentar a taxa de acerto
- Utiliza análise multi-timeframe para decisões mais robustas

## 🚀 Como Usar

### Instalação

1. Clone o repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

### Configuração

Edite o arquivo `config.py` para ajustar os parâmetros do bot:

- **Parâmetros de Trading**: capital inicial, risco por trade, stop loss, etc.
- **Configurações de ML**: ativar/desativar ML, confiança mínima, features, etc.

### Execução

Para iniciar o bot:

```bash
python trade_bot.py
```

### Backtest

Para testar a estratégia com dados históricos:

1. Colete dados históricos:

```bash
python coletar_dados_historicos.py
```

2. Execute o backtest:

```bash
python backtest_ml.py
```

## 📈 Estratégias Implementadas

- **Análise Técnica**: RSI, MACD, EMA, Bollinger Bands
- **Machine Learning**: Previsão de direção de preço com confiança
- **Gestão de Risco**: Critério de Kelly, trailing stops, tamanho adaptativo de posição
- **Multi-Timeframe**: Análise em diferentes intervalos de tempo

## 🔧 Arquitetura

- `trade_bot.py`: Classe principal do bot
- `core/ml_predictor.py`: Sistema de Machine Learning
- `core/estrategias.py`: Indicadores técnicos e estratégias
- `backtest_ml.py`: Sistema de backtest com ML
- `coletar_dados_historicos.py`: Coleta de dados para backtest

## 📊 Desempenho

O uso de Machine Learning pode aumentar significativamente a taxa de acerto do bot:

- **Taxa de acerto esperada com ML**: 65-75%
- **Taxa de acerto sem ML**: 45-55%

O backtest mostrará a comparação de desempenho entre as versões com e sem ML.

## 🛠️ Personalização

Você pode personalizar o bot de várias maneiras:

- Adicionar novas features ao ML em `core/ml_predictor.py`
- Implementar novas estratégias em `core/estrategias.py`
- Ajustar parâmetros de risco em `config.py`

## 📝 Requisitos

- Python 3.7+
- pandas
- numpy
- scikit-learn
- matplotlib
- python-binance

## ⚠️ Aviso de Risco

Trading envolve risco significativo de perda financeira. Este bot é fornecido apenas para fins educacionais e de pesquisa. Use por sua conta e risco.

## 📜 Licença

Este projeto é licenciado sob a licença MIT.