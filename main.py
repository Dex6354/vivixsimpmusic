import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil

st.set_page_config(page_title="Music Database Generator", layout="wide")

# O arquivo simpmusic.db original (com todos os dados) deve estar na mesma pasta do script
BASE_SIMP = "simpmusic.db"

st.title("📂 Gerador de base: Music Database")

# 1. Upload do arquivo de origem
vivi_file = st.file_uploader("Importe o arquivo vivi.db", type=["db"])

if vivi_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix="_vivi.db") as tmp_v:
        tmp_v.write(vivi_file.read())
        path_vivi = tmp_v.name

    try:
        # Extrair IDs do vivi.db mantendo a ordem original
        conn_v = sqlite3.connect(path_vivi)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        st.subheader("Lista de IDs detectada")
        st.dataframe(df_ids, use_container_width=True)

        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado na pasta do script.")
        else:
            # Processamento em memória/temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_out:
                output_path = tmp_out.name
            
            # Copia o arquivo original com todas as 23 tabelas e dados
            shutil.copy2(BASE_SIMP, output_path)

            try:
                conn_out = sqlite3.connect(output_path)
                cursor = conn_out.cursor()

                # Prepara os IDs (associando à playlist 1 para visibilidade no app)
                ids_to_insert = [(row['songId'], 1) for _, row in df_ids.iterrows()]
                
                # Insere os novos IDs na tabela correta da estrutura original
                cursor.executemany(
                    "INSERT OR IGNORE INTO pair_song_local_playlist (songId, playlistId) VALUES (?, ?)", 
                    ids_to_insert
                )
                
                conn_out.commit()
                conn_out.close()

                # 2. Botão de Download com o nome solicitado
                with open(output_path, "rb") as f:
                    file_data = f.read()
                    
                st.success("Tudo pronto! Clique abaixo para baixar sua nova base.")
                st.download_button(
                    label="📥 BAIXAR MUSIC DATABASE",
                    data=file_data,
                    file_name="Music Database.db",
                    mime="application/octet-stream"
                )

            except Exception as e:
                st.error(f"Erro ao processar dados: {e}")
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)

    except Exception as e:
        st.error(f"Erro ao ler vivi.db: {e}")
    finally:
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
