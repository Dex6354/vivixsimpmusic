import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile
import json

st.set_page_config(page_title="Music Database Generator", layout="wide")

BASE_SIMP = "simpmusic.db"
SETTINGS_FILE = "settings.preferences_pb"

def get_columns(conn, table_name):
    """Retorna uma lista com os nomes das colunas de uma tabela."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

st.title("📂 Gerador de base: Music Database")

vivi_file = st.file_uploader("Importe o arquivo .backup", type=["backup"])

if vivi_file:
    proc_dir = tempfile.mkdtemp()
    path_vivi_backup = os.path.join(proc_dir, "vivi_upload.backup")
    path_song_db = os.path.join(proc_dir, "song.db")

    with open(path_vivi_backup, "wb") as f:
        f.write(vivi_file.read())

    try:
        # 1. Extrair song.db do backup enviado
        with zipfile.ZipFile(path_vivi_backup, 'r') as z:
            if "song.db" in z.namelist():
                z.extract("song.db", proc_dir)
            else:
                st.error("Arquivo 'song.db' não encontrado dentro do backup.")
                st.stop()

        # 2. Identificar colunas comuns entre song2 (origem) e Music Database (destino)
        conn_source = sqlite3.connect(path_song_db)
        cols_source = get_columns(conn_source, "song")
        
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo '{BASE_SIMP}' não encontrado.")
            st.stop()
            
        conn_dest_temp = sqlite3.connect(BASE_SIMP)
        cols_dest = get_columns(conn_dest_temp, "song")
        conn_dest_temp.close()

        # Filtra apenas as colunas que existem em ambos os bancos
        common_cols = [c for c in cols_source if c in cols_dest]
        
        if not common_cols:
            st.error("Nenhuma coluna correspondente encontrada entre os bancos de dados.")
            st.stop()

        # Lê os dados das colunas comuns do arquivo enviado
        query_source = f"SELECT {', '.join(common_cols)} FROM song"
        df_metadata = pd.read_sql_query(query_source, conn_source)
        
        # Pega a ordem da playlist
        lista_ids = pd.read_sql_query("SELECT songId FROM playlist_song_map ORDER BY rowid", conn_source)['songId'].tolist()
        conn_source.close()

        st.success(f"✅ Colunas sincronizadas: {', '.join(common_cols)}")

        # 3. Gerar o novo banco de dados
        db_output_name = "Music Database"
        db_output_path = os.path.join(proc_dir, db_output_name)
        shutil.copy2(BASE_SIMP, db_output_path)

        try:
            conn_out = sqlite3.connect(db_output_path)
            cursor = conn_out.cursor()

            # Inserção dinâmica na tabela song
            placeholders = ", ".join(["?"] * len(common_cols))
            sql_insert_song = f"INSERT OR REPLACE INTO song ({', '.join(common_cols)}) VALUES ({placeholders})"
            cursor.executemany(sql_insert_song, df_metadata.values.tolist())

            # Atualização da tabela de junção (playlist)
            cursor.execute("DELETE FROM pair_song_local_playlist")
            val_in_playlist = 1775992825264
            # Assume-se que a coluna de ID na tabela destino é 'songId' ou similar
            # Aqui usamos lista_ids que veio de playlist_song_map do backup
            dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
            cursor.executemany(
                "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                dados_pair
            )

            # Atualização da coluna tracks (JSON) na local_playlist
            tracks_json = json.dumps(lista_ids)
            cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

            conn_out.commit()
            conn_out.close()

            # 4. Empacotar tudo de volta no .backup
            final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
            with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                zipf.write(db_output_path, arcname=db_output_name)
                if os.path.exists(SETTINGS_FILE):
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

            with open(final_backup_path, "rb") as f:
                st.download_button(
                    label="📥 BAIXAR SIMPMUSIC.BACKUP",
                    data=f.read(),
                    file_name="simpmusic.backup",
                    mime="application/octet-stream"
                )

        except Exception as e:
            st.error(f"Erro ao gravar no banco de destino: {e}")
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
