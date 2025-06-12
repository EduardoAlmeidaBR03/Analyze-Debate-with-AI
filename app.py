from flask import Flask, request, jsonify, render_template_string, send_from_directory
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
# Novos imports para wordcloud
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  
import io
import base64
from collections import Counter
import string

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurar Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
# Atualizar para o modelo mais recente
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_video_id(youtube_url):
    """Extrai o ID do vídeo do YouTube da URL"""
    # Padrões comuns de URLs do YouTube
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    return None

def get_transcript_from_youtube_api(video_id):
    """Obtém a transcrição do vídeo usando a YouTube Transcript API"""
    try:
        # Tentar obter transcrição em português primeiro
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR'])
        except:
            # Se não houver em português, tentar em inglês
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except:
                # Se não houver em inglês, pegar qualquer idioma disponível
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Concatenar todas as partes da transcrição
        full_transcript = ""
        for entry in transcript_list:
            full_transcript += entry['text'] + " "
        
        return full_transcript.strip()
        
    except Exception as e:
        print(f"Erro ao obter transcrição da YouTube Transcript API: {e}")
        return None

def get_available_transcripts(video_id):
    """Obtém lista de idiomas disponíveis para transcrição"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = []
        
        for transcript in transcript_list:
            available_languages.append({
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable
            })
        
        return available_languages
        
    except Exception as e:
        print(f"Erro ao listar transcrições disponíveis: {e}")
        return []

def get_youtube_info_alternative(youtube_url):
    """Método alternativo para obter informações do YouTube usando múltiplas abordagens"""
    
    # Tentar primeiro com PyTube
    try:
        from pytube import YouTube
        print(f"Tentando PyTube para: {youtube_url}")
        
        yt = YouTube(youtube_url)
        
        if yt.title and yt.author:  # Se conseguiu obter as informações básicas
            info = {
                'title': yt.title,
                'description': yt.description or 'Descrição não disponível',
                'length': yt.length or 0,
                'views': yt.views or 0,
                'author': yt.author
            }
            print(f"PyTube funcionou: {info['title']}")
            return info
            
    except Exception as e:
        print(f"PyTube falhou: {e}")
    
    # Método alternativo: extrair informações do HTML da página
    try:
        print("Tentando método alternativo (scraping)")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(youtube_url, headers=headers, timeout=10)
        html_content = response.text
        
        # Extrair título
        title_match = re.search(r'"title":"([^"]+)"', html_content)
        title = title_match.group(1) if title_match else "Título não disponível"
        
        # Extrair autor/canal
        author_match = re.search(r'"author":"([^"]+)"', html_content) or re.search(r'"channelName":"([^"]+)"', html_content)
        author = author_match.group(1) if author_match else "Canal não disponível"
        
        # Extrair duração (em segundos)
        duration_match = re.search(r'"lengthSeconds":"(\d+)"', html_content)
        duration = int(duration_match.group(1)) if duration_match else 0
        
        # Extrair visualizações
        views_match = re.search(r'"viewCount":"(\d+)"', html_content)
        views = int(views_match.group(1)) if views_match else 0
        
        # Extrair descrição
        desc_match = re.search(r'"shortDescription":"([^"]*)"', html_content)
        description = desc_match.group(1) if desc_match else "Descrição não disponível"
        
        info = {
            'title': title,
            'description': description,
            'length': duration,
            'views': views,
            'author': author
        }
        
        print(f"Scraping funcionou: {info['title']}")
        return info
        
    except Exception as e:
        print(f"Método alternativo falhou: {e}")
    
    # Se tudo falhar, retornar informações básicas com base no ID do vídeo
    try:
        video_id = extract_video_id(youtube_url)
        return {
            'title': f'Vídeo do YouTube (ID: {video_id})',
            'description': 'Não foi possível obter a descrição',
            'length': 0,
            'views': 0,
            'author': 'Canal não identificado'
        }
    except:
        return {
            'title': 'Vídeo do YouTube',
            'description': 'Não foi possível obter informações',
            'length': 0,
            'views': 0,
            'author': 'Canal não identificado'
        }

def analyze_with_gemini(transcript, video_info=None):
    """Analisa a transcrição usando o Gemini AI"""
    try:
        prompt = f"""
        Analise o seguinte conteúdo de vídeo do YouTube e forneça uma análise detalhada:

        {f"Título: {video_info.get('title', 'N/A')}" if video_info else ""}
        {f"Autor: {video_info.get('author', 'N/A')}" if video_info else ""}
        {f"Descrição: {video_info.get('description', 'N/A')}" if video_info else ""}

        Transcrição/Conteúdo:
        {transcript}

        Por favor, forneça:
        1. Um resumo conciso do que foi discutido
        2. Elaborar uma análise crítica dos pontos positivos das falas de Adriana
        3. . Elaborar uma análise crítica dos pontos positivos das falas de Lodovico

        Responda em português de forma estruturada e detalhada.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Erro ao analisar com Gemini: {e}")
        return f"Erro na análise: {str(e)}"

