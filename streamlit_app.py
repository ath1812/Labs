import streamlit as st

# Define each lab as a page.
lab1_page = st.Page("lab-1.py", title="Lab 1", icon="🧪")
lab2_page = st.Page("lab-2.py", title="Lab 2", icon="🧪", default=True)

# Build the navigation (Lab2 is the default landing page).
pg = st.navigation([lab1_page, lab2_page])
pg.run()