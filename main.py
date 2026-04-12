import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile

st.set_page_config(page_title="Music Database Generator", layout="wide")

# Arquivos necessários na raiz do projeto
BASE_SIMP = "simpmusic.db"
SETTINGS_FILE = "settings.preferences_pb"

st.title("📂 Gerador de base: Music Database")

# Upload do arquivo .backup (que internamente é um ZIP com song.db)
vivi_file = st.file_uploader("Importe o arquivo .backup", type=["backup"])

if vivi_file:
    # Criamos um diretório temporário para processar os arquivos internos
    proc_dir = tempfile.mkdtemp()
    path_vivi_backup = os.path.join(proc_dir, "vivi_upload.backup")
    path_song_db = os.path.join(proc_dir, "song.db")

    with open(path_vivi_backup, "wb") as f:
        f.write(vivi_file.read())

    try:
        # 1. Abrir o ZIP (.backup) e extrair apenas o song.db
        with zipfile.ZipFile(path_vivi_backup, 'r') as z:
            # Verifica se song.db existe dentro do backup
            if "song.db" in z.namelist():
                z.extract("song.db", proc_dir)
            else:
                st.error("Arquivo 'song.db' não encontrado dentro do backup.")
                st.stop()

        # 2. Extrair IDs do song.db extraído
        conn_v = sqlite3.connect(path_song_db)
        # Note: Ajustei o nome da tabela para 'playlist_song_map' conforme seu código anterior
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_ids['songId'].tolist()
        st.success(f"✅ {len(lista_ids)} IDs encontrados no arquivo song.db.")

        # Verificação de arquivos na raiz para a montagem do novo arquivo
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado na raiz.")
        elif not os.path.exists(SETTINGS_FILE):
            st.error(f"Arquivo '{SETTINGS_FILE}' não encontrado na raiz.")
        else:
            # 3. Preparar o novo arquivo "Music Database"
            db_output_name = "Music Database"
            db_output_path = os.path.join(proc_dir, db_output_name)
            
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                # Processamento do SQL no novo banco
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

                # 4. Criar o pacote final .backup (contendo Music Database e settings.preferences_pb)
                final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
                with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                    zipf.write(db_output_path, arcname=db_output_name)
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                # 5. Botão de Download
                with open(final_backup_path, "rb") as f:
                    backup_data = f.read()
                
                st.divider()
                st.write(f"📊 Total de registros na tabela destino: {total_final}")
                
                st.download_button(
                    label="📥 BAIXAR SIMPMUSIC.BACKUP",
                    data=backup_data,
                    file_name="simpmusic.backup",
                    mime="application/octet-stream"
                )

            except Exception as e:
                st.error(f"Erro ao processar banco de dados: {e}")
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo enviado: {e}")
    finally:
        # Limpa todos os arquivos temporários criados no diretório proc_dir
        shutil.rmtree(proc_dir, ignore_errors=True)
