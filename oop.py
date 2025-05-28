import uuid
import random

# Nama : [Isi Nama Anda]
# NIM : [Isi NIM Anda]
# Kelas : [Isi Kelas Anda]

# Class dasar MakhlukHidup
class MakhlukHidup:
    # Variabel statis untuk menghitung total makhluk
    total_makhluk = 0

    def _init_(self, spesies):
        self.spesies = spesies  # Atribut spesies
        self.usia = 0           # Atribut usia, dimulai dari 0
        self.dna = self._generate_dna() # Atribut dna
        MakhlukHidup.total_makhluk += 1 # Tambah hitungan total makhluk

    # Metode untuk menghasilkan DNA
    def _generate_dna(self):
        return str(uuid.uuid4())

    # Metode untuk mendapatkan spesies
    def get_spesies(self):
        return self.spesies

    # Metode untuk mendapatkan usia
    def get_usia(self):
        return self.usia

    # Metode untuk mendapatkan DNA
    def get_dna(self):
        return self.dna

    # Metode untuk menua (akan di-override oleh Manusia)
    def menua(self):
        pass # Implementasi dasar, akan di-override

    # Metode statis untuk mendapatkan total makhluk
    @staticmethod
    def get_total_makhluk():
        return MakhlukHidup.total_makhluk

# Class Manusia, mewarisi dari MakhlukHidup
class Manusia(MakhlukHidup):
    def _init_(self, nama):
        super()._init_("Homo Sapiens") # Manusia adalah spesies "Homo Sapiens"
        self.nama = nama # Atribut nama

    # Implementasi metode menua untuk Manusia
    def menua(self):
        if self.usia < 80: # Usia maksimal 80 tahun
            self.usia += 1

    # Metode untuk belajar
    def belajar(self):
        print(f"{self.nama} sedang belajar.")

    # Metode untuk bekerja
    def bekerja(self):
        print(f"{self.nama} sedang bekerja.")

    # Metode untuk mencetak informasi manusia
    def cetak_info(self):
        print(f"Nama: {self.nama}, Spesies: {self.get_spesies()}, Usia: {self.get_usia()}, DNA: {self.get_dna()}")


# --- Pengujian ---

# Objek Manusia pertama
manusia_pertama = Manusia("Budi")

print("--- Informasi Manusia Pertama ---")
manusia_pertama.cetak_info()

print("\n--- Manusia Pertama Menua ---")
for _ in range(3):
    manusia_pertama.menua()
print(f"Usia {manusia_pertama.nama} sekarang: {manusia_pertama.get_usia()}")

print("\n--- Aktivitas Manusia Pertama ---")
manusia_pertama.belajar()
manusia_pertama.bekerja()

# Buat 1000 objek Manusia acak
daftar_manusia = []
for i in range(1000):
    m = Manusia(f"Orang_{i+1}")
    usia_random = random.randint(0, 80)
    for _ in range(usia_random):
        m.menua()
    daftar_manusia.append(m)

# Inisialisasi kategori usia
balita = 0      # usia <= 5
anak = 0        # usia <= 12
remaja = 0      # usia <= 17
dewasa = 0      # usia <= 59
lansia = 0      # usia > 59

# Hitung jumlah objek manusia berdasarkan kategori usia
for manusia in daftar_manusia:
    usia = manusia.get_usia()
    if usia <= 5:
        balita += 1
    elif usia <= 12:
        anak += 1
    elif usia <= 17:
        remaja += 1
    elif usia <= 59:
        dewasa += 1
    else:
        lansia += 1

print("\n--- Statistik 1000 Objek Manusia ---")
print(f"Jumlah object manusia berusia balita: {balita}")
print(f"Jumlah object manusia berusia anak-anak: {anak}")
print(f"Jumlah object manusia berusia remaja: {remaja}")
print(f"Jumlah object manusia berusia dewasa: {dewasa}")
print(f"Jumlah object manusia berusia lansia: {lansia}")

print(f"Jumlah total makhluk yang tercatat: {MakhlukHidup.get_total_makhluk()}")