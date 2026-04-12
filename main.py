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

vivi_file = st.file_uploader("Importe o arquivo vivi.db", type=["db"])

if vivi_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix="_vivi.db") as tmp_v:
        tmp_v.write(vivi_file.read())
        path_vivi = tmp_v.name

    try:
        # 1. Extrair IDs do vivi.db mantendo a ordem original
        conn_v = sqlite3.connect(path_vivi)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_ids['songId'].tolist()
        st.success(f"✅ {len(lista_ids)} IDs encontrados no arquivo de origem.")

        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado na pasta do script.")
        else:
            # 2. Preparar o arquivo de saída
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_out:
                output_path = tmp_out.name
            
            # Copia integral do arquivo original (23 tabelas + dados)
            shutil.copy2(BASE_SIMP, output_path)

            try:
                conn_out = sqlite3.connect(output_path)
                cursor = conn_out.cursor()

                # 3. Inserção com preenchimento de colunas obrigatórias
                # Usamos songId, playlistId (1) e position (índice da lista)
                dados_insercao = []
                for i, s_id in enumerate(lista_ids):
                    dados_insercao.append((s_id, 1, i))

                cursor.executemany(
                    "INSERT OR IGNORE INTO pair_song_local_playlist (songId, playlistId, position) VALUES (?, ?, ?)", 
                    dados_insercao
                )
                
                conn_out.commit()
                
                # Verificação interna
                cursor.execute("SELECT COUNT(*) FROM pair_song_local_playlist")
                total_final = cursor.fetchone()[0]
                conn_out.close()

                # 4. Botão de Download
                with open(output_path, "rb") as f:
                    file_data = f.read()
                
                st.divider()
                st.write(f"📊 Total de registros na tabela destino após união: {total_final}")
                
                st.download_button(
                    label="📥 BAIXAR MUSIC DATABASE",
                    data=file_data,
                    file_name="Music Database.db",
                    mime="application/octet-stream"
                )

            except Exception as e:
                st.error(f"Erro ao inserir dados na estrutura: {e}")
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)

    except Exception as e:
        st.error(f"Erro ao ler vivi.db: {e}")
    finally:
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
