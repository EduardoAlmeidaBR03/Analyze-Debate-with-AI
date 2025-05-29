# API de Análise de Vídeos do YouTube

Esta API permite analisar vídeos do YouTube obtendo a transcrição através do Kome.ai e gerando uma análise detalhada usando o Gemini AI.

## Funcionalidades

- 📹 Extração de informações de vídeos do YouTube
- 📝 Obtenção de transcrições via Kome.ai
- 🤖 Análise inteligente do conteúdo usando Gemini AI
- 🔍 Fallback para descrição do YouTube caso a transcrição não esteja disponível

## Instalação

1. Clone ou baixe os arquivos do projeto
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure a chave da API do Gemini no arquivo `.env` (já configurada)

## Como usar

### 1. Iniciar a API

```bash
python app.py
```

A API será executada em `http://localhost:5000`

### 2. Fazer requisições

#### Endpoint principal: `/analyze-youtube`

**Método:** POST  
**Content-Type:** application/json

**Exemplo de requisição:**
```json
{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Exemplo de resposta:**
```json
{
    "status": "success",
    "video_info": {
        "title": "Título do Vídeo",
        "author": "Nome do Canal",
        "description": "Descrição do vídeo...",
        "length": 300,
        "views": 1000000
    },
    "transcript_source": "kome.ai",
    "analysis": "Análise detalhada gerada pelo Gemini...",
    "video_id": "VIDEO_ID"
}
```

#### Outros endpoints:

- `GET /` - Informações sobre a API
- `GET /health` - Verificação de saúde da API

### 3. Testar a API

Execute o arquivo de teste:
```bash
python test_api.py
```

## Como funciona

1. **Extração do ID do vídeo**: A API extrai o ID do vídeo da URL fornecida
2. **Obtenção de informações**: Usa PyTube para obter metadados do vídeo
3. **Transcrição**: Tenta obter a transcrição via Kome.ai
4. **Fallback**: Se não conseguir a transcrição, usa a descrição do YouTube
5. **Análise**: Envia o conteúdo para o Gemini AI para análise detalhada

## Estrutura da Análise

A análise do Gemini inclui:

1. Resumo conciso do conteúdo
2. Principais pontos abordados
3. Argumentos apresentados
4. Conclusões e mensagens principais
5. Tom e estilo da discussão
6. Público-alvo aparente
7. Qualidade e credibilidade das informações

## Limitações

- A integração com Kome.ai pode precisar de ajustes dependendo da API deles
- Alguns vídeos podem ter restrições de acesso
- A qualidade da análise depende da qualidade da transcrição/descrição

## Arquivos do Projeto

- `app.py` - Aplicação principal da API
- `requirements.txt` - Dependências do Python
- `.env` - Configurações de ambiente (chave do Gemini)
- `test_api.py` - Script de teste da API
- `README.md` - Documentação

## Exemplo de Uso com cURL

```bash
curl -X POST http://localhost:5000/analyze-youtube \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

## Exemplo de Uso com Python

```python
import requests

url = "http://localhost:5000/analyze-youtube"
data = {"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}

response = requests.post(url, json=data)
result = response.json()

print(result['analysis'])
```