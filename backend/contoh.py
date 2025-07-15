import os
import math
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

# Setelah dimuat, AMBIL nilainya ke dalam sebuah variabel Python
google_api_key = os.getenv("GOOGLE_API_KEY")

# Lakukan pengecekan untuk memastikan key-nya ada
if google_api_key:
    print("✅ API Key berhasil dimuat dari file .env.")
    # Set environment variable untuk digunakan oleh library lain seperti LangChain
    os.environ["GOOGLE_API_KEY"] = google_api_key
else:
    print("❌ ERROR: Tidak dapat menemukan GOOGLE_API_KEY di dalam file .env.")

# Langkah 1: Definisikan Tool untuk Kalkulasi

class ManpowerRecommendationInput(BaseModel):
    tipe_properti: str = Field(description="Tipe properti, harus salah satu dari: 'Gedung Kantor', 'Apartemen', 'Mall', 'Rumah Sakit'.")
    luas_total_area: int = Field(description="Total luas area yang aktif digunakan dalam satuan meter persegi/m².")
    jumlah_lobby: int = Field(description="Jumlah lobi utama di dalam gedung.", default= 1)
    jumlah_lantai: int = Field(description="Jumlah lantai yang ada di dalam gedung.")
    jumlah_kamar_mandi_pria: int = Field(description = "Jumlah kamar mandi pria yang ada di dalam gedung.")
    jumlah_kamar_mandi_wanita: int = Field(description = "Jumlah kamar mandi wanita yang ada di dalam gedung.")
    jumlah_gondola: int = Field(description = "Jumlah gondola yang ada di dalam gedung.", default=0)
    luas_area_hijau: int = Field(desciption = "Total luas area taman/hijau dalam meter persegi/m²")
    kapasitas_pengunjung: [int] = Field(None, description = "Estimasi kapasitas pengunjungharian. Wajib untuk Mall")
    jumlah_area_publik_apartemen: [int] = Field(None, description = "Jumlah lantai dengan fasilitas umum (lobi, kolam renang, gym). WAJIB untuk Apartemen.")

@tool(args_schema=ManpowerRecommendationInput)
def rekomendasi_jumlah_manpower(**kwargs) -> dict:
    """
    Gunakan tools ini untuk menghitung rekomendasi jumlah manpower (supervisor, team leader, admin, gardener, cleaning service, OB) yang dibutuhkan disebuah fasilitas.
    """
    print(f"\[Sistem] === Tool 'rekomendasi_jumlah_manpower' dieksekusi ===")

    tipe_properti = kwargs.get("tipe_properti")
    jumlah_cso = 0
    catatan_tambahan = []

    if tipe_properti in ["Gedung Kantor"]:
        jumlah_lantai = kwargs.get("jumlah_lantai") 
        if not jumlah_lantai: return {"error": "Untuk Office Tower, jumlah lantai wajib diisi."}
        jumlah_cso = math.ceil(jumlah_lantai /8) *2

    elif tipe_properti == "mall":
        luas_total_area = kwargs.get("luas_total_area")
        kapasitas = kwargs.get("kapasitas_pengunjung")
        if not luas_total_area or not kapasitas: return {"error":"Untuk Mall, luas area dan kapasitas pengunjung wajib diisi."}
        # Aturan dummy: 1 CSO per 1500 m2 + tambahan untuk toilet berdasarkan kapasitas
        cso_area = math.ceil(luas_total_area/1500)
        cso_toilet = 0
        if kapasitas <=1000:
            cso_toilet = 4 # 2 couple
        else:
            cso_toilet = 8 # 4 couple
        total_cso = cso_area + cso_toilet

    elif tipe_properti == "Apartemen":
        luas_total_area = kwargs.get("luas_total_area")
        jumlah_area_publik_apartemen = kwargs.get("jumlah_area_publik_apartemen")
        if not luas_total_area or not jumlah_area_publik_apartemen: return{"error": "Untuk Apartemen, luas area dan jumlah lantai publik wajib diisi."}
        # Aturan dummy: 1 CSP per 2500m2 + 1 couple per lantai publik
        cso_area = math.ceil(luas_total_area/2500)
        cso_toilet_umum = jumlah_area_publik_apartemen * 2
        total_cso = cso_area + cso_toilet_umum

    elif tipe_properti == "Rumah Sakit":
        luas_total_area = kwargs.get("luas_total_area")
        if not luas_total_area: return {"error": "Untuk Rumah Sakit, luas area wajib diisi"}
        # Aturan dummy: 1 CSO per 500m2 karena standar higineis tinggi
        total_cso = math.ceil(luas_total_area/500)
    
    else:
        return {"error": f"Tipe properti '{tipe_properti}'' tidak dikenal."}
               
    # Hitung Supervisi TL & SPV)
    total_tl = math.ceil(total_cso/10)
    total_spv = 1

    # Perhitungan gardener
    luas_area_hijau = kwargs.get("luas_area_hijau", 0)
    jumlah_gardener = 0
    if luas_area_hijau > 0:
        ratio_gardener = 4500 #Default
        if tipe_properti == "Rumah Sakit": ratio_gardener = 2500
        elif tipe_properti == "Mall": ratio_gardener = 3250
        elif tipe_properti == "Office Tower": ratio_gardener = 4000
        jumlah_gardener = math.ceil(luas_area_hijau/ratio_gardener)

    # Perhitungan Gondola
    jumlah_unit_gondola = kwargs.get("jumlah_gondola", 0)
    jumlah_operator_gondola = jumlah_unit_gondola * 3

    # Hitung subtotal staf operasional terlebih dahulu
    sub_total_operasional = total_cso + total_tl + total_spv + jumlah_gardener + jumlah_operator_gondola

    # Perhitungan Admin
    jumlah_admin = 0
    if sub_total_operasional > 30:
        jumlah_admin = 1
        catatan_tambahan.append("1 Admin ditambahkan karena total tim operasional lebih dari 30 orang.")

    # Kalkulasi Total Keseluruhan
    total_manpower = sub_total_operasional + jumlah_admin

    hasil = {
        "estimasi_total_manpower": total_manpower,
        "rincian":{
            "CSO (Cleaning Service Officer)": total_cso,
            "Supervisor": total_spv,
            "Team Leader": total_tl,
            "Admin": jumlah_admin,
            "Gardener": jumlah_gardener,
            "Operator Gondola": jumlah_operator_gondola,
        },
        "catatan_tambahan": catatan_tambahan
    }
    print(f"[Sistem] Hasil kalkulasi:{hasil}")
    print("[Sistem]=================================================\n")
    return hasil

