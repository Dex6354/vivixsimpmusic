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
        with zipfile.ZipFile(path_vivi_backup, 'r') as z:
            if "song.db" in z.namelist():
                z.extract("song.db", proc_dir)
            else:
                st.error("Arquivo 'song.db' não encontrado no backup.")
                st.stop()

        # 1. Mapeamento de Colunas
        conn_source = sqlite3.connect(path_song_db)
        cols_source = get_columns(conn_source, "song")
        
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo '{BASE_SIMP}' não encontrado na raiz.")
            st.stop()
            
        conn_dest_check = sqlite3.connect(BASE_SIMP)
        cols_dest = get_columns(conn_dest_check, "song")
        conn_dest_check.close()

        # Colunas que existem com o mesmo nome em ambos
        common_cols = [c for c in cols_source if c in cols_dest and c not in ['id', 'videoId']]
        
        # 2. Extração de dados (Mapeando 'id' da origem para 'videoId' do destino)
        # No song2.db a chave é 'id', no Music Database a chave é 'videoId'
        query_source = f"SELECT id as videoId, {', '.join(common_cols)} FROM song"
        df_metadata = pd.read_sql_query(query_source, conn_source)
        
        # Pega a ordem da playlist
        lista_ids = pd.read_sql_query("SELECT songId FROM playlist_song_map ORDER BY rowid", conn_source)['songId'].tolist()
        conn_source.close()

        # 3. Gerar novo banco
        db_output_name = "Music Database"
        db_output_path = os.path.join(proc_dir, db_output_name)
        shutil.copy2(BASE_SIMP, db_output_path)

        try:
            conn_out = sqlite3.connect(db_output_path)
            cursor = conn_out.cursor()

            # Inserção na tabela 'song' (videoId + colunas comuns)
            all_target_cols = ['videoId'] + common_cols
            placeholders = ", ".join(["?"] * len(all_target_cols))
            sql_insert_song = f"INSERT OR REPLACE INTO song ({', '.join(all_target_cols)}) VALUES ({placeholders})"
            
            cursor.executemany(sql_insert_song, df_metadata.values.tolist())

            # Atualização da junção (pair_song_local_playlist)
            cursor.execute("DELETE FROM pair_song_local_playlist")
            val_in_playlist = 1775992825264
            dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
            cursor.executemany(
                "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                dados_pair
            )

            # Atualização da lista JSON (tracks)
            tracks_json = json.dumps(lista_ids)
            cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

            conn_out.commit()
            conn_out.close()

            # 4. ZIP/Backup Final
            final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
            with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                zipf.write(db_output_path, arcname=db_output_name)
                if os.path.exists(SETTINGS_FILE):
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

            with open(final_backup_path, "rb") as f:
                st.success(f"✅ Sucesso! {len(lista_ids)} músicas sincronizadas visualmente.")
                st.download_button(
                    label="📥 BAIXAR SIMPMUSIC.BACKUP",
                    data=f.read(),
                    file_name="simpmusic.backup",
                    mime="application/octet-stream"
                )

        except Exception as e:
            st.error(f"Erro ao gravar dados: {e}")
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
