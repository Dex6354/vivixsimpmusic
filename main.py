import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile

st.set_page_config(page_title="Music Database Generator", layout="wide")

# Arquivos necessários
BASE_SIMP = "simpmusic.db"
SETTINGS_FILE = "settings.preferences_pb"

st.title("📂 Gerador de base: Music Database")

vivi_file = st.file_uploader("Importe o arquivo vivi.db", type=["db"])

if vivi_file:
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
        st.success(f"✅ {len(lista_ids)} IDs encontrados no arquivo de origem.")

        # Verificação de arquivos na raiz
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado na raiz.")
        elif not os.path.exists(SETTINGS_FILE):
            st.error(f"Arquivo '{SETTINGS_FILE}' não encontrado na raiz.")
        else:
            # 2. Preparar pasta temporária para o ZIP
            temp_dir = tempfile.mkdtemp()
            db_output_name = "Music Database"
            db_output_path = os.path.join(temp_dir, db_output_name)
            
            # Copia o banco original para o novo nome (sem .db)
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                # Processamento do SQL
                conn_out = sqlite3.connect(db_output_path)
                cursor = conn_out.cursor()
                cursor.execute("DELETE FROM pair_song_local_playlist")

                val_in_playlist = 1775992825264
                dados_insercao = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]

                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_insercao
                )
                conn_out.commit()
                
                cursor.execute("SELECT COUNT(*) FROM pair_song_local_playlist")
                total_final = cursor.fetchone()[0]
                conn_out.close()

                # 3. Criar o arquivo ZIP
                zip_path = os.path.join(temp_dir, "simpmusic.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    # Adiciona o banco gerado
                    zipf.write(db_output_path, arcname=db_output_name)
                    # Adiciona o arquivo de preferências da raiz
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                # 4. Botão de Download
                with open(zip_path, "rb") as f:
                    zip_data = f.read()
                
                st.divider()
                st.write(f"📊 Total de registros na tabela destino: {total_final}")
                
                st.download_button(
                    label="📥 BAIXAR SIMPMUSIC.ZIP",
                    data=zip_data,
                    file_name="simpmusic.zip",
                    mime="application/zip"
                )

            except Exception as e:
                st.error(f"Erro ao processar banco de dados: {e}")
            finally:
                # Limpa a pasta temporária
                shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        st.error(f"Erro ao ler vivi.db: {e}")
    finally:
        if os.path.exists(path_vivi):
            os.remove(path_vivi)
