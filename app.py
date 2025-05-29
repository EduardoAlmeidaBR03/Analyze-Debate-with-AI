from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

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
    """Obtém a transcrição do vídeo em português usando a YouTube Transcript API"""
    try:
        # Tentar obter transcrição em português
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR'])
        
        # Concatenar todas as partes da transcrição
        full_transcript = ""
        for entry in transcript_list:
            full_transcript += entry['text'] + " "
        
        return full_transcript.strip()
        
    except Exception as e:
        print(f"Erro ao obter transcrição em português: {e}")
        return None

def get_available_transcripts(video_id):
    """Verifica se há transcrições em português disponíveis"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        portuguese_transcripts = []
        
        for transcript in transcript_list:
            if transcript.language_code in ['pt', 'pt-BR']:
                portuguese_transcripts.append({
                    'language': transcript.language,
                    'language_code': transcript.language_code,
                    'is_generated': transcript.is_generated,
                    'is_translatable': transcript.is_translatable
                })
        
        return portuguese_transcripts
        
    except Exception as e:
        print(f"Erro ao listar transcrições em português: {e}")
        return []

def get_youtube_info_alternative(youtube_url):
    """Método alternativo para obter informações do YouTube"""
    try:
        from pytube import YouTube
        
        yt = YouTube(youtube_url)
        
        # Obter informações básicas
        info = {
            'title': yt.title,
            'description': yt.description,
            'length': yt.length,
            'views': yt.views,
            'author': yt.author
        }
        
        return info
        
    except Exception as e:
        print(f"Erro ao obter informações do YouTube: {e}")
        return None

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
        4. Me forneça as 50 palavras mais utilizadas e sua frequencia para eu gerar uma nuvem de palavras

        Responda em português de forma estruturada e detalhada.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Erro ao analisar com Gemini: {e}")
        return f"Erro na análise: {str(e)}"

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

        return jsonify({
            'status': 'success',
            'video_info': video_info,
            'transcript_source': transcript_source,
            'available_transcripts': available_transcripts,
            'transcript_length': len(transcript),
            'analysis': analysis,
            'video_id': video_id
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
            '/health': 'GET - Status da API'
        }
    })

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
            '/health': {
                'method': 'GET', 
                'description': 'Verifica status da API'
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
            '/health'
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
            '/health': ['GET']
        }
    }), 405

if __name__ == '__main__':
    print("🚀 Iniciando API de Análise de Vídeos do YouTube...")
    print("📍 Endpoints disponíveis:")
    print("   GET  / - Informações da API")
    print("   POST /analyze-youtube - Analisar vídeo")
    print("   GET  /health - Status da API")
    print("🌐 Acesse: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)