import random
import requests
from bs4 import BeautifulSoup
from database import atualizar_status_linha

CCM_API_URL = "https://ccm.artesp.sp.gov.br/metroferroviario/api/status/"
CPTM_API_URL = "http://apps.cptm.sp.gov.br:8080/AppMobileService/api/DiretoCPTMV2/"

# Mapeamento de LinhaId da API CPTM para nome exibido
CPTM_LINHAS = {
    10: "Linha 10-Turquesa",
    11: "Linha 11-Coral",
    12: "Linha 12-Safira",
    13: "Linha 13-Jade",
}

CPTM_OPERADORA = "CPTM - Companhia Paulista de Trens Metropolitanos"

_EMOJI = {"normal": "✅", "atencao": "🟡", "parada": "🔴"}


def _mapear_ccm(classificacao: str, situacao: str, descricao: str) -> tuple[str, str]:
    """Converte campos da API CCM para status interno."""
    if classificacao == "operacional":
        return "normal", ""
    # classificacao pode ser: "nao_operacional", "paralisada", "com_ocorrencias", etc.
    if classificacao in ("nao_operacional", "paralisada"):
        return "parada", situacao or descricao
    return "atencao", situacao or descricao


def _mapear_cptm(status_str: str, descricao_api: str) -> tuple[str, str]:
    """Converte campo Status da API CPTM para status interno."""
    s = status_str.lower()
    if "normal" in s:
        return "normal", ""
    if "paralisada" in s or "encerrada" in s:
        return "parada", descricao_api or status_str
    # Velocidade reduzida, via única, serviço parcial, etc.
    return "atencao", descricao_api or status_str


def buscar_ccm_api() -> bool:
    """Busca status de todas as linhas pela API JSON do CCM ARTESP."""
    try:
        r = requests.get(CCM_API_URL, timeout=10)
        if r.status_code != 200:
            print(f"❌ CCM API retornou HTTP {r.status_code}")
            return False

        dados = r.json()
        count = 0
        for empresa in dados.get("empresas", []):
            for linha in empresa.get("linhas", []):
                s = linha["status"]
                status, descricao = _mapear_ccm(
                    s["classificacao"],
                    s.get("situacao", ""),
                    s.get("descricao", ""),
                )
                atualizar_status_linha(
                    nome_linha=linha["nome"],
                    status=status,
                    operadora=empresa["nome"],
                    descricao=descricao,
                )
                count += 1
                print(f"  {_EMOJI.get(status, '❓')} {linha['nome']} ({empresa['nome']}): {status}")

        if count > 0:
            print(f"\n✅ CCM API: {count} linhas atualizadas!")
            return True

        print("⚠️ CCM API: nenhuma linha retornada")
        return False

    except Exception as e:
        print(f"❌ CCM API erro: {e}")
        return False


def buscar_cptm_api() -> bool:
    """Busca linhas CPTM pela API do app oficial da CPTM (dados mais recentes)."""
    try:
        r = requests.get(CPTM_API_URL, timeout=10)
        if r.status_code != 200:
            print(f"❌ CPTM API retornou HTTP {r.status_code}")
            return False

        dados = r.json()
        count = 0
        for item in dados:
            linha_id = item.get("LinhaId")
            nome = CPTM_LINHAS.get(linha_id, f"Linha {linha_id}")
            status, descricao = _mapear_cptm(
                item.get("Status", ""),
                item.get("Descricao", ""),
            )
            atualizar_status_linha(
                nome_linha=nome,
                status=status,
                operadora=CPTM_OPERADORA,
                descricao=descricao,
            )
            count += 1
            print(f"  {_EMOJI.get(status, '❓')} {nome}: {status}")

        if count > 0:
            print(f"\n✅ CPTM API: {count} linhas atualizadas!")
            return True

        print("⚠️ CPTM API: nenhuma linha retornada")
        return False

    except Exception as e:
        print(f"❌ CPTM API erro: {e}")
        return False


