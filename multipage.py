import streamlit as st

class MultiPage:
    """Framework for combining multiple streamlit applications
    """
    def __init__(self) -> None:
        self.pages = []
    
    def add_page(self, title, func):
        self.pages.append(
            {
            'title': title,
            'function': func
            }
        )
    
    def run(self):
        #st.sidebar.title("Grind Master")
        page = st.logo("logo.png")
        page = st.sidebar.header(":rainbow[Svedala Performance Reporting App]")
        page = st.sidebar.image("mill.png", width=300)
        page = st.sidebar.header("***Next Gen Grinding Intelligence***", divider='gray')
        page = st.sidebar.markdown("###")
        page = st.sidebar.markdown("###")
        page = st.sidebar.markdown("###")
        page = st.sidebar.radio(
            'App Navigation', 
            self.pages,
            format_func=lambda page: page['title']  # Function to modify the display of the labels.

        )
        page['function']()
