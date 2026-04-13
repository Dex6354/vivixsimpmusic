import streamlit as st
from ytmusicapi import YTMusic

# Inicializa a API
yt = YTMusic()

st.set_page_config(page_title="JSON Debugger - AlbumId", layout="wide")

st.title("🐞 Debugger: Captura de AlbumId")

# O ID que você forneceu
VIDEO_ID = "ikFFVfObwss"

if st.button("Capturar JSON com AlbumId"):
    try:
        # get_watch_playlist é o endpoint que contém a relação música-álbum (MPREb...)
        response = yt.get_watch_playlist(VIDEO_ID)
        
        # Tenta localizar o ID no primeiro rastro do objeto
        detected_id = "Não encontrado no JSON"
        if 'tracks' in response and len(response['tracks']) > 0:
            album_obj = response['tracks'][0].get('album', {})
            detected_id = album_obj.get('id', detected_id)

        st.success(f"Processado!")
        st.metric("Album ID Detectado", detected_id)
        
        st.divider()
        st.subheader("📦 JSON Capturado (Watch Playlist)")
        st.write("Expanda o JSON abaixo e procure por: `tracks` -> `[0]` -> `album` -> `id`")
        
        # Exibe o JSON completo onde o MPREb_D5nYt9190Tm deve residir
        st.json(response)
        
    except Exception as e:
        st.error(f"Erro ao capturar dados: {e}")
