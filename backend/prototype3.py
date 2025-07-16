import os
import math
import streamlit as st
from typing import Optional
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


# --- Konfigurasi Awal ---S
load_dotenv()
if os.getenv("GOOGLE_API_KEY"):
    print("✅ API Key berhasil dimuat.")
else:
    print("❌ ERROR: GOOGLE_API_KEY tidak ditemukan.")

# ==============================================================================

# --- Tool 1: Khusus untuk Office Tower ---
class OfficeTowerInput(BaseModel):
    """Input spesifik untuk kalkulasi manpower di Office Tower."""
    jumlah_lantai_aktif: int = Field(description="Jumlah lantai kerja yang perlu dibersihkan.")
    is_trafik_lobby_padat: bool = Field(description="Apakah trafik di lobi utama tergolong padat? (True/False)")
    is_trafik_lantai_padat: bool = Field(description="Apakah trafik di lantai kerja (koridor) tergolong padat? (True/False)")
    jumlah_lobby: int = Field(description="Jumlah lobi utama.")
    jumlah_lantai_basement: Optional[int] = Field(default=0, description="Jumlah lantai basement (hanya yang di bawah tanah).")
    luas_area_hijau: Optional[int] = Field(default=0, description="Total luas area taman/hijau dalam m².")
    apakah_perlu_ob: bool = Field(description="Apakah klien membutuhkan jasa Office Boy (OB)?")
    jumlah_ob: Optional[int] = Field(default=0, description="Jumlah OB yang dibutuhkan jika perlu.")
    apakah_ada_gondola: bool = Field(default=False, description="Apakah gedung dilengkapi dengan unit gondola?")
    jumlah_unit_gondola: Optional[int] = Field(default=0, description="Jumlah unit gondola jika ada.")
    butuh_jasa_rappelling: Optional[bool] = Field(default=False, description="Apakah klien membutuhkan jasa pembersihan rappelling?")
    jumlah_shift: int = Field(description="Jumlah shift kerja per hari (misal: 1, 2, atau 3).")

@tool(args_schema=OfficeTowerInput)
def estimasi_office_tower(**kwargs) -> dict:
    """Gunakan tool ini HANYA untuk menghitung kebutuhan manpower untuk properti tipe Office Tower."""
    print(f"\n[Sistem] === Tool 'estimasi_office_tower' dieksekusi dengan data: {kwargs} ===")

 # 1. Tim Gardener
    gardener = math.ceil(kwargs.get("luas_area_hijau", 0) / 1500)

    # 2. Tim Lobi
    cso_lobby = kwargs.get("jumlah_lobby", 1) * (2 if kwargs.get("is_trafik_lobby_padat", False) else 1)

    # 3. Tim Lantai (CSO Zona)
    lantai_aktif = kwargs.get("jumlah_lantai_aktif", 0)
    zona = 3 if kwargs.get("is_trafik_lantai_padat", False) else 8
    cso_lantai = math.ceil(lantai_aktif / zona) * 2

    # 4. Tim Basement
    cso_basement = math.ceil(kwargs.get("jumlah_lantai_basement", 0) / 2)

    # 5. Tim Fasad
    tim_fasad = 0
    if kwargs.get("apakah_ada_gondola", False):
        tim_fasad = kwargs.get("jumlah_unit_gondola", 0) * 3
    elif kwargs.get("butuh_jasa_rappelling", False):
        tim_fasad = 2

    # 6. Tim Office Boy
    jumlah_ob = kwargs.get("jumlah_ob", 0) if kwargs.get("apakah_perlu_ob", False) else 0

    # Total CSO
    total_cso = cso_lobby + cso_lantai + cso_basement

    # Perhitungan Tim Manajerial
    jumlah_shift = kwargs.get("jumlah_shift", 1)
    total_tl = jumlah_shift
    total_spv = 1
    sub_total_operasional = total_cso + total_tl + total_spv + gardener + tim_fasad + jumlah_ob
    jumlah_admin = 1 if sub_total_operasional > 30 else 0
    total_manpower = sub_total_operasional + jumlah_admin

    # Distribusi per Shift
    rincian_shift = {}
    if jumlah_shift == 3:
        cso_siang = math.ceil(total_cso * 0.5)
        cso_sore = math.ceil(total_cso * 0.3)
        cso_malam = total_cso - cso_siang - cso_sore if (total_cso - cso_siang - cso_sore > 0) else 0
        rincian_shift = {"Shift Siang": f"{cso_siang} CSO, 1 TL", "Shift Sore": f"{cso_sore} CSO, 1 TL", "Shift Malam": f"{cso_malam} CSO, 1 TL"}
    elif jumlah_shift == 2:
        cso_siang = math.ceil(total_cso * 0.6)
        cso_malam = total_cso - cso_siang
        rincian_shift = {"Shift Siang": f"{cso_siang} CSO, 1 TL", "Shift Sore/Malam": f"{cso_malam} CSO, 1 TL"}
    else:
        rincian_shift = {"Shift Siang": f"{total_cso} CSO, {total_tl} TL"}
    
    hasil = {
        "estimasi_total_manpower": total_manpower,
        "rincian_tim": {"CSO (Total)": total_cso, "Team Leader": total_tl, "Supervisor": total_spv, "Admin": jumlah_admin, "Gardener": gardener, "Tim Fasad": tim_fasad, "Office Boy (OB)": jumlah_ob},
        "distribusi_per_shift": rincian_shift
    }
    return hasil

