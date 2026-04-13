import streamlit as st
from ytmusicapi import YTMusic
import json

yt = YTMusic()

st.set_page_config(page_title="Deep JSON Debugger", layout="wide")
st.title("🐞 Deep Debugger: ikFFVfObwss")

VIDEO_ID = "ikFFVfObwss"

if st.button("Forçar Varredura de Metadados"):
    try:
        # Método que acessa os dados do player do YouTube Music
        raw_data = yt.get_song(VIDEO_ID)
        
        st.subheader("📦 Resposta Completa da API")
        st.write("Procure por 'browseId' ou 'albumId' dentro dos campos abaixo:")
        
        # Exibe o JSON bruto para inspeção manual
        st.json(raw_data)
        
        # Tentativa de extração automática via Microformat
        try:
            microformat = raw_data.get('microformat', {}).get('microformatDataRenderer', {})
            st.divider()
            st.subheader("📌 Possível Localização:")
            st.write(f"Link de navegação: {microformat.get('urlCanonical')}")
        except:
            pass
            
    except Exception as e:
        st.error(f"Erro ao acessar os dados: {e}")