# Langkah 2: Membuat Agent yang Akan Menggunakan Tool

SYSTEM_PROMPT= """
 Anda adalah "Hoffbot", AI asisten yang cerdas dan ramah dari PT. Hoffmen Cleanindo.
 Tujuan utama Anda adalah membatu klien mendapatkan estimasi kebutuhan manpower.
 
ALUR KERJA:
1.  Sapa pengguna, lalu selalu tanyakan **Tipe Properti** terlebih dahulu.
2.  Berdasarkan Tipe Properti, tanyakan parameter utamanya (Jumlah Lantai untuk Office Tower, atau Luas Area untuk yang lain, serta parameter spesifik lainnya seperti kapasitas atau area publik).
3.  Setelah itu, tanyakan secara proaktif:
    - "Apakah ada area taman/hijau yang perlu dirawat? Jika ya, berapa perkiraan luasnya dalam meter persegi?"
    - "Apakah gedung dilengkapi dengan unit gondola? Jika ya, ada berapa unit?"
4.  Kumpulkan semua informasi yang relevan, lalu panggil tool `estimasi_manpower_lengkap`.
5.  Sajikan hasilnya dalam format rincian yang profesional, termasuk jika ada catatan tambahan dari hasil perhitungan.
"""

# Langkah 3: Membuat Loop Percakapan Interaktif

llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash-latest", temperature=0)
tools = [rekomendasi_jumlah_manpower]
prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), MessagesPlaceholder(variable_name = "chat_history"), ("user", "{input}"), MessagesPlaceholder(variable_name="agent_scratchpad")])
agent = create_tool_calling_agent(llm,tools,prompt)
agent_executor = AgentExecutor(agent=agent, tools = tools, verbose=True)



if __name__ == "__main__":
    print("Hoffbot: Halo, saya Hoffbot, asistem AI dari PT. Hoffmen Cleanindo. Saya akan membantu Anda menghitung kebutuhan manpower untuk timm cleaning secara lengkap.")
    chat_history = []
    while True:
        user_input = input("Anda:")
        if user_input.lower() in ["exit", "quit", "keluar"]:
            break
        result = agent_executor.invoke({"input": user_input, "chat_history": chat_history})
        chat_history.extend([HumanMessage(content = user_input), AIMessage(content=result["output"])])