# --- Tool 2: Khusus untuk Mall ---
class MallInput(BaseModel):
    """Input spesifik untuk kalkulasi manpower di Mall."""
    luas_area_total: int = Field(description="Luas area total Mall dalam m².")
    jumlah_lantai: int = Field(description="Jumlah lantai di Mall.")
    kapasitas_pengunjung: int = Field(description="Estimasi kapasitas pengunjung harian.")
    jumlah_shift: int = Field(description="Jumlah shift kerja per hari.")

@tool(args_schema=MallInput)
def estimasi_mall(luas_area_total: int, jumlah_lantai: int, kapasitas_pengunjung: int, jumlah_shift: int) -> dict:
    """Gunakan tool ini HANYA untuk menghitung kebutuhan manpower untuk properti tipe Mall."""
    cso_area = math.ceil(luas_area_total / 1500)
    cso_lantai = math.ceil(jumlah_lantai / 2)
    cso_toilet = 8 if kapasitas_pengunjung > 1000 else 4
    total_cso = cso_area + cso_lantai + cso_toilet
    total_tl = jumlah_shift
    total_manpower = total_cso + total_tl + 1 # SPV
    return {"estimasi_total_manpower": total_manpower, "rincian": {"CSO": total_cso, "TL": total_tl, "SPV": 1}}

def buat_pdf(user_data: dict, chat_history: list) --> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size = 12)

    # Informasi Klien
    pdf.set_font("Arial", "B", 16)
    pdf.fell(200, 10, txt = "Laporan Estimasi Manpower", ln = True, align = "C")
    pdf.ln(10)


# ==============================================================================

