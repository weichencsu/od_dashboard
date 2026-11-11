import streamlit as st
from multipage import MultiPage
from spages import PRODUCTION, PEBBLE, WEAR, MILLFILLING, FULLER_PRODUCTION

MAGE_EMOJI_URL = "streamlitBKN.png"
st.set_page_config(page_title='Svedala Dashboard',page_icon=MAGE_EMOJI_URL, initial_sidebar_state = 'expanded', layout="wide")
#page_icon = favicon,

st.markdown(
            f"""
            <style>
                .reportview-container .main .block-container{{
                    max-width: 1500px;
                    padding-top: 0rem;
                    padding-right: 1rem;
                    padding-left: 1rem;
                    padding-bottom: 0rem;
                }}
    
            </style>
            """,
            unsafe_allow_html=True,
        )


app = MultiPage()

# add applications
app.add_page("🔴 Svedala Production Reporting", PRODUCTION.app)
app.add_page("🟠 Fuller Production Reporting", FULLER_PRODUCTION.app)
app.add_page("🔵 Pebble Rate Forecast", PEBBLE.app)
app.add_page("🟢 Liner Wear Forecast", WEAR.app)
app.add_page("🟣 Mill Filling Tools", MILLFILLING.app)


# Run application
if __name__ == '__main__':
    app.run()
