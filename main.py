import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os

st.set_page_config(page_title="SimpMusic Full Generator", layout="wide")

# O arquivo original simpmusic.db deve estar na mesma pasta do script para servir de molde
BASE_SIMP = "simpmusic.db"

st.title("📂 Gerador Completo SimpMusic")
st.write("Extrai IDs do 'vivi.db' e gera um 'simpmusic.db' com a estrutura completa (23 tabelas).")

def get_full_schema(db_path):
    """Extrai todos os comandos de criação do banco original"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Pega o SQL de criação de todas as tabelas, índices e triggers
    cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")
    schemas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return schemas

vivi_file = st.file_uploader("1. Importe o arquivo vivi.db", type=["db"])

if vivi_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix="_vivi.db") as tmp_v:
        tmp_v.write(vivi_file.read())
        path_vivi = tmp_v.name

    try:
        # Extrair IDs do vivi.db
        conn_v = sqlite3.connect(path_vivi)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        st.subheader("IDs capturados da origem")
        st.dataframe(df_ids, use_container_width=True)

        if st.button("🚀 Gerar simpmusic.db Completo"):
            if not os.path.exists(BASE_SIMP):
                st.error(f"Erro: O arquivo '{BASE_SIMP}' (molde) não foi encontrado na pasta.")
            else:
                # 1. Obter o Schema original
                schemas = get_full_schema(BASE_SIMP)

                # 2. Criar novo banco temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_s:
                    path_output = tmp_s.name

                conn_out = sqlite3.connect(path_output)
                cursor_out = conn_out.cursor()

                # 3. Replicar todas as 23 tabelas e estruturas
                for statement in schemas:
                    try:
                        cursor_out.execute(statement)
                    except:
                        continue # Ignora erros de tabelas que já possam existir
                
                # 4. Inserir os dados na tabela alvo
                ids_to_insert = [(row['songId'], 1) for _, row in df_ids.iterrows()]
                
                try:
                    cursor_out.executemany(
                        "INSERT OR IGNORE INTO pair_song_local_playlist (songId, playlistId) VALUES (?, ?)", 
                        ids_to_insert
                    )
                    conn_out.commit()
                    st.success(f"Arquivo gerado com sucesso com todas as tabelas originais!")

                    # 5. Download
                    with open(path_output, "rb") as f:
                        st.download_button(
                            label="📥 BAIXAR simpmusic.db COMPLETO",
                            data=f,
                            file_name="simpmusic.db",
                            mime="application/octet-stream"
                        )
                except Exception as e:
                    st.error(f"Erro ao inserir dados: {e}")
                finally:
                    conn_out.close()

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
    finally:
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
