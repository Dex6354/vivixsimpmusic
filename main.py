import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil

st.set_page_config(page_title="SimpMusic Merger", layout="wide")

# O arquivo simpmusic.db original (com todos os dados) deve estar na mesma pasta
BASE_SIMP = "simpmusic.db"

st.title("📂 Atualização de Banco de Dados")
st.write("Mantém todos os dados do SimpMusic e adiciona os IDs do Vivi.")

vivi_file = st.file_uploader("1. Importe o arquivo vivi.db", type=["db"])

if vivi_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix="_vivi.db") as tmp_v:
        tmp_v.write(vivi_file.read())
        path_vivi = tmp_v.name

    try:
        # 1. Extrair os IDs do vivi.db mantendo a ordem
        conn_v = sqlite3.connect(path_vivi)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        st.subheader("IDs capturados da origem")
        st.dataframe(df_ids, use_container_width=True)

        if st.button("🚀 Gerar simpmusic.db Atualizado"):
            if not os.path.exists(BASE_SIMP):
                st.error(f"Erro: O arquivo base '{BASE_SIMP}' não foi encontrado na pasta do script.")
            else:
                # 2. Criar uma cópia física completa do simpmusic.db original
                # Isso garante que todas as 23 tabelas e seus dados permaneçam intactos
                with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_out:
                    output_path = tmp_out.name
                
                shutil.copy2(BASE_SIMP, output_path)

                try:
                    conn_out = sqlite3.connect(output_path)
                    cursor = conn_out.cursor()

                    # 3. Inserir apenas os novos IDs na tabela solicitada
                    # playlistId 1 é usado como padrão para as músicas aparecerem
                    ids_to_insert = [(row['songId'], 1) for _, row in df_ids.iterrows()]
                    
                    cursor.executemany(
                        "INSERT OR IGNORE INTO pair_song_local_playlist (songId, playlistId) VALUES (?, ?)", 
                        ids_to_insert
                    )
                    
                    conn_out.commit()
                    conn_out.close()

                    # 4. Oferecer para download o arquivo que é uma cópia do original + novos IDs
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="📥 BAIXAR simpmusic.db COMPLETO",
                            data=f,
                            file_name="simpmusic.db",
                            mime="application/octet-stream"
                        )
                    st.success("Sucesso! Os IDs foram mesclados ao seu arquivo original.")

                except Exception as e:
                    st.error(f"Erro ao inserir dados: {e}")
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)

    except Exception as e:
        st.error(f"Erro ao ler vivi.db: {e}")
    finally:
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
