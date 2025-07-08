import mysql.connector
import re

def limpiar_rut(rut):
    return re.sub(r"[^\dkK]", "", rut).upper()

# Conexión a la base de datos
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Fgn2024$",
    database="clientes_db"
)
cursor = db.cursor(dictionary=True)

# Obtener todos los RUTs
cursor.execute("SELECT id, rut FROM clientes")
clientes = cursor.fetchall()

# Limpiar y actualizar
for cliente in clientes:
    rut_limpio = limpiar_rut(cliente["rut"])
    cursor.execute("UPDATE clientes SET rut = %s WHERE id = %s", (rut_limpio, cliente["id"]))

db.commit()
cursor.close()
db.close()

print("✅ RUTs limpiados correctamente.")