# Ajari AI untuk menjadi "Dispatcher" yang memilih tool yang tepat
def setup_agent():
    print("Membuat agent baru...")
    tools = [estimasi_office_tower, estimasi_mall]
    SYSTEM_PROMPT = """
    Anda adalah "Hoffbot", AI konsultan dari PT. Hoffmen Cleanindo.
    Tugas Anda adalah memilih tool yang tepat berdasarkan tipe properti yang disebutkan pengguna.

    ALUR WAWANCARA ANDA DENGAN KLIEN UNTUK **OFFICE TOWER / GEDUNG PERKANTORAN**:
    1. Sapa pengguna dan konfirmasi bahwa mereka ingin menghitung kebutuhan manpower tim cleaning di properti Office Tower.
    2. Tanyakan pertanyaan berikut **secara berurutan** untuk mengumpulkan data. jangan lanjut sebelum pertanyaan terjawab.
        a. Berapa **Jumlah Lantai Aktif** yang perlu dibersihkan (tidak termasuk lobby dan basement)?
        b. Apakah **Trafik di Lantai Kerja** tergolong **Padat**? (Ya/Tidak)
        C. Berapa **Jumlah Lobi Utama** di gedung tersebut?
        d. Apakah **Trafik di Lobi Utama** tergolong Padat**? (Ya/Tidak)
        e. Apakah ada **Lantai Basement**? Jika ya, berapa lantai?
        f. Apakah ada **Area Taman/Hijau**? Jika ya, berapa perkiraan luasnya dalam meter persegi?
        g. Untuk pembersihan kaca luar, tanyakan **"Apakah gedung memiliki Mesin Gondola?"** (Ya/Tidak).
        - **JIKA JAWABANNYA 'YA'**: Ajukan pertanyaan lanjutan yang WAJIB dijawab: **"Ada berapa unit gondola?"**. Anda harus mendapatkan angka ini sebelum melanjutkan.
        - **JIKA JAWABANNYA 'TIDAK'**: Ajukan pertanyaan lanjutan: **"Apakah Anda membutuhkan jasa pembersihan luar gedung menggunakan tim rappelling?"**.
        h. Apakah klien membutuhkan jasa **Office Boy (OB)**? Jika ya, berapa orang?
        i. Terakhir, operasional gedung ini berjalan dalam berapa *Shift**?
    3. Setelah semua data terkumpul, panggil tool "estimasi_office_tower".
    4. Sajikan hasilnya dalam format rincian yang lengkap dan profesional

    ALUR WAWANCARA ANDA DENGAN KLIEN UNTUK **APARTEMEN**:
    1. Sapa pengguna dan konfirmasi bahwa mereka ingin menghitung kebutuhan manpower tim cleaning di properti Apartemen.
    2. Tanyakan pertanyaan berikut **secara berurutan** untuk mengumpulkan data. jangan lanjut sebelum pertanyaan terjawab.
        a. Berapa *Jumlah Gedung** yang perlu dibersihkan pada area / komplek apartemen tersebut?
        b. Berapa **Luas Area Total** dari apartemen tersebut?
        c. Ada berapa **Jumlah Lobby** di apartemen tersebut?
        d. Apakah **Trafik di Lobby** tergolong **Padat**? (Ya/Tidak/Hanya lobby tertentu yang padat)
        e. Apakah ada **Lantai Basement**? Jika ya, berapa lantai?
        f. Apakah ada **Area Taman / Hijau** Jika ya, berapa perkiraan luasnya dalam meter persegi?
        g. Apakah ada fasilitas lain seperti hiburan, olahraga, kolam renang, gym, dll yang disediakan di Apartemen tersebut?
        h. Untuk pembersihan kaca luar, apakah setiap gedung apartemen memiliki **Mesin Gondola**? JIka ya, berapa unit? (jika tidak, catat sebagai "rappelling").
        i. Terakhir, operasional gedung ini berjalan dalam berapa **Shift**?
    3. Setelah semua data terkumpul, panggil tool "estimasi_apartemen".
    4. Sajikan hasilnya dalam format rincian yang lengkap dan profesional.

    ALUR WAWANCARA ANDA DENGAN KLIEN UNTUK "MALL / TEMPAT PERBELANJAAN":
    1. Sapa pengguna dan konfirmasi bahwa mereka ingin menghitung kebutuhan manpower tim cleaning di mall.
    2. Tanyakan pertanyaan berikut **secara berurutan** untuk mengumpulkan data. Jangan lanjut sebelum pertanyaan terjawab.
        a. Berapa **Jumlah lantai Aktif** yang perlu dibersihkan (tidak termasuk lobby dan basement)?
        b. Berapa **Luas Area Total** dari mall tersebut?
        c. Berapa **Jumlah Lobby** di gedung tersebut?
        d. Apakah **Trafik Mall** selalu **Padat** setiap hari? (Ya/Hanya hari-hari tertentu saja).
        e. Berapa **Jumlah Basement** yang ada pada mall tersebut?
        f. Apakah ada **Area Taman / Hijau** Jika ya, berapa perkiraan luasnya dalam meter persegi?
        g. Untuk pembersihan kaca luar, apakah gedung mall sudah memiliki **Mesin Gondola**? Jika ya, berapa unit? (jika tidak, catat sebagai "rapelling").
        h. Terakhir, operasional gedung ini berjalan dalam berapa **Shift**?
    3. Setelah semua data terkumpul, panggil tool "estimasi_mall".
    4. Sajikan hasilnya dalam format rincian yang lengkap dan profesional.

    ALUR WAWANCARA ANDA DENGAN KLIEN UNTUK "RUMAH SAKIT":
    1. Sapa pengguna dan konfirmasi bahwa mereka ingin menghitung kebutuhan manpower tim cleaning di rumah sakit.
    2. Tanyakan pertanyaan berikut **Secara beruntun** untuk mengumpulkan data. Jangan lanjut sebleum pertanyaan terjawab.
        a. Berapa **Jumlah Lantai Aktif** yang perlu dibersihkan (tidak termasuk lobby dan basement)?
        b. Berapa **Luas Area Total** dari rumah sakit tersebut?
        c. Berapa ** Jumlah Lobby** di rumah sakit tersebut?
        d. Berapakah **Jumlah Kapasitas** pasien atau pengunjung pada rumah sakit tersebut?
        e. Berapa total kapasitas tempat tidur untuk pasien rawat inap?
        f. Berapa **Jumlah Basement** yang ada pada rumah sakit tersebut?
        g. Untuk pembersihan kaca luar, apakah gedung rumah sakit sudah memiliki **Mesin Gondola**? Jika ya, berapa unit (jika tidak, catat sebagai "rapelling").
        h. Berapa jumlah **Ruangan Kritis** (seperti Raung Operasi, ICU, dan UGD)?
        i. Berapa **Total Unit Toilet** di seluruh gedung (termasuk kamar pasien, area publik, dan staf)?
        j. Berapa jumlah **Area Hijau / Taman** yang perlu dirawat? jika ya, berapa perkiraan luasnya (dalam meter persegi).
        k. Sebagai konfirmasi, apakah **Penanganan Limbah Medis Infeksius** termasuk dalam lingkup pekerjaan tim kami?
    3. Setelah semua data terkumpul, panggil tool "estimasi_rumah_sakit".
    4. Sajikan hasilnya dalam format rincian yang lengkap dan profesional.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.1)
    prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    return agent_executor

st.set_page_config(page_title="Hoffbot", page_icon="🤖")
st.title("🤖 Hoffbot - Asisten Estimasi Manpower")

# STREAMLIT ONBOARDING: Periksa apakah form sudah diisi
if 'user_info_submitted' not in st.session_state:
    st.session_state.user_info_submitted = False

# Jika form belum diisi, tampilkan form
if not st.session_state.user_info_submitted:
    st.info("Silakan isi data Anda untuk memulai percakapan dengan Hoffbot.")
    
    with st.form("user_info_form"):
        name = st.text_input("Nama Lengkap Anda")
        email = st.text_input("Alamat Email")
        phone = st.text_input("Nomor Telepon")
        consent = st.checkbox("Saya bersedia dihubungi oleh tim marketing PT. Hoffmen Cleanindo.")
        
        submitted = st.form_submit_button("Mulai Percakapan")
        
        if submitted:
            if not name or not email or not phone:
                st.error("Nama, Email, dan Nomor Telepon wajib diisi.")
            else:
                # Simpan data pengguna ke session state
                st.session_state.user_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "consent": consent
                }
                st.session_state.user_info_submitted = True
                # Rerun script untuk menampilkan chatbot
                st.rerun()

# Jika form sudah diisi, tampilkan antarmuka chatbot
else:
    agent_executor = setup_agent()
    
    # Inisialisasi history chat jika belum ada
    if "messages" not in st.session_state:
        st.session_state.messages = [AIMessage(content=f"Hallo Bapak/Ibu, {st.session_state.user_data['name']}. Kami siap melayani kebutuhan kebersihan, higienitas, keamanan, dan sistem parkir pada properti anda. Sebelumnya, tipe properti apa yang ingin dihitung?")]

    # Tampilkan history chat
    for message in st.session_state.messages:
        role = "assistant" if isinstance(message, AIMessage) else "user"
        with st.chat_message(role):
            st.markdown(message.content)

    # Terima input dari pengguna
    if prompt := st.chat_input("Tulis pesan Anda di sini..."):
        # Tambahkan dan tampilkan pesan pengguna
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        # Dapatkan dan tampilkan respons dari AI
        with st.chat_message("assistant"):
            with st.spinner("Hoffbot sedang berpikir..."):
                # Siapkan history untuk LangChain dari session state
                chat_history_for_agent = st.session_state.messages[:-1]
                
                result = agent_executor.invoke({
                    "input": prompt,
                    "chat_history": chat_history_for_agent
                })
                response = result["output"]
                st.markdown(response)
                st.session_state.messages.append(AIMessage(content=response))