def clean_text_for_wordcloud(text):
    """Limpa e processa o texto para gerar a nuvem de palavras"""
    if not text:
        return ""
    
    # Converter para minúsculas
    text = text.lower()
    
    # Remover pontuação
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remover números
    text = re.sub(r'\d+', '', text)
    
    # Remover palavras muito comuns em português (stop words)
    stop_words = {
        'música','o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 'dos', 'das',
        'para', 'por', 'com', 'em', 'no', 'na', 'nos', 'nas', 'e', 'ou', 'mas', 'que',
        'se', 'não', 'eu', 'tu', 'ele', 'ela', 'nós', 'vós', 'eles', 'elas', 'meu',
        'minha', 'meus', 'minhas', 'seu', 'sua', 'seus', 'suas', 'nosso', 'nossa',
        'nossos', 'nossas', 'este', 'esta', 'estes', 'estas', 'esse', 'essa', 'esses',
        'essas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'como', 'quando', 'onde',
        'porque', 'quanto', 'qual', 'quais', 'quem', 'muito', 'mais', 'menos', 'bem',
        'já', 'ainda', 'só', 'também', 'até', 'então', 'sobre', 'depois', 'antes',
        'aqui', 'ali', 'lá', 'sim', 'aí', 'né', 'tá', 'vai', 'é', 'ser', 'estar',
        'ter', 'haver', 'fazer', 'ver', 'dar', 'dizer', 'ir', 'vir', 'saber', 'poder'
    }
    
    # Dividir em palavras e filtrar
    words = text.split()
    filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]
    
    return ' '.join(filtered_words)

def extract_speaker_text(transcript, speaker_name):
    """Extrai o texto falado por um participante específico"""
    if not transcript or not speaker_name:
        return ""
    
    # Padrões para identificar falas do participante
    patterns = [
        rf'{re.escape(speaker_name)}\s*:(.+?)(?={re.escape("Adriana")}|{re.escape("Lodovico")}|\Z)',
        rf'{re.escape(speaker_name)}\s+(.+?)(?={re.escape("Adriana")}|{re.escape("Lodovico")}|\Z)',
        rf'{re.escape(speaker_name)}(.+?)(?={re.escape("Adriana")}|{re.escape("Lodovico")}|\Z)'
    ]
    
    speaker_text = ""
    
    # Tentar diferentes padrões para extrair as falas
    for pattern in patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE | re.DOTALL)
        if matches:
            speaker_text = " ".join(matches).strip()
            break
    
    # Se não encontrar padrões específicos, tentar busca por contexto
    if not speaker_text:
        # Dividir o texto em parágrafos/seções
        sections = re.split(r'\n+', transcript)
        for section in sections:
            if speaker_name.lower() in section.lower():
                # Extrair texto após o nome do participante
                speaker_match = re.search(rf'{re.escape(speaker_name)}\s*:?\s*(.+)', section, re.IGNORECASE)
                if speaker_match:
                    speaker_text += " " + speaker_match.group(1)
    
    return speaker_text.strip()

def generate_wordcloud(text, colormap='viridis', title_suffix=""):
    """Gera uma nuvem de palavras e retorna como base64"""
    try:
        # Limpar o texto
        clean_text = clean_text_for_wordcloud(text)
        
        if not clean_text:
            return None, []
        
        # Contar frequência das palavras
        words = clean_text.split()
        word_freq = Counter(words)
        
        # Pegar as 50 palavras mais comuns
        top_words = word_freq.most_common(50)
        
        # Criar a nuvem de palavras
        wordcloud = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            max_words=50,
            colormap=colormap,
            relative_scaling=0.5,
            random_state=42
        ).generate(clean_text)
        
        # Salvar como imagem em memória
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        
        # Adicionar título se fornecido
        if title_suffix:
            plt.title(f'Nuvem de Palavras - {title_suffix}', fontsize=16, pad=20)
        
        # Converter para base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', 
                   dpi=150, facecolor='white', edgecolor='none')
        img_buffer.seek(0)
        
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()  # Liberar memória
        
        return img_str, top_words
        
    except Exception as e:
        print(f"Erro ao gerar nuvem de palavras: {e}")
        return None, []

