import streamlit as st
from ytmusicapi import YTMusic

# Inicializa a API
yt = YTMusic()

st.set_page_config(page_title="AlbumId Finder", layout="wide")

st.title("🔍 Localizador de albumId")

# Dados extraídos da URL fornecida
video_id = "ikFFVfObwss"
search_query = "Highway to Hell AC/DC"

if st.button("Extrair albumId e Gerar JSON"):
    try:
        # 1. Realiza a busca filtrando por 'songs' para obter o objeto de música oficial
        search_results = yt.search(search_query, filter="songs")
        
        # 2. Procura o item que corresponde ao videoId
        match = next((item for item in search_results if item.get('videoId') == video_id), None)
        
        # Fallback: Se não houver match exato, tenta o primeiro resultado da busca
        if not match and search_results:
            match = search_results[0]

        if match:
            # Captura o albumId (browseId)
            album_id = match.get('album', {}).get('id', "Não encontrado")
            
            st.success(f"Busca finalizada!")
            st.metric("Album ID Encontrado", album_id)
            
            st.divider()
            st.subheader("🐞 Debugger JSON")
            st.write("Inspecione o campo `'album' -> 'id'` abaixo:")
            st.json(match)
        else:
            st.error("Não foi possível encontrar um objeto de música correspondente a este ID.")
            
    except Exception as e:
        st.error(f"Erro na API: {e}")