def atualizar_status_real():
    """
    Atualiza status usando APIs oficiais.

    Prioridade:
    1. CCM ARTESP JSON API  → todas as linhas (Metrô, CPTM, ViaQuatro, ViaMobilidade, TIC)
    2. CPTM App API         → substitui linhas CPTM (10-13) com dados mais recentes
    3. HTML scraper CCM     → fallback se a API JSON falhar
    4. Dados simulados      → último recurso
    """
    print("🔄 Buscando dados das APIs oficiais...\n")

    ccm_ok = buscar_ccm_api()

    if ccm_ok:
        print("\n🔄 Suplementando linhas CPTM com API própria...\n")
        buscar_cptm_api()
    else:
        print("\n⚠️ CCM API indisponível — tentando scraper HTML...\n")
        if not scrape_ccm_html():
            print("\n⚠️ Scraper HTML também falhou — usando dados simulados...\n")
            atualizar_status_simulado()


def scrape_ccm_html() -> bool:
    """Fallback: coleta status pela página HTML do CCM ARTESP."""
    try:
        url = "https://ccm.artesp.sp.gov.br/metroferroviario/status-linhas/"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            print(f"❌ CCM HTML retornou HTTP {r.status_code}")
            return False

        soup = BeautifulSoup(r.text, "html.parser")
        operadora_atual = "Desconhecida"
        count = 0

        for elem in soup.find_all(["h2", "h3"]):
            if elem.name == "h2":
                operadora_atual = elem.get_text(strip=True)
                continue

            linha_nome = elem.get_text(strip=True)
            if not linha_nome.startswith("Linha"):
                continue
            status = "normal"
            descricao = ""

            for sib in elem.find_all_next():
                if sib.name == "h3":
                    break
                texto = sib.get_text(strip=True).lower()
                if "operação normal" in texto:
                    status = "normal"
                    break
                if "com ocorrências" in texto or "atividade programada" in texto:
                    status = "atencao"
                    descricao = sib.get_text(strip=True)
                    break
                if "parada" in texto or "encerrada" in texto:
                    status = "parada"
                    descricao = sib.get_text(strip=True)
                    break

            atualizar_status_linha(linha_nome, status, operadora_atual, descricao)
            count += 1
            print(f"  {_EMOJI.get(status, '❓')} {linha_nome} ({operadora_atual}): {status}")

        if count > 0:
            print(f"\n✅ CCM HTML: {count} linhas atualizadas!")
            return True

        print("⚠️ CCM HTML: nenhuma linha encontrada — estrutura pode ter mudado")
        return False

    except Exception as e:
        print(f"❌ CCM HTML erro: {e}")
        return False


def atualizar_status_simulado():
    """Último recurso: status aleatório para todas as linhas."""
    linhas = {
        "Linha 1-Azul": "Metrô de São Paulo",
        "Linha 2-Verde": "Metrô de São Paulo",
        "Linha 3-Vermelha": "Metrô de São Paulo",
        "Linha 4-Amarela": "ViaQuatro",
        "Linha 5-Lilás": "ViaMobilidade 5",
        "Linha 7-Rubi": "TIC Trens",
        "Linha 8-Diamante": "ViaMobilidade 8 e 9",
        "Linha 9-Esmeralda": "ViaMobilidade 8 e 9",
        "Linha 10-Turquesa": CPTM_OPERADORA,
        "Linha 11-Coral": CPTM_OPERADORA,
        "Linha 12-Safira": CPTM_OPERADORA,
        "Linha 13-Jade": CPTM_OPERADORA,
        "Linha 15-Prata": "Metrô de São Paulo",
    }
    descricoes = {"normal": "", "atencao": "A linha está enfrentando atrasos.", "parada": "A linha está parada."}
    for linha, operadora in linhas.items():
        status = random.choice(["normal", "atencao", "parada"])
        atualizar_status_linha(linha, status, operadora, descricoes[status])
    print("✅ Status atualizado com dados simulados!")
