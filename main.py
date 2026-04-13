import streamlit as st
import zipfile
import sqlite3
import os
import pandas as pd

# Configuração da página para usar a largura total
st.set_page_config(page_title="SQLite Backup Viewer", layout="wide")

# Estilização CSS para parecer mais com um visualizador de banco de dados
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stTable { background-color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📂 SQLite Web Viewer (.backup)")

# Upload do arquivo
uploaded_file = st.sidebar.file_uploader("Suba seu arquivo .backup", type=["backup", "zip"])

if uploaded_file is not None:
    temp_dir = "temp_db"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    try:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            # Procura os arquivos específicos mencionados
            db_filename = next((f for f in file_list if f in ["song.db", "Music Database"]), None)

            if db_filename:
                zip_ref.extract(db_filename, temp_dir)
                db_path = os.path.join(temp_dir, db_filename)
                
                # Conexão
                conn = sqlite3.connect(db_path)
                
                # 1. Obter todas as tabelas e suas estruturas
                query_tables = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                tables = pd.read_sql_query(query_tables, conn)['name'].tolist()

                if tables:
                    st.sidebar.subheader("Tabelas")
                    selected_table = st.sidebar.radio("Selecione para visualizar:", tables)

                    # 2. Obter informações das colunas (PRAGMA table_info)
                    columns_info = pd.read_sql_query(f"PRAGMA table_info('{selected_table}')", conn)
                    
                    # Layout principal
                    st.subheader(f"Tabela: `{selected_table}`")
                    
                    # Abas para Dados e Estrutura (Estilo SQLiteViewer)
                    tab1, tab2 = st.tabs(["📄 Dados", "🏗️ Estrutura (Schema)"])
                    
                    with tab1:
                        # Limitar a visualização inicial para performance, mas permitir ver tudo
                        df = pd.read_sql_query(f"SELECT * FROM {selected_table}", conn)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.caption(f"Total de registros: {len(df)}")

                    with tab2:
                        st.write("Detalhes das Colunas:")
                        st.table(columns_info[['name', 'type', 'notnull', 'pk']])

                conn.close()
            else:
                st.error("Arquivo de banco de dados não encontrado dentro do zip.")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("👈 Por favor, faça o upload do arquivo .backup na barra lateral para começar.")
    st.markdown("""
    **Como funciona:**
    1. O sistema lê o arquivo `.backup` como um arquivo comprimido.
    2. Localiza automaticamente `song.db` ou `music database`.
    3. Extrai as tabelas e permite a navegação lateral idêntica ao SQLite Viewer.
    """)
