import requests
import json

# URL da API local
API_URL = "http://localhost:5000"

def test_api():
    """Testa a API com um vídeo do YouTube"""
    
    # Exemplo de URL do YouTube (substitua por uma URL real)
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll como exemplo
    
    # Dados para enviar
    data = {
        "youtube_url": youtube_url
    }
    
    try:
        # Fazer requisição para a API
        response = requests.post(f"{API_URL}/analyze-youtube", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Análise realizada com sucesso!")
            print(f"Status: {result['status']}")
            print(f"Título: {result.get('video_info', {}).get('title', 'N/A')}")
            print(f"Autor: {result.get('video_info', {}).get('author', 'N/A')}")
            print(f"Fonte da transcrição: {result.get('transcript_source', 'N/A')}")
            print(f"Tamanho da transcrição: {result.get('transcript_length', 0)} caracteres")
            print(f"Idiomas disponíveis: {len(result.get('available_transcripts', []))}")
            print("\n📊 Análise do Gemini:")
            print(result.get('analysis', 'Análise não disponível'))
        else:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(response.json())
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API. Certifique-se de que ela está rodando.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def test_transcript_only():
    """Testa endpoint de transcrição apenas"""
    video_id = "dQw4w9WgXcQ"  # Rick Roll
    
    try:
        response = requests.get(f"{API_URL}/transcript-only/{video_id}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Transcrição obtida com sucesso!")
            print(f"Video ID: {result['video_id']}")
            print(f"Tamanho da transcrição: {result['transcript_length']} caracteres")
            print(f"Idiomas disponíveis: {len(result.get('available_transcripts', []))}")
            print(f"Transcrição (primeiros 200 chars): {result['transcript'][:200]}...")
        else:
            print(f"❌ Erro na requisição de transcrição: {response.status_code}")
            print(response.json())
            
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def test_health():
    """Testa se a API está funcionando"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API está funcionando!")
            result = response.json()
            print(f"Método de transcrição: {result.get('transcript_method', 'N/A')}")
            print(result)
        else:
            print(f"❌ API retornou status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando. Execute 'python app.py' primeiro.")

if __name__ == "__main__":
    print("🧪 Testando a API de Análise de Vídeos do YouTube (YouTube Transcript API)\n")
    
    print("1. Testando se a API está funcionando...")
    test_health()
    
    print("\n2. Testando obtenção de transcrição apenas...")
    test_transcript_only()
    
    print("\n3. Testando análise completa de vídeo...")
    test_api()