def generate_speaker_wordclouds(transcript):
    """Gera nuvens de palavras separadas para Adriana e Lodovico"""
    wordclouds = {}
    
    # Extrair texto de cada participante
    adriana_text = extract_speaker_text(transcript, "Adriana")
    lodovico_text = extract_speaker_text(transcript, "Lodovico")
    
    print(f"Texto extraído da Adriana: {len(adriana_text)} caracteres")
    print(f"Texto extraído do Lodovico: {len(lodovico_text)} caracteres")
    
    # Gerar nuvem de palavras para Adriana
    if adriana_text:
        adriana_wordcloud, adriana_freq = generate_wordcloud(
            adriana_text, 
            colormap='Reds', 
            title_suffix="Adriana"
        )
        if adriana_wordcloud:
            wordclouds['adriana'] = {
                'image': adriana_wordcloud,
                'word_frequencies': adriana_freq,
                'text_length': len(adriana_text)
            }
    
    # Gerar nuvem de palavras para Lodovico
    if lodovico_text:
        lodovico_wordcloud, lodovico_freq = generate_wordcloud(
            lodovico_text, 
            colormap='Blues', 
            title_suffix="Lodovico"
        )
        if lodovico_wordcloud:
            wordclouds['lodovico'] = {
                'image': lodovico_wordcloud,
                'word_frequencies': lodovico_freq,
                'text_length': len(lodovico_text)
            }
    
    return wordclouds

