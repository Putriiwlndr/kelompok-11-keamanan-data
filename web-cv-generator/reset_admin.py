import hashlib
import sqlite3


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

username = "admin"
new_password = hash_pw("admin123")  # Ganti ke password baru yang diinginkan

conn = sqlite3.connect("cv.db")
cur = conn.cursor()

cur.execute("UPDATE user SET password = ? WHERE username = ?", (new_password, username))
conn.commit()
conn.close()

print("✅ Password admin berhasil diubah ke 'admin123'")
