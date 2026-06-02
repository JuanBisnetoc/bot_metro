import requests
import json

print("🔍 Testando API CCM ARTESP...\n")

url = "https://ccm.artesp.sp.gov.br/metroferroviario/api/status/"

try:
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}\n")
    
    dados = response.json()
    
    print("=" * 80)
    print("RESPOSTA COMPLETA DA API (JSON):")
    print("=" * 80)
    print(json.dumps(dados, indent=2, ensure_ascii=False))
    print("\n")
    
    print("=" * 80)
    print("ESTRUTURA DOS DADOS:")
    print("=" * 80)
    print(f"Tipo: {type(dados)}")
    print(f"Chaves principais: {list(dados.keys())}")
    print("\n")
    
    # Procura por arrays/listas
    for chave, valor in dados.items():
        print(f"Chave '{chave}':")
        print(f"  - Tipo: {type(valor)}")
        if isinstance(valor, list) and len(valor) > 0:
            print(f"  - Quantidade de items: {len(valor)}")
            print(f"  - Primeiro item: {json.dumps(valor[0], indent=4, ensure_ascii=False)}")
        elif isinstance(valor, dict):
            print(f"  - Sub-chaves: {list(valor.keys())}")
        print()

except requests.exceptions.Timeout:
    print("❌ Timeout ao conectar")
except requests.exceptions.ConnectionError:
    print("❌ Erro de conexão")
except json.JSONDecodeError:
    print("❌ Resposta não é JSON válido")
    print(f"Conteúdo: {response.text[:500]}")
except Exception as e:
    print(f"❌ Erro: {e}")