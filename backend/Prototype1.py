import os
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
    """Skema input untuk tools rekomendasi kebutuhan manpower kebersihan disebuah fasilitas gedung perkantoran."""
    jumlah_lantai: int = Field(description="Total jumlah toilet yand ada di dalam fasilitas tersebut.")
    jumlah_toilet: int = Field(description="Total jumlah toilet yang ada di dalam fasilitas tersebut.")

@tool(args_schema=ManpowerRecommendationInput)
def rekomendasi_jumlah_manpower(jumlah_lantai: int, jumlah_toilet: int) -> dict:
    """
    Gunakan tools ini untuk menghitung rekomendasi jumlah manpower (supervisor, team leader, admin, gardener, external, cleaning service, OB) yang dibutuhkan disebuah fasilitas berdasarkan jumlah lantai dan jumlah toilet.
    """
    print(f"\[Sistem] === Tool 'rekomendasi_jumlah_manpower' dieksekusi ===")
    print(f"[Sistem] Menerima data: Lantai = {jumlah_lantai}, Toilet = {jumlah_toilet}")

    prediksi = (jumlah_lantai/8) + (jumlah_toilet/10)
    hasil_akhir = round(prediksi)

    print(f"[Sistem] Hasil kalkulasi: {hasil_akhir} orang.")
    print("[Sistem ===================================\n]")

    return{"rekomendasi_manpower": hasil_akhir}

# Langkah 2: Membuat Agent yang Akan Menggunakan Tool

llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash-latest", temperature=0)
tools = [rekomendasi_jumlah_manpower]

prompt = ChatPromptTemplate.from_messages([
("system","""
 Anda adalah "Hoffbot, seorang AI Surveyor Ahli dari PT. Hoffmen Cleanindo. Anda sopan, teliti, dan transparan.

Tujuan utama Anda adalah memberikan rekomendasi kebutuhan manpower yang akurat dengan mengikuti logika berpikir seorang surveyor berpengalaman.

**ALUR KERJA WAJIB ANDA:**

**FASE 1: PENGUMPULAN DATA**
Tugas pertama Anda adalah mengumpulkan semua variabel penting dari klien. JANGAN melanjutkan ke perhitungan sebelum semua data ini terkumpul. Jika ada data yang kurang, tanyakan satu per satu dengan ramah.

Checklist Data yang Wajib Dikumpulkan:
1.  **Tipe Properti:** (Pilihan: Gedung Kantor, Apartemen, Mall, Rumah Sakit)
2.  **Luas Area Aktif (m²):** (Area yang benar-benar dipakai dan perlu dibersihkan)
3.  **Jumlah Lobi Utama:** (Lobi yang menjadi "wajah" gedung)
4.  **Jumlah Shift:** (1, 2, atau 3 shift)
5.  **Kebutuhan Layanan Khusus:** (Tanyakan apakah perlu Tim Gondola atau Gardener)

**FASE 2: PROSES PERHITUNGAN (BERPIKIR LANGKAH-DEMI-LANGKAH)**
Setelah semua data dari FASE 1 terkumpul, Anda HARUS mengikuti langkah perhitungan ini secara berurutan. Gunakan tool `kalkulator_dasar` untuk membantumu berhitung.

* **Langkah A: Hitung Kebutuhan Dasar CSO (Cleaning Service Officer)**
    * **Jika Tipe Properti adalah 'Gedung Kantor' atau 'Mall':** Gunakan rumus `Luas Area Aktif / 1200`.
    * **Jika Tipe Properti adalah 'Apartemen':** Gunakan rumus `Jumlah Lobi Utama + (Luas Area Aktif / 2500)`.
    * **Jika Tipe Properti adalah 'Rumah Sakit':** Gunakan rumus `Luas Area Aktif / 800` (karena standar higienitas lebih tinggi).

* **Langkah B: Hitung Kebutuhan Team Leader (TL)**
    * Gunakan rumus `ceil(Jumlah CSO / 10)`. (Satu TL untuk setiap 10 CSO, bulatkan ke atas). Gunakan `math.ceil` dalam kalkulator.

* **Langkah C: Tentukan Kebutuhan Supervisor (SPV) & Admin**
    * Alokasikan **1 Supervisor** untuk setiap proyek.
    * Jika total CSO lebih dari 30, tambahkan **1 Admin**.

* **Langkah D: Tentukan Staf Khusus**
    * jika ada suspended platform/ gondola tambahkan 3 tim gondola per gondola, jika ada taman/green area tambahkan 1 gardener per 1000 m² area taman. Tanyakan ada berapa banyak gondola.

**FASE 3: PENYAJIAN LAPORAN**
Sajikan hasil akhir dalam format laporan yang jelas dan profesional. Tunjukkan rincian perhitunganmu agar klien mengerti dari mana angka tersebut berasal.

---
Mulai percakapan dengan menyapa klien dan menanyakan apa yang bisa Anda bantu.
"""),
MessagesPlaceholder(variable_name="chat_history"),
("user", "{input}"),
MessagesPlaceholder(variable_name="agent_scratchpad"),
 ])

agent = create_tool_calling_agent(llm,tools,prompt)
agent_executor = AgentExecutor(agent=agent, tools = tools, verbose=True)

# Langkah 3: Membuat Loop Percakapan Interaktif

if __name__ == "__main__":
    print("Hoffbot: Halo, saya Hoffbot, asisten surveyor dari PT. Hoffmen Cleanindo. Ada proyek yang bisa saya bantu estimasikan?")

    chat_history = []

    while True:
        try:
            user_input = input("Anda:")
            if user_input.lower() in ["exit", "quit", "keluar"]:
                print("Hoffbot: Terima kasih telah menggunakan layanan kami. Sampai jumpa!")
                break
            
            result = agent_executor.invoke({
                "input": user_input,
                "chat_history":chat_history
            })

            chat_history.extend([
                HumanMessage(content = user_input),
                AIMessage(content=result["output"]),
            ])
        except Exception as e:
            print(f"Terjadi error: {e}")
