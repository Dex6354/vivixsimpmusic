import streamlit as st
from ytmusicapi import YTMusic

# Inicializa a API
yt = YTMusic()

st.set_page_config(page_title="JSON Debugger", layout="wide")

st.title("🐞 Debugger: Busca de AlbumId")

# Dados para busca
video_id = "ikFFVfObwss"
search_query = "Highway to Hell AC/DC" # Removido "- Topic" para melhor indexação

if st.button("Buscar Metadados"):
    try:
        # A API search com filtro 'songs' retorna o objeto 'album' com o 'id'
        results = yt.search(search_query, filter="songs")
        
        # Procura o objeto que contém o videoId correto
        match = next((item for item in results if item.get('videoId') == video_id), None)
        
        if match:
            st.subheader("✅ Resultado Encontrado")
            
            # Exibe o albumId detectado de forma clara
            album_id = match.get('album', {}).get('id', "NÃO ENCONTRADO")
            st.code(f"AlbumId extraído: {album_id}")
            
            st.divider()
            st.subheader("📦 JSON Completo")
            # Este é o debugger solicitado
            st.json(match)
        else:
            st.warning("Música não encontrada nos resultados de busca com este ID.")
            st.write("Resultados da busca geral para análise:")
            st.json(results)
            
    except Exception as e:
        st.error(f"Erro ao acessar a API: {e}")
