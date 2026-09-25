import streamlit as st

lab1_page = st.Page("lab-1.py", title="Lab 1", icon="🧪", default=True)
lab2_page = st.Page("lab-2.py", title="Lab 2", icon="🧪")
lab3_page = st.Page("lab-3.py", title="Lab 3", icon="🧪")
lab4_page = st.Page("lab-4.py", title="Lab 4", icon="🧪")
lab5_page = st.Page("lab-5.py", title="Lab 5", icon="🧪")
pg = st.navigation([lab1_page, lab2_page, lab3_page,lab4_page, lab5_page])
pg.run()