@app.route('/analyze-youtube', methods=['POST', 'GET'])
def analyze_youtube_video():
    """Endpoint principal para analisar vídeos do YouTube"""
    
    # Se for GET, mostrar formulário de exemplo
    if request.method == 'GET':
        return jsonify({
            'message': 'Endpoint para análise de vídeos do YouTube',
            'method': 'POST',
            'content_type': 'application/json',
            'example_body': {
                'youtube_url': 'https://www.youtube.com/watch?v=VIDEO_ID'
            },
            'usage': 'Envie uma requisição POST com a URL do YouTube no body JSON',
            'transcript_source': 'YouTube Transcript API'
        })
    
    try:
        data = request.get_json()
        
        if not data or 'youtube_url' not in data:
            return jsonify({
                'error': 'URL do YouTube é obrigatória',
                'status': 'error',
                'example': {
                    'youtube_url': 'https://www.youtube.com/watch?v=VIDEO_ID'
                }
            }), 400

        youtube_url = data['youtube_url']
        
        # Validar URL do YouTube
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({
                'error': 'URL do YouTube inválida',
                'status': 'error',
                'received_url': youtube_url
            }), 400

        # Obter informações do vídeo
        video_info = get_youtube_info_alternative(youtube_url)
        
        # Obter lista de idiomas disponíveis para transcrição
        available_transcripts = get_available_transcripts(video_id)
        
        # Tentar obter transcrição usando YouTube Transcript API
        transcript = get_transcript_from_youtube_api(video_id)
        
        transcript_source = 'youtube_transcript_api'
        
        # Se não conseguir transcrição, usar descrição do YouTube como fallback
        if not transcript and video_info and video_info.get('description'):
            transcript = video_info['description']
            transcript_source = 'youtube_description'
        elif not transcript:
            return jsonify({
                'error': 'Não foi possível obter transcrição ou descrição do vídeo',
                'status': 'error',
                'video_info': video_info,
                'available_transcripts': available_transcripts,
                'message': 'Este vídeo pode não ter legendas/transcrição disponível'
            }), 400

        # Analisar com Gemini
        analysis = analyze_with_gemini(transcript, video_info)
        
        # Gerar nuvem de palavras geral
        wordcloud_img, word_frequencies = generate_wordcloud(transcript, 'viridis', 'Geral')
        
        # Gerar nuvens de palavras por participante
        speaker_wordclouds = generate_speaker_wordclouds(transcript)

        return jsonify({
            'status': 'success',
            'video_info': video_info,
            'transcript_source': transcript_source,
            'available_transcripts': available_transcripts,
            'transcript_length': len(transcript),
            'transcript': transcript,  # Adicionando a transcrição na resposta
            'analysis': analysis,
            'video_id': video_id,
            'wordcloud': wordcloud_img,  # Imagem da nuvem de palavras geral em base64
            'word_frequencies': word_frequencies,  # Lista das palavras mais frequentes gerais
            'speaker_wordclouds': speaker_wordclouds  # Nuvens de palavras por participante
        })

    except Exception as e:
        return jsonify({
            'error': f'Erro interno: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/transcript-only/<video_id>', methods=['GET'])
def get_transcript_only(video_id):
    """Endpoint para obter apenas a transcrição de um vídeo"""
    try:
        # Obter transcrição
        transcript = get_transcript_from_youtube_api(video_id)
        available_transcripts = get_available_transcripts(video_id)
        
        if not transcript:
            return jsonify({
                'error': 'Transcrição não disponível para este vídeo',
                'status': 'error',
                'video_id': video_id,
                'available_transcripts': available_transcripts
            }), 404
        
        return jsonify({
            'status': 'success',
            'video_id': video_id,
            'transcript': transcript,
            'transcript_length': len(transcript),
            'available_transcripts': available_transcripts
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Erro ao obter transcrição: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificação de saúde da API"""
    return jsonify({
        'status': 'healthy',
        'message': 'API de análise de vídeos do YouTube está funcionando',
        'transcript_method': 'YouTube Transcript API',
        'endpoints': {
            '/': 'GET - Informações da API',
            '/analyze-youtube': 'POST - Analisar vídeo do YouTube',
            '/transcript-only/<video_id>': 'GET - Obter apenas transcrição',
            '/wordcloud/<video_id>': 'GET - Gerar nuvem de palavras',
            '/health': 'GET - Status da API',
            '/frontend': 'GET - Interface web'
        }
    })

@app.route('/frontend')
def frontend():
    """Serve the frontend HTML page"""
    with open('index.html', 'r', encoding='utf-8') as file:
        return file.read()

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files if needed"""
    return send_from_directory('static', filename)

@app.route('/', methods=['GET'])
def home():
    """Endpoint raiz com instruções de uso"""
    return jsonify({
        'message': 'API de Análise de Vídeos do YouTube',
        'version': '2.0',
        'transcript_method': 'YouTube Transcript API',
        'endpoints': {
            '/analyze-youtube': {
                'method': 'POST',
                'description': 'Analisa um vídeo do YouTube',
                'body': {
                    'youtube_url': 'URL do vídeo do YouTube'
                }
            },
            '/transcript-only/<video_id>': {
                'method': 'GET',
                'description': 'Obtém apenas a transcrição de um vídeo',
                'example': '/transcript-only/dQw4w9WgXcQ'
            },
            '/wordcloud/<video_id>': {
                'method': 'GET',
                'description': 'Gera nuvem de palavras de um vídeo',
                'example': '/wordcloud/dQw4w9WgXcQ'
            },
            '/health': {
                'method': 'GET', 
                'description': 'Verifica status da API'
            },
            '/frontend': {
                'method': 'GET',
                'description': 'Interface web para análise de vídeos'
            }
        },
        'example_usage': {
            'url': 'http://localhost:5000/analyze-youtube',
            'method': 'POST',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': {
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint não encontrado',
        'available_endpoints': [
            '/',
            '/analyze-youtube',
            '/health',
            '/frontend'
        ]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Método não permitido',
        'message': 'Verifique o método HTTP e endpoint corretos',
        'endpoints': {
            '/': ['GET'],
            '/analyze-youtube': ['POST', 'GET'],
            '/health': ['GET'],
            '/frontend': ['GET']
        }
    }), 405

@app.route('/wordcloud/<video_id>', methods=['GET'])
def generate_wordcloud_only(video_id):
    """Endpoint para gerar apenas a nuvem de palavras de um vídeo"""
    try:
        # Obter transcrição
        transcript = get_transcript_from_youtube_api(video_id)
        
        if not transcript:
            return jsonify({
                'error': 'Transcrição não disponível para este vídeo',
                'status': 'error',
                'video_id': video_id
            }), 404
        
        # Gerar nuvem de palavras
        wordcloud_img, word_frequencies = generate_wordcloud(transcript)
        
        if not wordcloud_img:
            return jsonify({
                'error': 'Não foi possível gerar a nuvem de palavras',
                'status': 'error',
                'video_id': video_id
            }), 500
        
        return jsonify({
            'status': 'success',
            'video_id': video_id,
            'wordcloud': wordcloud_img,
            'word_frequencies': word_frequencies,
            'total_words': len(word_frequencies)
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Erro ao gerar nuvem de palavras: {str(e)}',
            'status': 'error'
        }), 500

if __name__ == '__main__':
    print("🚀 Iniciando API de Análise de Vídeos do YouTube...")
    print("📍 Endpoints disponíveis:")
    print("   GET  / - Informações da API")
    print("   GET  /frontend - Interface web")
    print("   POST /analyze-youtube - Analisar vídeo")
    print("   GET  /health - Status da API")
    print("🌐 Acesse a interface em: http://localhost:5000/frontend")
    app.run(debug=True, host='0.0.0.0', port=5000)