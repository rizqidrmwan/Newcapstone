import streamlit as st
import pandas as pd
from langdetect import detect
import matplotlib.pyplot as plt
from datetime import datetime
import re
import logging
import os
from collections import Counter
from wordcloud import WordCloud

# Konfigurasi logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app_debug.log")
    ]
)

# Kamus kata positif dan negatif untuk analisis Bahasa Indonesia
positive_words = ["baik", "puas", "hebat", "bagus", "indah", "terima kasih", "senang", "suka", "luar biasa", "memuaskan", "ramah", "cepat", "mantap", "bagus sekali", "menyenangkan"]
negative_words = ["buruk", "jelek", "kecewa", "benci", "sedih", "marah", "tidak puas", "payah", "mengecewakan", "parah", "lambat", "sombong", "melelahkan", "tidak ramah", "parah sekali", "gagal", "kesal"]

# Daftar kata untuk menangani negasi
negation_words = ["tidak", "bukan", "kurang", "jangan", "gagal"]

def preprocess_text(text):
    text = re.sub(r'[^\w\s]', '', text)  # Menghapus tanda baca
    text = re.sub(r'\s+', ' ', text).strip().lower()  # Menghilangkan spasi ganda dan mengubah teks menjadi huruf kecil
    return text

def analyze_sentiment_id(text):
    text = preprocess_text(text)
    positive_score = sum(1 for word in positive_words if word in text)
    negative_score = sum(1 for word in negative_words if word in text)

    # Deteksi negasi dalam teks, yang bisa mengubah sentimen
    for neg_word in negation_words:
        if neg_word in text:
            # Jika terdapat negasi, sentimen positif bisa berubah menjadi negatif
            if positive_score > negative_score:
                return "Negatif", negative_score - positive_score
            else:
                return "Negatif", negative_score - positive_score

    if positive_score > negative_score:
        return "Positif", positive_score - negative_score
    elif negative_score > positive_score:
        return "Negatif", negative_score - positive_score
    else:
        return "Netral", 0

def detect_language(text):
    try:
        if not text.strip():
            return "unknown"
        return detect(text)
    except Exception as e:
        logging.warning(f"Deteksi bahasa gagal: {e}")
        return "unknown"

def log_analysis(user_input, sentiment, score, lang):
    log_data = {
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Input": [user_input],
        "Sentiment": [sentiment],
        "Score": [score],
        "Language": [lang]
    }
    log_df = pd.DataFrame(log_data)
    try:
        log_df.to_csv("user_analysis_log.csv", mode="a", index=False, header=False)
        update_github_log()
    except Exception as e:
        st.error(f"Gagal menyimpan log: {e}")

def update_github_log():
    try:
        # Ambil token dari environment variable
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise Exception("Token GitHub tidak ditemukan di environment variable.")

        # Nama repositori di GitHub
        repo_name = "Amicalista/Analisis-Sentiment-Gojek-Indonesia"
        file_path = "user_analysis_log.csv"

        # Autentikasi ke GitHub
        g = Github(github_token)
        repo = g.get_repo(repo_name)

        # Ambil file dari repositori
        contents = repo.get_contents(file_path)
        with open(file_path, "r") as file:
            content = file.read()

        # Perbarui file di GitHub
        repo.update_file(contents.path, "Update log file", content, contents.sha)
        logging.info("Log berhasil diperbarui di GitHub.")
    except Exception as e:
        logging.error(f"Gagal memperbarui log di GitHub: {e}")

# Fungsi untuk menghasilkan word cloud
def generate_word_cloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    return wordcloud

st.set_page_config(page_title="Aplikasi Analisis Sentimen", page_icon="📊", layout="wide")

st.title("📊 Analisis Sentimen")
st.markdown("""
Aplikasi ini memungkinkan Anda untuk menganalisis sentimen teks baik secara manual maupun dari file CSV yang diunggah.
**Mendukung Bahasa Indonesia!**
""")

# Input teks manual
st.subheader("1. Masukkan Teks untuk Analisis")
input_text = st.text_area("Masukkan teks untuk dianalisis:", height=150, key="input_text_area")

if st.button("Analisis Sentimen"):
    if input_text:
        lang = detect_language(input_text)
        if lang == "id":
            sentiment, score = analyze_sentiment_id(input_text)
        else:
            sentiment, score = "Tidak Diketahui", "N/A"

        st.markdown("**Hasil Analisis Sentimen:**")
        st.write(f"Sentimen: **{sentiment}**")
        st.write(f"Skor Sentimen (nilai numerik): **{score}**")
        st.write(f"Bahasa yang terdeteksi: **{lang}**")

        log_analysis(input_text, sentiment, score, lang)

        # Menampilkan word cloud dari teks
        wordcloud_image = generate_word_cloud(input_text)
        st.image(wordcloud_image.to_array(), caption="Word Cloud dari Teks Masukkan", use_column_width=True)

        if score != "N/A":
            colors = {"Positif": "green", "Negatif": "red", "Netral": "gray"}
            fig, ax = plt.subplots()
            ax.bar([sentiment], [score], color=colors.get(sentiment, "blue"))
            ax.set_title("Hasil Analisis Sentimen")
            ax.set_ylabel("Skor")
            st.pyplot(fig)

# Unggah file CSV untuk analisis
st.subheader("2. Unggah File CSV untuk Analisis Sentimen")
uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.markdown("**Data yang Diupload:**")
    st.dataframe(df)

    text_column = st.selectbox("Pilih kolom teks untuk dianalisis:", df.columns)

    if text_column:
        st.write(f"Menganalisis sentimen pada kolom '{text_column}'...")
        df[['sentiment', 'sentiment_score']] = df[text_column].apply(lambda x: pd.Series(analyze_sentiment_id(x)))

        st.markdown("**Hasil Analisis Sentimen:**")
        st.dataframe(df[[text_column, 'sentiment', 'sentiment_score']])

        for _, row in df.iterrows():
            log_analysis(row[text_column], row['sentiment'], row['sentiment_score'], "id")

        sentiment_counts = df['sentiment'].value_counts()
        fig, ax = plt.subplots()
        sentiment_counts.plot(kind='bar', color=['green', 'red', 'gray'], ax=ax)
        ax.set_title("Distribusi Sentimen")
        ax.set_xlabel("Sentimen")
        ax.set_ylabel("Jumlah")
        st.pyplot(fig)

        # Menampilkan word cloud dari file CSV
        st.markdown("**Word Cloud dari File CSV:**")
        common_words_all = ' '.join(df[text_column].dropna()).lower()
        wordcloud_image_csv = generate_word_cloud(common_words_all)
        st.image(wordcloud_image_csv.to_array(), caption="Word Cloud dari Data CSV", use_column_width=True)
    else:
        st.warning("Kolom teks tidak dipilih. Pastikan memilih kolom yang berisi teks.")
