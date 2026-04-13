import streamlit as st
from ytmusicapi import YTMusic

yt = YTMusic()

st.set_page_config(page_title="JSON AlbumId Finder", layout="wide")
st.title("🐞 Debugger de Precisão: MPREb_D5nYt9190Tm")

VIDEO_ID = "ikFFVfObwss"

if st.button("Capturar Objeto com AlbumId"):
    try:
        # Este endpoint é o que vincula o vídeo ao contexto do álbum oficial
        data = yt.get_watch_playlist(VIDEO_ID)
        
        # Filtro para o Debugger: foca no primeiro item da lista de faixas
        # onde o YouTube Music armazena o browseId do álbum
        target_track = {}
        if 'tracks' in data and len(data['tracks']) > 0:
            target_track = data['tracks'][0]

        st.success("JSON capturado!")
        
        # Mostramos o campo específico primeiro para conferência
        album_data = target_track.get('album', {})
        st.write(f"**Album ID detectado no objeto:** `{album_data.get('id')}`")

        st.divider()
        st.subheader("📦 JSON Completo (Foco: tracks[0])")
        st.write("Verifique o campo `'album'` -> `'id'` dentro deste JSON:")
        
        # O debugger focado no objeto que contém o ID que você busca
        st.json(target_track)
        
        with st.expander("Ver Resposta Completa da API (Raw)"):
            st.json(data)
            
    except Exception as e:
        st.error(f"Erro ao capturar dados: {e}")
