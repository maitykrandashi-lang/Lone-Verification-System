import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Financial Transaction Analysis", layout="centered")

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# (Streamlit reruns the whole script on every interaction,
#  so anything that needs to "persist" must live in session_state)
# ---------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "verified" not in st.session_state:
    st.session_state.verified = False
if "doc_type" not in st.session_state:
    st.session_state.doc_type = None

# ---------------------------------------------------------
# DUMMY CREDENTIALS
# Replace this with a real database / auth provider later.
# ---------------------------------------------------------
VALID_USERNAME = "admin"
VALID_PASSWORD = "admin123"


# ---------------------------------------------------------
# PAGE 1: LOGIN
# ---------------------------------------------------------
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.success("Login Successfully")
            st.session_state.logged_in = True
            time.sleep(0.8)
            st.rerun()
        else:
            st.error("Login Failed! Invalid Username or Password.")


# ---------------------------------------------------------
# CHART: SALARY SLIP (pie chart only)
# ---------------------------------------------------------
def salary_slip_chart():
    st.subheader("📊 Salary Slip Breakdown")

    # In a real app, these numbers would come from parsing the
    # uploaded file. Hardcoded here to match your sample data.
    data = {
        "Component": ["Basic Pay", "HRA", "Deductions", "Net Pay"],
        "Amount (Rs.)": [42000, 8000, 3500, 46500],
    }
    df = pd.DataFrame(data)

    fig = px.pie(df, names="Component", values="Amount (Rs.)",
                 title="Salary Component Distribution")
    st.plotly_chart(fig, use_container_width=True)
    st.table(df)


# ---------------------------------------------------------
# CHARTS: BANK STATEMENT (pie chart + bar chart)
# ---------------------------------------------------------
def bank_statement_charts():
    st.subheader("📊 Category Wise Expense")

    data = {
        "Category": ["Food", "Transport", "Recharge", "Shopping", "Bills"],
        "Amount": [5000, 2500, 1000, 4000, 1500],
    }
    df = pd.DataFrame(data)

    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(df, names="Category", values="Amount", title="Expense Share")
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        fig_bar = px.bar(df, x="Category", y="Amount", title="Category Wise Expense")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.table(df)


# ---------------------------------------------------------
# PAGE 2: DOCUMENT UPLOAD
# ---------------------------------------------------------
def upload_page():
    st.title("📄 Document Upload")
    st.write("Select the document type and upload the file for verification.")

    doc_type = st.selectbox("Select Document Type", ["Salary Slip", "Bank Statement"])
    uploaded_file = st.file_uploader(
        "Upload your document",
        type=["pdf", "jpg", "jpeg", "png", "csv", "xlsx"],
    )

    if st.button("Upload"):
        if uploaded_file is not None:
            with st.spinner("Verifying document..."):
                time.sleep(1.5)  # placeholder for real parsing/verification logic
            st.success(f"{doc_type} uploaded and verified successfully!")
            st.session_state.verified = True
            st.session_state.doc_type = doc_type
        else:
            st.warning("Please select a file before uploading.")

    # Show the relevant chart(s) only after successful verification
    if st.session_state.verified:
        st.markdown("---")
        if st.session_state.doc_type == "Salary Slip":
            salary_slip_chart()
        elif st.session_state.doc_type == "Bank Statement":
            bank_statement_charts()

    st.markdown("---")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.verified = False
        st.session_state.doc_type = None
        st.rerun()


# ---------------------------------------------------------
# ROUTER: decides which page to show
# ---------------------------------------------------------
if st.session_state.logged_in:
    upload_page()
else:
    login_page()
