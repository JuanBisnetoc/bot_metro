import sqlite3
from datetime import datetime
from config import DB_PATH

def conectar_bd():
    #Conecta ao banco SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def criar_tabelas():
    #Cria tabelas do banco
    conn = conectar_bd()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS linhas (
            id INTEGER PRIMARY KEY,
            nome TEXT UNIQUE,
            operadora TEXT,
            status TEXT DEFAULT 'normal',
            ultima_atualizacao DATETIME,
            descricao_problema TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_status (
            id INTEGER PRIMARY KEY,
            linha_id INTEGER,
            status TEXT,
            data_hora DATETIME,
            FOREIGN KEY (linha_id) REFERENCES linhas(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            chat_id INTEGER PRIMARY KEY,
            data_inscricao DATETIME
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Tabelas criadas!")

def atualizar_status_linha(nome_linha, status, operadora, descricao=""):
    """Atualiza status de uma linha"""
    conn = conectar_bd()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        # Insert or update
        cursor.execute("""
            INSERT OR REPLACE INTO linhas (nome, operadora, status, ultima_atualizacao, descricao_problema)
            VALUES (?, ?, ?, ?, ?)
        """, (nome_linha, operadora, status, datetime.now(), descricao))
        
        # Registrar no histórico
        cursor.execute("SELECT id FROM linhas WHERE nome = ?", (nome_linha,))
        linha_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO historico_status (linha_id, status, data_hora)
            VALUES (?, ?, ?)
        """, (linha_id, status, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def obter_linhas_com_problema():
    """Retorna linhas com problemas"""
    conn = conectar_bd()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome, operadora, status, descricao_problema, ultima_atualizacao
            FROM linhas
            WHERE status != 'normal'
            ORDER BY ultima_atualizacao DESC
        """)
        resultados = cursor.fetchall()
        conn.close()
        return [dict(row) for row in resultados]
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def obter_todas_linhas():
    """Retorna todas as linhas"""
    conn = conectar_bd()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome, operadora, status, ultima_atualizacao
            FROM linhas
            ORDER BY nome
        """)
        resultados = cursor.fetchall()
        conn.close()
        return [dict(row) for row in resultados]
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def adicionar_usuario(chat_id: int) -> bool:
    conn = conectar_bd()
    if not conn:
        return False
    try:
        conn.execute(
            "INSERT OR IGNORE INTO usuarios (chat_id, data_inscricao) VALUES (?, ?)",
            (chat_id, datetime.now()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def remover_usuario(chat_id: int) -> bool:
    conn = conectar_bd()
    if not conn:
        return False
    try:
        conn.execute("DELETE FROM usuarios WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def usuario_inscrito(chat_id: int) -> bool:
    conn = conectar_bd()
    if not conn:
        return False
    try:
        row = conn.execute(
            "SELECT 1 FROM usuarios WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def obter_todos_usuarios() -> list[int]:
    conn = conectar_bd()
    if not conn:
        return []
    try:
        rows = conn.execute("SELECT chat_id FROM usuarios").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []


def verificar_e_notificar():
    """Retorna mensagem formatada com linhas com problema, ou None se tudo normal."""
    linhas_problema = obter_linhas_com_problema()
    if not linhas_problema:
        return None
    mensagem = "🚨 *Problemas Detectados no Metro/Trem:*\n\n"
    for linha in linhas_problema:
        emoji = "🟡" if linha["status"] == "atencao" else "🔴"
        mensagem += f"{emoji} {linha['nome']} ({linha['operadora']})\n"
        if linha["descricao_problema"]:
            mensagem += f"   └─ {linha['descricao_problema']}\n"
        mensagem += f"   └─ Atualizado: {linha['ultima_atualizacao']}\n\n"
    return mensagem


def obter_status_resumido():
    """Retorna resumo do status"""
    conn = conectar_bd()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'normal' THEN 1 ELSE 0 END) as normais,
                SUM(CASE WHEN status = 'atencao' THEN 1 ELSE 0 END) as atencao,
                SUM(CASE WHEN status = 'parada' THEN 1 ELSE 0 END) as paradas
            FROM linhas
        """)
        resultado = cursor.fetchone()
        conn.close()
        return dict(resultado) if resultado else None
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None