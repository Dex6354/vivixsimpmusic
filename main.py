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
        st.info(f"🔍 {len(lista_ids)} IDs lidos do arquivo de origem.")

        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado.")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_out:
                output_path = tmp_out.name
            
            shutil.copy2(BASE_SIMP, output_path)

            try:
                conn_out = sqlite3.connect(output_path)
                cursor = conn_out.cursor()

                # 2. Garantir que os IDs existam na tabela 'song' (obrigatório para o app mostrar)
                # Inserimos com valores genéricos para não dar erro de NOT NULL
                for s_id in lista_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO song (id, title, duration, liked, totalPlayTime, isLocal) 
                        VALUES (?, ?, 0, 0, 0, 0)
                    """, (s_id, "Música Importada"))

                # 3. Limpar a playlist atual e inserir a nova sequência
                cursor.execute("DELETE FROM pair_song_local_playlist")
                
                dados_playlist = []
                for i, s_id in enumerate(lista_ids):
                    # Usando playlistId 1 e a posição sequencial
                    dados_playlist.append((s_id, 1, i))

                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position) VALUES (?, ?, ?)", 
                    dados_playlist
                )
                
                conn_out.commit()
                
                # Verificação
                cursor.execute("SELECT COUNT(*) FROM pair_song_local_playlist")
                check_count = cursor.fetchone()[0]
                conn_out.close()

                with open(output_path, "rb") as f:
                    file_data = f.read()
                
                st.success(f"✅ Sucesso! {check_count} músicas prontas para download.")
                
                st.download_button(
                    label="📥 BAIXAR MUSIC DATABASE",
                    data=file_data,
                    file_name="Music Database.db",
                    mime="application/octet-stream"
                )

            except Exception as e:
                st.error(f"Erro na gravação: {e}")
            finally:
                if os.path.exists(output_path): os.remove(output_path)

    except Exception as e:
        st.error(f"Erro no vivi.db: {e}")
    finally:
        if os.path.exists(path_vivi): os.remove(path_vivi)
