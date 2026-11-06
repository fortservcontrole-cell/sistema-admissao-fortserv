import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# ====================================================
# 1. INICIALIZAÇÃO E CONFIGURAÇÃO DO BANCO DE DADOS
# ====================================================
DB_NAME = "admissao_fortserv.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Candidatos / Senhas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha INTEGER NOT NULL,
            is_especial INTEGER DEFAULT 0,
            nome TEXT,
            cargo TEXT,
            cpf TEXT,
            etapa_atual TEXT NOT NULL,
            porcentagem REAL NOT NULL,
            hora_chegada TEXT NOT NULL,
            hora_liberacao TEXT,
            tempo_total TEXT,
            ult_usuario TEXT NOT NULL,
            tem_retorno INTEGER DEFAULT 0,
            ult_justificativa TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE candidatos ADD COLUMN senha INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE candidatos ADD COLUMN is_especial INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Tabela de Histórico e Auditoria
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id INTEGER NOT NULL,
            candidato_nome TEXT NOT NULL,
            etapa_origem TEXT NOT NULL,
            etapa_destino TEXT NOT NULL,
            tipo_movimentacao TEXT NOT NULL,
            justificativa TEXT,
            data_hora TEXT NOT NULL,
            mes_ano TEXT NOT NULL,
            operador TEXT NOT NULL
        )
    """)
    
    # Tabela de Configurações do Sistema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('logo_url', 'logo-fortserv.png')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('admin_email', 'luciano.veras@fortserv.com.br')")
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('senha_admin', '22Tkb590')")
    
    # Credenciais Padrão dos Setores Operacionais
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('senha_mesa', '2026mesaadmissao')")
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('senha_rh', '2026rhdocecontratos')")
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('senha_estoque', '2026estoqueentregas')")
    
    conn.commit()
    conn.close()

init_db()

def get_config(chave):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def set_config(chave, valor):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()

def clear_all_tickets():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM candidatos")
    c.execute("DELETE FROM historico_movimentacoes")
    try:
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('candidatos', 'historico_movimentacoes')")
    except Exception:
        pass
    conn.commit()
    conn.close()

# ====================================================
# 2. DEFINIÇÃO DAS 11 ETAPAS, SETORES E SENHAS
# ====================================================
ETAPAS_CONFIG = [
    {"num": "01", "nome": "01. Candidato Recepção", "pct": 9.1, "setor": "Recepção Central", "setor_id": "mesa"},
    {"num": "02", "nome": "02. Mesa Entrevista", "pct": 18.2, "setor": "Seleção / Operações", "setor_id": "mesa"},
    {"num": "03", "nome": "03. Mesa Exame Psicológico", "pct": 27.3, "setor": "Psicologia / RH", "setor_id": "mesa"},
    {"num": "04", "nome": "04. Exame Médico", "pct": 36.4, "setor": "Medicina do Trabalho", "setor_id": "mesa"},
    {"num": "05", "nome": "05. Doc Steck", "pct": 45.5, "setor": "Triagem Documental", "setor_id": "mesa"},
    {"num": "06", "nome": "06. Validação Doc RH", "pct": 54.5, "setor": "Analista de RH", "setor_id": "RH"},
    {"num": "07", "nome": "07. Cadastro - RE", "pct": 63.6, "setor": "Dpto. Pessoal", "setor_id": "RH"},
    {"num": "08", "nome": "08. Contrato Emitido", "pct": 72.7, "setor": "Dpto. Pessoal", "setor_id": "RH"},
    {"num": "09", "nome": "09. Contrato Assinado & Crachá", "pct": 81.8, "setor": "DP & Identificação", "setor_id": "RH"},
    {"num": "10", "nome": "10. Retirar Uniforme", "pct": 90.9, "setor": "Almoxarifado / EPIs", "setor_id": "estoque"},
    {"num": "11", "nome": "11. Liberado", "pct": 100.0, "setor": "Coordenação Final (Concluído)", "setor_id": "finalizado"}
]

ETAPAS_NOMES = [e["nome"] for e in ETAPAS_CONFIG]
ETAPAS_PCT_MAP = {e["nome"]: e["pct"] for e in ETAPAS_CONFIG}
ETAPAS_SETOR_MAP = {e["nome"]: e["setor_id"] for e in ETAPAS_CONFIG}

SETORES_INFO = {
    "mesa": {"label": "Mesa (Atendimento / Exames / Doc Steck)", "senha_key": "senha_mesa", "senha_default": "2026mesaadmissao"},
    "RH": {"label": "RH (Validação / Cadastro / Contratos)", "senha_key": "senha_rh", "senha_default": "2026rhdocecontratos"},
    "estoque": {"label": "Estoque (Almoxarifado / Uniformes)", "senha_key": "senha_estoque", "senha_default": "2026estoqueentregas"}
}

# ====================================================
# 3. CONFIGURAÇÃO VISUAL - FORTSERV - SISTEMA ADMISSIONAL (V23)
# ====================================================
st.set_page_config(
    page_title="FORTSERV - Sistema Admissional",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS V23 (Ocultar Menu Lateral + Navegação Superior + Cards Empilhados)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    /* ENQUADRAMENTO E PREENCHIMENTO HARMONIOSO EM TELA ÚNICA */
    .block-container {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    header[data-testid=stHeader], div[data-testid=stHeader], footer {
        display: none !important;
    }
    
    div.stElementContainer, div.element-container {
        margin-bottom: 1px !important;
        margin-top: 1px !important;
    }
    
    div[data-testid=stVerticalBlock] > div {
        gap: 0.18rem !important;
    }
    
    div[data-testid=stHorizontalBlock] {
        gap: 0.3rem !important;
        align-items: center !important;
    }
    
    hr {
        margin: 0.2rem 0 !important;
        padding: 0 !important;
    }
    
    /* BOTÕES SUPERIORES DE NAVEGAÇÃO */
    div.stButton > button {
        padding: 3px 8px !important;
        font-size: 13px !important;
        font-weight: 800 !important;
        min-height: 32px !important;
        border-radius: 6px !important;
    }
    
    /* CARTÕES DE KPI (INDICADORES TELA ÚNICA) */
    .kpi-card-v23 {
        background: #FFFFFF;
        border-radius: 6px;
        padding: 4px 6px;
        border: 1px solid #CBD5E1;
        box-shadow: 0px 1px 2px rgba(0, 0, 0, 0.02);
        text-align: center;
    }
    .kpi-title-v23 {
        font-size: 10px;
        font-weight: 800;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        line-height: 1.0;
    }
    .kpi-value-v23 {
        font-size: 20px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
        margin-top: 1px;
    }

    /* QUADRO BRANCO - CONTADOR DE ETAPA (PREENCHIMENTO HARMONIOSO) */
    .white-counter-box-v23 {
        background: #FFFFFF;
        border: 1px solid #94A3B8;
        border-radius: 6px;
        padding: 3px 6px;
        min-width: 85px;
        text-align: center;
        line-height: 1.1;
    }
    .white-counter-title-v23 {
        font-size: 11px;
        font-weight: 800;
        color: #1E293B;
    }
    .white-counter-qty-v23 {
        font-size: 16px;
        font-weight: 900;
        color: #1E3A8A;
    }

    /* CARTÃO AZUL DO SETOR (TEXTO DENSE E VISÍVEL) */
    .sector-badge-blue-v23 {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
        color: #FFFFFF;
        border-radius: 6px;
        padding: 4px 8px;
        min-width: 200px;
        max-width: 200px;
        line-height: 1.2;
    }
    .sector-badge-title-v23 {
        font-size: 13px;
        font-weight: 800;
        color: #FFFFFF;
    }
    .sector-badge-sub-v23 {
        font-size: 10px;
        color: #BFDBFE;
        font-weight: 600;
    }

    /* QUADRADOS DE SENHA (TEXTO AMBIENTE 15px) */
    .ticket-square-normal {
        background: #DBEAFE;
        color: #1E40AF;
        border: 1.5px solid #2563EB;
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 800;
        font-size: 15px;
        display: inline-block;
        margin-right: 3px;
        margin-bottom: 2px;
        box-shadow: 0px 1px 2px rgba(0,0,0,0.04);
    }
    .ticket-square-especial {
        background: #DC2626;
        color: #FFFFFF;
        border: 1.5px solid #991B1B;
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 800;
        font-size: 15px;
        display: inline-block;
        margin-right: 3px;
        margin-bottom: 2px;
        box-shadow: 0px 1px 3px rgba(220,38,38,0.2);
    }
    .ticket-square-retorno {
        background: #F59E0B;
        color: #FFFFFF;
        border: 1.5px solid #D97706;
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 800;
        font-size: 15px;
        display: inline-block;
        margin-right: 3px;
        margin-bottom: 2px;
        box-shadow: 0px 1px 3px rgba(245,158,11,0.2);
    }
    .ticket-square-finalizado {
        background: #10B981;
        color: #FFFFFF;
        border: 1.5px solid #059669;
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 800;
        font-size: 15px;
        display: inline-block;
        margin-right: 3px;
        margin-bottom: 2px;
        box-shadow: 0px 1px 2px rgba(16,185,129,0.15);
    }

    .auth-banner-ok {
        background-color: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 6px;
        padding: 6px 10px;
        color: #065F46;
        font-weight: 600;
        font-size: 12px;
        margin-bottom: 8px;
    }
    
    /* REGRAS DE IMPRESSÃO */
    @media print {
        div[data-testid="stHeader"], .no-print, nav, footer {
            display: none !important;
        }
        body {
            background: #FFFFFF !important;
            color: #000000 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Estado de Sessão para Navegação por Abas Superiores
if "top_tab" not in st.session_state:
    st.session_state.top_tab = "PAINEL TV"

if "setor_logado" not in st.session_state:
    st.session_state.setor_logado = None
if "operador_nome" not in st.session_state:
    st.session_state.operador_nome = ""

# BARRA DE NAVEGAÇÃO SUPERIOR (3 BOTÕES PRINCIPAIS)
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    btn_style_tv = "primary" if st.session_state.top_tab == "PAINEL TV" else "secondary"
    if st.button("📺 PAINEL TV", use_container_width=True, type=btn_style_tv):
        st.session_state.top_tab = "PAINEL TV"
        st.rerun()

with nav_col2:
    btn_style_lanc = "primary" if st.session_state.top_tab == "LANÇAMENTOS" else "secondary"
    if st.button("📝 LANÇAMENTOS", use_container_width=True, type=btn_style_lanc):
        st.session_state.top_tab = "LANÇAMENTOS"
        st.rerun()

with nav_col3:
    btn_style_admin = "primary" if st.session_state.top_tab == "ADMIN" else "secondary"
    if st.button("🔐 ADMIN", use_container_width=True, type=btn_style_admin):
        st.session_state.top_tab = "ADMIN"
        st.rerun()

st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)

# Função Auxiliar: Dashboard de KPIs
def render_kpi_dashboard():
    conn = sqlite3.connect(DB_NAME)
    df_cand = pd.read_sql_query("SELECT * FROM candidatos", conn)
    df_hist = pd.read_sql_query("SELECT * FROM historico_movimentacoes", conn)
    conn.close()
    
    total_cand = len(df_cand)
    em_andamento = len(df_cand[df_cand['etapa_atual'] != '11. Liberado']) if total_cand > 0 else 0
    concluidos = len(df_cand[df_cand['etapa_atual'] == '11. Liberado']) if total_cand > 0 else 0
    total_especiais = len(df_cand[df_cand['is_especial'] == 1]) if total_cand > 0 else 0
    total_retornos = len(df_hist[df_hist['tipo_movimentacao'] == 'RETORNO']) if not df_hist.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class='kpi-card-v23'>
            <div class='kpi-title-v23'>Total de Senhas</div>
            <div class='kpi-value-v23'>{total_cand}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class='kpi-card-v23'>
            <div class='kpi-title-v23'>Em Andamento</div>
            <div class='kpi-value-v23' style='color: #2563EB;'>{em_andamento}</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class='kpi-card-v23'>
            <div class='kpi-title-v23'>Concluídos (100%)</div>
            <div class='kpi-value-v23' style='color: #059669;'>{concluidos}</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class='kpi-card-v23'>
            <div class='kpi-title-v23'>🔴 Senhas Especiais</div>
            <div class='kpi-value-v23' style='color: #DC2626;'>{total_especiais}</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class='kpi-card-v23'>
            <div class='kpi-title-v23'>Ocorrências Retorno</div>
            <div class='kpi-value-v23' style='color: #D97706;'>{total_retornos}</div>
        </div>
        """, unsafe_allow_html=True)
    # space removed

