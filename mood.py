import psycopg2
import pandas as pd
import streamlit as st
from datetime import datetime
import yfinance as yf
import matplotlib.pyplot as plt

# ---------------- DB Connection ----------------
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="finance_tracker",
        user="postgres",
        password="Roshni@23",
        port="5432"
    )

# ---------------- DB Helpers ----------------
def insert_mood(mode_text: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "modelog" ("mode", "timestamp") VALUES (%s, %s)',
                (mode_text, datetime.now())
            )
        conn.commit()
    finally:
        conn.close()

def insert_metal_price(metal_name: str, price_per_gram: float):
    # ensure plain float (avoid np.float64 passing into SQL)
    price_per_gram = float(price_per_gram)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "metalprice" ("metalname", "sizepergram", "daterecorded") VALUES (%s, %s, %s)',
                (metal_name, price_per_gram, datetime.now())
            )
        conn.commit()
    finally:
        conn.close()

def fetch_metal_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM "metalprice" ORDER BY "daterecorded" DESC;')
    colnames = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=colnames)
    cur.close()
    conn.close()
    return df

def fetch_mood_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM "modelog" ORDER BY "timestamp" DESC;')
    colnames = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=colnames)
    cur.close()
    conn.close()
    return df
# ---------------- Streamlit UI ----------------
st.title("📊 Finance & Mood Tracker")

# ===== Insert panels
st.subheader("➕ Add Mood")
col1, col2, col3, col4, col5 = st.columns(5)
if col1.button("😊 Happy"):
    insert_mood("Happy")
    st.success("Saved: Happy")
if col2.button("😢 Sad"):
    insert_mood("Sad")
    st.success("Saved: Sad")
if col3.button("😐 Neutral"):
    insert_mood("Neutral")
    st.success("Saved: Neutral")
if col4.button("😫 Stressed"):
    insert_mood("Stressed")
    st.success("Saved: Stressed")
if col5.button("🤩 Excited"):
    insert_mood("Excited")
    st.success("Saved: Excited")

st.markdown("---")

st.subheader("💰 Add Metal Price (Manual)")
c1, c2, c3 = st.columns([2,2,1])
with c1:
    manual_metal = st.selectbox("Metal", ["Gold", "Silver", "Platinum"])
with c2:
    manual_price = st.number_input("Price per gram", min_value=0.0, step=0.01)
with c3:
    if st.button("Save Price"):
        if manual_price > 0:
            insert_metal_price(manual_metal, manual_price)
            st.success(f"Saved: {manual_metal} = {manual_price} per gram")
        else:
            st.error("Enter a valid price.")

st.markdown("---")

st.subheader("⚡ Fetch Gold Price (Free via Yahoo Finance)")
st.caption("Uses futures ticker GC=F (USD). We save the latest close as a quick proxy.")
if st.button("Fetch & Save Gold (GC=F)"):
    try:
        hist = yf.Ticker("GC=F").history(period="1d")
        if hist.empty:
            st.error("No data returned from Yahoo Finance.")
        else:
            latest_close = float(hist["Close"].iloc[-1])   # ensure plain float
            # NOTE: GC=F is USD per troy ounce. If you need per gram or INR, convert:
            #   per_gram_usd = latest_close / 31.1035
            #   per_gram_inr = per_gram_usd * <USD->INR rate>
            per_gram_usd = latest_close / 31.1035
            insert_metal_price("Gold", per_gram_usd)
            st.success(f"Saved Gold ≈ {per_gram_usd:.2f} USD/gram")
    except Exception as e:
        st.error(f"Fetch failed: {e}")

st.markdown("---")

# ===== Tables
st.subheader("💰 Metal Price Records")
metal_df = fetch_metal_data()
st.dataframe(metal_df, use_container_width=True)

st.subheader("🧠 Mood Records")
mood_df = fetch_mood_data()
st.dataframe(mood_df, use_container_width=True)

# ===== Quick Charts
if not metal_df.empty:
    st.subheader("📈 Gold Price Trend (USD/gram)")
    # filter gold only
    gold = metal_df[metal_df["metalname"].str.lower() == "gold"].copy()
    # parse datetime
    gold["daterecorded"] = pd.to_datetime(gold["daterecorded"])
    gold = gold.sort_values("daterecorded")
    if not gold.empty:
        fig = plt.figure()
        plt.plot(gold["daterecorded"], gold["sizepergram"])
        plt.xlabel("Date")
        plt.ylabel("USD per gram")
        plt.title("Gold (USD/gram) over time")
        st.pyplot(fig)
    else:
        st.info("No Gold records yet to chart.")

if not mood_df.empty:
    st.subheader("📊 Mood Frequency")
    counts = mood_df["mode"].value_counts().reset_index()
    counts.columns = ["mode", "Count"]
    fig2 = plt.figure()
    plt.bar(counts["mode"], counts["Count"])
    plt.xlabel("Mood")
    plt.ylabel("Count")
    plt.title("Mood counts")
    st.pyplot(fig2)