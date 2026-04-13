import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile
import json
from ytmusicapi import YTMusic

st.set_page_config(page_title="Music Database Generator", layout="wide")

# Arquivos necessários na raiz do projeto
BASE_SIMP = "simpmusic.db"
SETTINGS_FILE = "settings.preferences_pb"

def format_duration(seconds):
    """Converte segundos para o formato M:SS"""
    try:
        if pd.isna(seconds) or seconds is None:
            return "0:00"
        seconds = int(seconds)
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    except:
        return "0:00"

def find_album_id(obj):
    """Busca recursiva pelo browseId que inicia com MPREb_ (Álbum)"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "browseId" and isinstance(v, str) and v.startswith("MPREb_"):
                return v
            result = find_album_id(v)
            if result: return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_album_id(item)
            if result: return result
    return None

st.title("📂 Gerador de base: Music Database + Album ID")

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
                st.error("Arquivo 'song.db' não encontrado dentro do backup.")
                st.stop()

        # 1. Extrair dados da tabela song do arquivo enviado (Adicionado thumbnailUrl)
        conn_v = sqlite3.connect(path_song_db)
        query = """
            SELECT p.songId, s.duration, s.explicit, s.title, s.thumbnailUrl 
            FROM playlist_song_map p
            LEFT JOIN song s ON p.songId = s.id
            ORDER BY p.rowid
        """
        df_source = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_source['songId'].tolist()
        st.success(f"✅ {len(lista_ids)} IDs e metadados recuperados.")

        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado.")
        elif not os.path.exists(SETTINGS_FILE):
            st.error(f"Arquivo '{SETTINGS_FILE}' não encontrado.")
        else:
            db_output_name = "Music Database"
            db_output_path = os.path.join(proc_dir, db_output_name)
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                yt = YTMusic()
                conn_out = sqlite3.connect(db_output_path)
                cursor = conn_out.cursor()

                # --- 1. LIMPEZA E INSERÇÃO NA TABELA song ---
                cursor.execute("DELETE FROM song")
                
                ts_val = 1775992827379
                dados_song = []
                
                st.write("🔍 Extraindo IDs de Álbum via YTMusic...")
                progress_bar = st.progress(0)
                total_rows = len(df_source)

                for index, row in df_source.iterrows():
                    s_id = row['songId']
                    d_raw = int(row['duration']) if pd.notna(row['duration']) else 0
                    d_fmt = format_duration(d_raw)
                    is_explicit = int(row['explicit']) if pd.notna(row['explicit']) else 0
                    title = str(row['title']) if pd.notna(row['title']) else "Unknown Title"
                    thumb = str(row['thumbnailUrl']) if pd.notna(row['thumbnailUrl']) else None
                    
                    # Lógica de extração do Album ID
                    album_id = None
                    try:
                        response = yt._send_request("next", {"videoId": s_id})
                        album_id = find_album_id(response)
                    except:
                        album_id = None

                    dados_song.append((
                        s_id, d_fmt, d_raw, 1, is_explicit, "INDIFFERENT", title, "Song",
                        0,          # liked
                        0,          # totalPlayTime
                        0,          # downloadState
                        ts_val,     # favoriteAt
                        ts_val,     # downloadedAt
                        ts_val,     # inLibrary
                        None,       # canvasUrl
                        None,       # canvasThumbUrl
                        album_id,   # albumId
                        thumb       # thumbnails (Mapeado de thumbnailUrl)
                    ))
                    
                    progress_bar.progress((index + 1) / total_rows)
                
                query_insert = """
                    INSERT INTO song (
                        videoId, duration, durationSeconds, isAvailable, isExplicit, 
                        likeStatus, title, videoType, liked, totalPlayTime, 
                        downloadState, favoriteAt, downloadedAt, inLibrary, 
                        canvasUrl, canvasThumbUrl, albumId, thumbnails
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.executemany(query_insert, dados_song)

                # --- 2. ATUALIZAÇÃO DA TABELA pair_song_local_playlist ---
                cursor.execute("DELETE FROM pair_song_local_playlist")
                val_in_playlist = 1775992825264
                dados_insercao = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_insercao
                )

                # --- 3. ATUALIZAÇÃO DA TABELA local_playlist ---
                tracks_json = json.dumps(lista_ids)
                cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

                conn_out.commit()
                conn_out.close()

                # 4. Criar o pacote final .backup
                final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
                with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                    zipf.write(db_output_path, arcname=db_output_name)
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                with open(final_backup_path, "rb") as f:
                    backup_data = f.read()
                
                st.divider()
                st.success(f"📊 {total_rows} músicas processadas com sucesso!")
                
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
        shutil.rmtree(proc_dir, ignore_errors=True)