# ====================================================
# ABA 1: PAINEL TV (VISUALIZAÇÃO DO CANDIDATO EM TELA ÚNICA)
# ====================================================
if st.session_state.top_tab == "PAINEL TV":
    render_kpi_dashboard()
    
    conn = sqlite3.connect(DB_NAME)
    df_tv = pd.read_sql_query("SELECT * FROM candidatos", conn)
    conn.close()
    
    
    # RENDERIZAÇÃO DAS 11 ETAPAS EM LAYOUT ENQUADRADO EMPILHADO HORIZONTAL
    for idx, e_conf in enumerate(ETAPAS_CONFIG):
        e_nome = e_conf["nome"]
        e_pct = e_conf["pct"]
        e_setor = e_conf["setor"]
        
        cand_na_etapa = df_tv[df_tv['etapa_atual'] == e_nome] if not df_tv.empty else pd.DataFrame()
        qtd_na_etapa = len(cand_na_etapa)
        
        c_quadro, c_setor, c_esteira = st.columns([1.1, 3.1, 10.8])
        
        with c_quadro:
            st.markdown(f"""
            <div class='white-counter-box-v23'>
                <div class='white-counter-title-v23'>ETAPA {e_conf['num']}</div>
                <div class='white-counter-qty-v23'>QTDE: {qtd_na_etapa}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_setor:
            st.markdown(f"""
            <div class='sector-badge-blue-v23'>
                <div class='sector-badge-title-v23'>{e_nome} ({e_pct}%)</div>
                <div class='sector-badge-sub-v23'>Responsável: {e_setor}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_esteira:
            squares_html = ""
            if not cand_na_etapa.empty:
                for _, c in cand_na_etapa.iterrows():
                    num_senha = int(c['senha'])
                    is_esp = (num_senha >= 250 and num_senha <= 300) or c['is_especial'] == 1
                    senha_formatted = f"{num_senha:03d}"
                    
                    if e_nome == "11. Liberado":
                        squares_html += f"<div class='ticket-square-finalizado' title='Senha {senha_formatted} - Liberado 100%'>✅ {senha_formatted}</div>"
                    elif is_esp:
                        squares_html += f"<div class='ticket-square-especial' title='Senha {senha_formatted} - Prioridade Especial'>🔴 {senha_formatted}</div>"
                    elif c['tem_retorno'] == 1:
                        squares_html += f"<div class='ticket-square-retorno' title='Senha {senha_formatted} - Retorno / Pendência'>⚠️ {senha_formatted}</div>"
                    else:
                        squares_html += f"<div class='ticket-square-normal' title='Senha {senha_formatted}'>SENHA {senha_formatted}</div>"
            else:
                squares_html = "<span style='font-size:12px; color:#94A3B8; font-style:italic;'>Nenhuma senha nesta etapa no momento.</span>"
                
            st.markdown(f"<div style='padding-top:6px;'>{squares_html}</div>", unsafe_allow_html=True)

# ====================================================
# ABA 2: LANÇAMENTOS (EMISSÃO & MOVIMENTAÇÃO POR SETOR)
# ====================================================
elif st.session_state.top_tab == "LANÇAMENTOS":
    st.subheader("📝 Lançamentos & Movimentação de Candidatos por Setor")
    
    # AUTENTICAÇÃO DE SETOR NO PAINEL DE LANÇAMENTOS
    if st.session_state.setor_logado:
        setor_id_atual = st.session_state.setor_logado
        label_setor_atual = SETORES_INFO[setor_id_atual]["label"]
        col_auth_ok, col_logout = st.columns([4, 1])
        with col_auth_ok:
            st.markdown(f"""
            <div class='auth-banner-ok'>
                🟢 <b>SETOR AUTENTICADO:</b> {label_setor_atual} | 👤 <b>Operador:</b> {st.session_state.operador_nome}
            </div>
            """, unsafe_allow_html=True)
        with col_logout:
            if st.button("🔒 Sair / Trocar Setor", use_container_width=True):
                st.session_state.setor_logado = None
                st.session_state.operador_nome = ""
                st.rerun()
    else:
        with st.expander("🔑 Identificação do Setor para Lançamentos (Mesa, RH ou Estoque)", expanded=True):
            col_s1, col_s2, col_s3, col_s4 = st.columns([2, 2, 2, 1.5])
            with col_s1:
                setor_sel = st.selectbox(
                    "Selecione seu Setor:",
                    ["mesa", "RH", "estoque"],
                    format_func=lambda x: f"{x.upper()} - {SETORES_INFO[x]['label']}"
                )
            with col_s2:
                senha_setor_input = st.text_input("Senha do Setor:", type="password", help="mesa: 2026mesaadmissao | RH: 2026rhdocecontratos | estoque: 2026estoqueentregas")
            with col_s3:
                op_nome_input = st.text_input("Seu Nome / Login:", value="Operador_Setor")
            with col_s4:
                # space removed
                # space removed
                if st.button("🔓 Logar", type="primary", use_container_width=True):
                    senha_correta_setor = get_config(SETORES_INFO[setor_sel]["senha_key"]) or SETORES_INFO[setor_sel]["senha_default"]
                    if senha_setor_input == senha_correta_setor:
                        st.session_state.setor_logado = setor_sel
                        st.session_state.operador_nome = op_nome_input.strip() or f"Operador_{setor_sel.upper()}"
                        st.success(f"Autenticado com sucesso no setor {setor_sel.upper()}!")
                        st.rerun()
                    else:
                        st.error(f"Senha incorreta para o setor {setor_sel.upper()}!")

    st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)
    
    col_emit, col_mov = st.columns([1, 1])
    
    # EMISSÃO DE SENHA NA RECEPÇÃO
    with col_emit:
        st.markdown("### ➕ Emissão de Nova Senha (Recepção)")
        
        if "flash_sucesso_senha" in st.session_state:
            st.success(st.session_state.pop("flash_sucesso_senha"))
            
        conn = sqlite3.connect(DB_NAME)
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAX(senha) FROM candidatos WHERE senha < 250")
            max_s = cur.fetchone()[0]
            prox_senha_sug = (max_s + 1) if max_s else 1
            if prox_senha_sug > 249: prox_senha_sug = 1
        except Exception:
            prox_senha_sug = 1
        conn.close()

        with st.form("form_nova_senha_v23"):
            num_senha_input = st.number_input("Número da Senha (01 a 300):", min_value=1, max_value=300, value=int(prox_senha_sug), step=1)
            c_nome_input = st.text_input("Nome do Candidato (Opcional):", value="")
            c_cargo_input = st.text_input("Cargo / Função:", value="Auxiliar de Operações")
            
            btn_emitir = st.form_submit_button("📥 Emitir e Registrar Senha (T0)", type="primary")
            
            if btn_emitir:
                try:
                    is_especial_flag = 1 if (num_senha_input >= 250 and num_senha_input <= 300) else 0
                    agora_dt = datetime.datetime.now()
                    agora_str = agora_dt.strftime("%Y-%m-%d %H:%M:%S")
                    mes_ano_str = agora_dt.strftime("%Y-%m")
                    
                    sector_recorded = f"Setor Mesa ({st.session_state.operador_nome or 'Recepção'})"
                    
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO candidatos (senha, is_especial, nome, cargo, cpf, etapa_atual, porcentagem, hora_chegada, ult_usuario)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (num_senha_input, is_especial_flag, c_nome_input, c_cargo_input, "0000", ETAPAS_NOMES[0], ETAPAS_PCT_MAP[ETAPAS_NOMES[0]], agora_str, sector_recorded))
                    
                    cand_id = c.lastrowid
                    
                    c.execute("""
                        INSERT INTO historico_movimentacoes (candidato_id, candidato_nome, etapa_origem, etapa_destino, tipo_movimentacao, justificativa, data_hora, mes_ano, operador)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cand_id, f"Senha {num_senha_input:03d} - {c_nome_input}", "Entrada", ETAPAS_NOMES[0], "AVANCO", "Emissão de senha na Recepção", agora_str, mes_ano_str, sector_recorded))
                    
                    conn.commit()
                    conn.close()
                    
                    if is_especial_flag == 1:
                        st.session_state["flash_sucesso_senha"] = f"🔴 **SENHA ESPECIAL {num_senha_input:03d} (PRIORIDADE)** emitida com sucesso!"
                    else:
                        st.session_state["flash_sucesso_senha"] = f"✅ **SENHA {num_senha_input:03d}** emitida com sucesso na Recepção!"
                    st.rerun()
                except Exception as ex:
                    st.error(f"Erro ao gravar senha: {ex}")

    # MOVIMENTAÇÃO DE SENHAS
    with col_mov:
        st.markdown("### 🚀 Movimentar ou Devolver Senha")
        
        conn = sqlite3.connect(DB_NAME)
        df_cand_active = pd.read_sql_query("SELECT * FROM candidatos WHERE etapa_atual != '11. Liberado' ORDER BY id ASC", conn)
        conn.close()
        
        if df_cand_active.empty:
            st.info("Nenhuma senha em andamento no momento.")
        else:
            cand_list_options = [f"Senha {int(r['senha']):03d} - {r['nome'] if r['nome'] else 'Candidato'} ({r['etapa_atual']})" for _, r in df_cand_active.iterrows()]
            sel_cand_str = st.selectbox("Selecione a Senha para Atendimento:", cand_list_options)
            
            senha_sel_num = int(sel_cand_str.split(" - ")[0].replace("Senha ", ""))
            cand_row = df_cand_active[df_cand_active['senha'] == senha_sel_num].iloc[0]
            cand_id_sel = int(cand_row['id'])
            etapa_atual_cand = cand_row['etapa_atual']
            setor_requerido = ETAPAS_SETOR_MAP[etapa_atual_cand]
            
            st.markdown(f"""
            **Detalhes do Atendimento:**
            - **Senha:** `{senha_sel_num:03d}`
            - **Candidato:** `{cand_row['nome'] or 'N/A'}` | **Cargo:** `{cand_row['cargo']}`
            - **Etapa Atual:** `{etapa_atual_cand}` ({cand_row['porcentagem']}%)
            - **Setor Responsável:** `{setor_requerido.upper()}`
            """)
            
            c_act1, c_act2 = st.columns(2)
            
            with c_act1:
                if st.button("🚀 Avançar Senha para Próxima Etapa", type="primary", use_container_width=True):
                    if not st.session_state.setor_logado:
                        st.error(f"🔒 Acesso bloqueado! Faça login no setor '{setor_requerido.upper()}' para movimentar esta senha.")
                    elif st.session_state.setor_logado != setor_requerido:
                        st.error(f"🚨 Acesso negado! O setor '{st.session_state.setor_logado.upper()}' não pode movimentar a etapa '{etapa_atual_cand}'. Faça login no setor '{setor_requerido.upper()}'.")
                    else:
                        idx_atual = ETAPAS_NOMES.index(etapa_atual_cand)
                        prox_etapa = ETAPAS_NOMES[min(idx_atual + 1, len(ETAPAS_NOMES) - 1)]
                        pct_nova = ETAPAS_PCT_MAP[prox_etapa]
                        
                        agora_dt = datetime.datetime.now()
                        agora_str = agora_dt.strftime("%Y-%m-%d %H:%M:%S")
                        mes_ano_str = agora_dt.strftime("%Y-%m")
                        
                        h_liberacao = cand_row['hora_liberacao']
                        tempo_total_str = cand_row['tempo_total']
                        
                        setor_clean = "Mesa" if st.session_state.setor_logado == "mesa" else ("RH" if st.session_state.setor_logado == "RH" else "Estoque")
                        sector_tag = f"Setor {setor_clean} ({st.session_state.operador_nome})"
                        
                        # REGRA DO ESTOQUE (Etapa 10 -> 11 Liberado 100%)
                        if etapa_atual_cand == "10. Retirar Uniforme" or prox_etapa == "11. Liberado":
                            prox_etapa = "11. Liberado"
                            pct_nova = 100.0
                            h_liberacao = agora_str
                            try:
                                h_chegada_dt = datetime.datetime.strptime(cand_row['hora_chegada'], "%Y-%m-%d %H:%M:%S")
                                diff = agora_dt - h_chegada_dt
                                horas = diff.seconds // 3600
                                minutos = (diff.seconds % 3600) // 60
                                tempo_total_str = f"{horas:02d}h {minutos:02d}min"
                            except Exception:
                                tempo_total_str = "00h 45min"
                                
                        conn = sqlite3.connect(DB_NAME)
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE candidatos 
                            SET etapa_atual = ?, porcentagem = ?, hora_liberacao = ?, tempo_total = ?, ult_usuario = ?
                            WHERE id = ?
                        """, (prox_etapa, pct_nova, h_liberacao, tempo_total_str, sector_tag, cand_id_sel))
                        
                        msg_justif = "Finalizado pelo Estoque (100% Concluído)" if prox_etapa == "11. Liberado" else f"Avanço de etapa por {sector_tag}"
                        
                        cur.execute("""
                            INSERT INTO historico_movimentacoes (candidato_id, candidato_nome, etapa_origem, etapa_destino, tipo_movimentacao, justificativa, data_hora, mes_ano, operador)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (cand_id_sel, f"Senha {senha_sel_num:03d} - {cand_row['nome']}", etapa_atual_cand, prox_etapa, "AVANCO", msg_justif, agora_str, mes_ano_str, sector_tag))
                        
                        conn.commit()
                        conn.close()
                        
                        if prox_etapa == "11. Liberado":
                            st.toast(f"🎉 Senha {senha_sel_num:03d} FINALIZADA pelo Estoque (100%)!")
                        else:
                            st.toast(f"✅ Senha {senha_sel_num:03d} avançou para {prox_etapa}!")
                        st.rerun()

            with c_act2:
                with st.popover("↩️ Devolver Senha", use_container_width=True):
                    idx_ret = ETAPAS_NOMES.index(etapa_atual_cand)
                    etapas_ant = ETAPAS_NOMES[:idx_ret] if idx_ret > 0 else [ETAPAS_NOMES[0]]
                    st.markdown(f"**Devolver Senha {senha_sel_num:03d}**")
                    st.caption(f"Etapa atual: {etapa_atual_cand}")
                    etapa_ret_target = st.selectbox("Selecione a Etapa Anterior para Onde a Senha Deve Voltar:", etapas_ant, key=f"sel_target_act_{cand_id_sel}")
                    justif_txt = st.text_area("Justificativa Obrigatória:", key=f"txt_just_act_{cand_id_sel}")
                    
                    if st.button("Confirmar Devolução", key=f"btn_confirm_ret_{cand_id_sel}"):
                        if not st.session_state.setor_logado:
                            st.error(f"🔒 Faça login no setor '{setor_requerido.upper()}' para devolver.")
                        elif st.session_state.setor_logado != setor_requerido:
                            st.error(f"🚨 Setor '{st.session_state.setor_logado.upper()}' não autorizado.")
                        elif not justif_txt.strip():
                            st.error("Justificativa obrigatória!")
                        else:
                            agora_dt = datetime.datetime.now()
                            agora_str = agora_dt.strftime("%Y-%m-%d %H:%M:%S")
                            mes_ano_str = agora_dt.strftime("%Y-%m")
                            pct_nova_ret = ETAPAS_PCT_MAP[etapa_ret_target]
                            setor_clean = "Mesa" if st.session_state.setor_logado == "mesa" else ("RH" if st.session_state.setor_logado == "RH" else "Estoque")
                            sector_tag = f"Setor {setor_clean} ({st.session_state.operador_nome})"
                            
                            conn = sqlite3.connect(DB_NAME)
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE candidatos 
                                SET etapa_atual = ?, porcentagem = ?, ult_usuario = ?, tem_retorno = 1, ult_justificativa = ?
                                WHERE id = ?
                            """, (etapa_ret_target, pct_nova_ret, sector_tag, justif_txt.strip(), cand_id_sel))
                            
                            cur.execute("""
                                INSERT INTO historico_movimentacoes (candidato_id, candidato_nome, etapa_origem, etapa_destino, tipo_movimentacao, justificativa, data_hora, mes_ano, operador)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (cand_id_sel, f"Senha {senha_sel_num:03d} - {cand_row['nome']}", etapa_atual_cand, etapa_ret_target, "RETORNO", justif_txt.strip(), agora_str, mes_ano_str, sector_tag))
                            
                            conn.commit()
                            conn.close()
                            st.toast(f"⚠️ Senha {senha_sel_num:03d} devolvida para {etapa_ret_target}!")
                            st.rerun()

# ====================================================
# ABA 3: ADMIN (PAINEL DO ADMINISTRADOR)
# ====================================================
elif st.session_state.top_tab == "ADMIN":
    st.subheader("🔐 PAINEL DE GESTÃO - Área do Administrador")
    
    if "admin_logado" not in st.session_state:
        st.session_state.admin_logado = False
        
    if not st.session_state.admin_logado:
        c_auth, _ = st.columns([1.5, 1])
        with c_auth:
            st.markdown("#### Autenticação Administrativa")
            pwd_input = st.text_input("Senha do Administrador:", type="password")
            if st.button("🔐 Acessar Painel Executivo", type="primary"):
                senha_correta = get_config("senha_admin") or "22Tkb590"
                if pwd_input == senha_correta:
                    st.session_state.admin_logado = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
    else:
        col_adm_status, col_adm_logout = st.columns([4, 1])
        with col_adm_status:
            admin_email_atual = get_config("admin_email") or "luciano.veras@fortserv.com.br"
            st.success(f"Administrador Conectado: **{admin_email_atual}**")
        with col_adm_logout:
            if st.button("🔒 Sair do Painel Admin", use_container_width=True):
                st.session_state.admin_logado = False
                st.rerun()
                
        st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)
        
        tab_eff, tab_report, tab_auto, tab_settings = st.tabs([
            "📊 Eficiência de Setores & Gargalos",
            "📄 Emissão de Relatório Executivo",
            "📧 Relatório Diário Automático & Drive",
            "⚙️ Configurações & Reset de Base"
        ])
        
        # --- TAB EFICIÊNCIA ---
        with tab_eff:
            st.subheader("Análise Mensal de Eficiência Operacional")
            conn = sqlite3.connect(DB_NAME)
            df_hist = pd.read_sql_query("SELECT * FROM historico_movimentacoes", conn)
            conn.close()
            
            if df_hist.empty:
                st.info("Nenhum histórico registrado no banco de dados até o momento.")
            else:
                meses_disponiveis = df_hist['mes_ano'].unique()
                mes_sel = st.selectbox("Selecione o Mês para Análise:", meses_disponiveis)
                
                df_mes_filtrado = df_hist[df_hist['mes_ano'] == mes_sel]
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Movimentações", len(df_mes_filtrado))
                m2.metric("Avanços de Etapa", len(df_mes_filtrado[df_mes_filtrado['tipo_movimentacao'] == 'AVANCO']))
                m3.metric("Ocorrências de Retorno", len(df_mes_filtrado[df_mes_filtrado['tipo_movimentacao'] == 'RETORNO']))
                
                st.markdown(f"#### Volume de Processamentos por Setor ({mes_sel}) - Gráfico de Barras Horizontais")
                
                volume_setores = df_mes_filtrado['etapa_destino'].value_counts()
                
                df_chart = pd.DataFrame({
                    'Etapa': ETAPAS_NOMES,
                    'Quantidade': [int(volume_setores.get(nome, 0)) for nome in ETAPAS_NOMES]
                }).set_index('Etapa')
                
                st.bar_chart(df_chart, horizontal=True)
                
                st.markdown("#### ⚠️ Detalhamento de Auditoria das Devoluções / Recusas")
                df_recusas = df_mes_filtrado[df_mes_filtrado['tipo_movimentacao'] == 'RETORNO']
                if not df_recusas.empty:
                    st.dataframe(df_recusas[['data_hora', 'candidato_nome', 'etapa_origem', 'etapa_destino', 'justificativa', 'operador']], use_container_width=True)
                else:
                    st.success("Nenhuma recusa ou retorno registrado neste mês.")

        # --- TAB RELATÓRIO ---
        with tab_report:
            st.subheader("📄 Emissão e Impressão de Relatório Executivo")
            
            conn = sqlite3.connect(DB_NAME)
            df_cand_all = pd.read_sql_query("SELECT * FROM candidatos", conn)
            df_hist_all = pd.read_sql_query("SELECT * FROM historico_movimentacoes", conn)
            conn.close()
            
            c_rep_btn1, c_rep_btn2, c_rep_btn3 = st.columns([1.5, 1.5, 1])
            
            with c_rep_btn1:
                btn_gerar_rep = st.button("📄 Gerar / Atualizar Relatório", type="primary", use_container_width=True)
                if btn_gerar_rep:
                    st.session_state.relatorio_gerado = True
                    
            with c_rep_btn2:
                # Botão para disparar impressora / diálogo de impressão do navegador
                st.components.v1.html("""
                    <button onclick="window.parent.print()" style="
                        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
                        color: #FFFFFF;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 14px;
                        cursor: pointer;
                        width: 100%;
                        height: 38px;
                        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
                    ">
                        🖨️ Imprimir Relatório Executivo
                    </button>
                """, height=45)
                
            with c_rep_btn3:
                # Botão de exportação direta para Excel
                import io
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_cand_all.to_excel(writer, sheet_name="Candidatos_Status", index=False)
                    df_hist_all.to_excel(writer, sheet_name="Historico_Auditoria", index=False)
                excel_data = excel_buffer.getvalue()
                
                st.download_button(
                    label="📥 Baixar Excel",
                    data=excel_data,
                    file_name=f"relatorio_executivo_admissao_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)
            
            if st.session_state.get("relatorio_gerado", True):
                st.markdown("""
                <div class='no-print' style='background: #EFF6FF; border-left: 4px solid #2563EB; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; color: #1E40AF;'>
                    💡 <b>Dica de Impressão:</b> Clique no botão <b>🖨️ Imprimir Relatório Executivo</b> para abrir a tela de impressão ou salvar o relatório em formato PDF.
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 📋 RELATÓRIO EXECUTIVO DE ADMISSÃO - FORTSERV FACILITIES")
                st.caption(f"Data de Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} | www.fortserv.com.br")
                
                st.markdown("#### 1. Status Atual das Senhas / Candidatos em Atendimento:")
                st.dataframe(
                    df_cand_all[['id', 'senha', 'is_especial', 'nome', 'cargo', 'etapa_atual', 'porcentagem', 'hora_chegada', 'hora_liberacao', 'tempo_total', 'ult_usuario', 'tem_retorno', 'ult_justificativa']], 
                    use_container_width=True
                )
                
                st.markdown("#### 2. Trilha de Auditoria e Histórico das Movimentações por Setor:")
                st.dataframe(
                    df_hist_all[['id', 'data_hora', 'candidato_nome', 'etapa_origem', 'etapa_destino', 'tipo_movimentacao', 'justificativa', 'operador']], 
                    use_container_width=True
                )
                st.success("✅ Relatório gerado com sucesso e disponível para impressão.")

        # --- TAB AUTOMAÇÃO ---
        with tab_auto:
            st.subheader("📧 Relatório Diário Automático & Backup no Google Drive")
            st.markdown("""
            O sistema conta com um script autônomo agendado que é disparado diariamente ao final do expediente.
            - **Anexo**: Planilha consolidada em Excel contendo a performance do dia e o acumulado do mês.
            """)
            if st.button("🚀 Disparar Teste de Envio do Relatório Diário Agora"):
                try:
                    import subprocess
                    res = subprocess.run(["python3", "agendador_relatorio_diario.py"], capture_output=True, text=True)
                    st.success("✅ Rotina executada com sucesso!")
                    st.code(res.stdout)
                except Exception as ex:
                    st.error(f"Erro ao disparar rotina: {ex}")

        # --- TAB CONFIGURAÇÕES & RESET ---
        with tab_settings:
            st.subheader("Configurações do Sistema e Zeramento de Base")
            
            st.markdown("#### Senhas dos Setores Operacionais:")
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                nova_senha_mesa = st.text_input("Senha Setor MESA:", value=get_config("senha_mesa") or "2026mesaadmissao", type="password")
            with c_s2:
                nova_senha_rh = st.text_input("Senha Setor RH:", value=get_config("senha_rh") or "2026rhdocecontratos", type="password")
            with c_s3:
                nova_senha_estoque = st.text_input("Senha Setor ESTOQUE:", value=get_config("senha_estoque") or "2026estoqueentregas", type="password")
            
            st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)
            st.markdown("#### Configurações Gerais:")
            novo_email = st.text_input("E-mail do Administrador:", value=admin_email_atual)
            nova_senha_admin = st.text_input("Senha de Acesso Admin:", value=get_config("senha_admin") or "22Tkb590", type="password")
            
            if st.button("💾 Salvar Configurações"):
                set_config("senha_mesa", nova_senha_mesa)
                set_config("senha_rh", nova_senha_rh)
                set_config("senha_estoque", nova_senha_estoque)
                set_config("admin_email", novo_email)
                set_config("senha_admin", nova_senha_admin)
                st.success("Todas as configurações foram salvas com sucesso!")
                st.rerun()

            st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)
            st.markdown("#### ⚠️ Zerar Banco de Dados")
            st.warning("Atenção: A ação abaixo apaga todos os registros de senhas e históricos de movimentação para iniciar testes limpos.")
            if st.button("🗑️ Zerar o Sistema", type="primary"):
                clear_all_tickets()
                st.success("✅ Sistema zerado com sucesso! Nenhuma senha ativa no banco de dados.")
                st.rerun()

# ====================================================
# RODAPÉ DE IDENTIFICAÇÃO DO DESENVOLVEDOR
# ====================================================
st.markdown("<div style='text-align: center; font-size: 11px; font-weight: 700; color: #64748B; margin-top: 10px; padding: 6px 0 2px 0; border-top: 1px solid #E2E8F0;'>Criado e desenvolvido por: Luciano Veras 2026</div>", unsafe_allow_html=True)
