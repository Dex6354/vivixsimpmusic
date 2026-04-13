import streamlit as st
from ytmusicapi import YTMusic

# Inicializa a API
yt = YTMusic()

st.set_page_config(page_title="JSON Album Debugger", layout="wide")

st.title("🐞 Debugger: Captura de MPREb_D5nYt9190Tm")

VIDEO_ID = "ikFFVfObwss"

if st.button("Executar Busca Profunda"):
    try:
        # Buscamos o ID diretamente. O YouTube Music retorna o objeto 'Track' 
        # que contém a prateleira de álbum completa.
        search_results = yt.search(VIDEO_ID)
        
        # Filtra pelo vídeo exato
        match = next((item for item in search_results if item.get('videoId') == VIDEO_ID), None)
        
        if match:
            st.success("Objeto encontrado!")
            
            # O MPREb_ costuma estar em match['album']['id']
            # O MPLYt_ (que você viu) é o ID da playlist do álbum, o MPREb_ é o ID do álbum em si.
            album_id = match.get('album', {}).get('id', "Não encontrado no nível 1")
            st.code(f"Album ID: {album_id}")
            
            st.divider()
            st.subheader("📦 JSON Completo")
            st.json(match)
        else:
            st.warning("Não foi possível encontrar o objeto Track para este ID. Mostrando resultados gerais:")
            st.json(search_results)
            
    except Exception as e:
        st.error(f"Erro na API: {e}")
