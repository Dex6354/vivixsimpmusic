import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil

st.set_page_config(page_title="Music Database Generator", layout="wide")

BASE_SIMP = "simpmusic.db"

st.title("📂 Gerador de base: Music Database")

vivi_file = st.file_uploader("Importe o arquivo vivi.db", type=["db"])

if vivi_file:
    # Salva o arquivo enviado
    with tempfile.NamedTemporaryFile(delete=False, suffix="_vivi.db") as tmp_v:
        tmp_v.write(vivi_file.read())
        path_vivi = tmp_v.name

    try:
        # 1. Extrair IDs do vivi.db
        conn_v = sqlite3.connect(path_vivi)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_ids['songId'].tolist()
        
        if not lista_ids:
            st.warning("⚠️ Nenhum ID encontrado no arquivo de origem.")
        else:
            st.success(f"✅ {len(lista_ids)} IDs encontrados.")

            if not os.path.exists(BASE_SIMP):
                st.error(f"Arquivo base '{BASE_SIMP}' não encontrado.")
            else:
                # 2. Preparar arquivo de saída em memória ou local temporário persistente
                output_path = "Music_Database_Temp.db"
                shutil.copy2(BASE_SIMP, output_path)

                try:
                    conn_out = sqlite3.connect(output_path)
                    cursor = conn_out.cursor()

                    # Limpa registros existentes para evitar conflitos de posição/ID
                    cursor.execute("DELETE FROM pair_song_local_playlist")

                    # 3. Preparar e Inserir dados
                    dados_insercao = [(s_id, 1, i) for i, s_id in enumerate(lista_ids)]

                    cursor.executemany(
                        "INSERT INTO pair_song_local_playlist (songId, playlistId, position) VALUES (?, ?, ?)", 
                        dados_insercao
                    )
                    
                    conn_out.commit()
                    
                    cursor.execute("SELECT COUNT(*) FROM pair_song_local_playlist")
                    total_final = cursor.fetchone()[0]
                    conn_out.close()

                    # 4. Oferecer Download
                    with open(output_path, "rb") as f:
                        btn = st.download_button(
                            label="📥 BAIXAR MUSIC DATABASE",
                            data=f,
                            file_name="Music Database.db",
                            mime="application/octet-stream"
                        )
                    
                    st.divider()
                    st.write(f"📊 Total de registros na tabela destino: {total_final}")

                except Exception as e:
                    st.error(f"Erro no processamento SQL: {e}")
                
    except Exception as e:
        st.error(f"Erro ao ler vivi.db: {e}")
    finally:
        # Remove arquivos temporários de sistema
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
