from flask import Flask, render_template, request, session, redirect, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message  # ← IMPORTACIÓN CORRECTA
from itsdangerous import URLSafeTimedSerializer
from flask import flash
import re
from datetime import datetime
import logging

app = Flask(__name__)  # ← CREA 'app' ANTES DE USAR 'app.config'

app.secret_key = "clave_secreta_segura"
s = URLSafeTimedSerializer(app.secret_key)

# Conexión a la base de datos
from mysql.connector import connect
global db
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Fgn2024$",  # Cambia si tienes contraseña
    database="clientes_db"
)
#cursor = get_cursor()

def get_cursor(dictionary=False):
    global db
    try:
        db.ping(reconnect=True)
    except:
        db = connect(
            host="localhost",
            user="root",
            password="Fgn2024$",
            database="clientes_db"
        )
    return db.cursor(dictionary=dictionary)










# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'francopyme2022@gmail.com'        # ✅ tu correo
app.config['MAIL_PASSWORD'] = 'kxzr tffy wszu lcrf'  # ⚠️ clave de aplicación (no la normal)


mail = Mail(app)



@app.route("/admin/mensajes")
def ver_mensajes():
    if not session.get("admin"):
        flash("Acceso restringido.")
        return redirect("/")

    db.ping(reconnect=True)  # <-- Asegura que la conexión está viva
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM mensajes_contacto ORDER BY fecha DESC")
    mensajes = cursor.fetchall()
    return render_template("admin_mensajes.html", mensajes=mensajes)


@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.route('/')
def inicio():
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos LIMIT 10")
    productos = cursor.fetchall()
    return render_template("inicio.html", productos=productos)

@app.route("/bienvenido")
def bienvenido():
    if "cliente" in session:
        return render_template("bienvenido.html", nombre=session["cliente"])
    else:
        return redirect("/")


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        rut = request.form["rut"]
        cursor = cursor = get_cursor(dictionary=True)
        cursor.execute("SELECT * FROM clientes WHERE rut = %s", (rut,))
        user = cursor.fetchone()

        if user:
            token = s.dumps(user["rut"], salt='recuperar-clave')
            enlace = f"http://localhost:5000/reset/{token}"

            msg = Message("Recuperación de contraseña",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[user["direccion"]])
            msg.body = f"Hola {user['nombre']},\n\nHaz clic aquí para restablecer tu contraseña:\n{enlace}\n\nEste enlace es válido por 15 minutos."
            mail.send(msg)
            return "📬 Se envió un enlace de recuperación a tu correo"
        else:
            return "❌ RUT no encontrado"

    return render_template("recuperar.html")

@app.route("/producto/<int:producto_id>")
def ver_producto(producto_id):
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cursor.fetchone()
    
    if not producto:
        return "Producto no encontrado", 404

    return render_template("producto.html", producto=producto)


@app.route("/agregar-carrito/<int:id>", methods=["POST"])
def agregar_al_carrito(id):
    cantidad = int(request.form.get("cantidad", 1))

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()

    if not producto:
        flash("Producto no encontrado.")
        return redirect("/productos")

    item = {
        "id": producto["id"],
        "nombre": producto["nombre"],
        "precio": producto["precio"],
        "imagen": producto["imagen"],
        "cantidad": cantidad
    }

    carrito = session.get("carrito", [])
    # Si ya está en el carrito, suma cantidad
    for p in carrito:
        if p["id"] == item["id"]:
            p["cantidad"] += cantidad
            break
    else:
        carrito.append(item)

    session["carrito"] = carrito
    flash("🛒 Producto agregado al carrito.")
    return redirect("/carrito")

@app.route('/nosotros')
def nosotros():
    return render_template('nosotros.html')


#@app.before_request
#def contar_mensajes():
#    if session.get("admin"):
#        cursor = get_cursor()
#        cursor.execute("SELECT COUNT(*) FROM mensajes_contacto WHERE leido = 0")
#        cantidad = cursor.fetchone()[0]
#        session["nuevos_mensajes"] = cantidad > 0





#from flask import make_response
#from weasyprint import HTML




@app.route("/admin/productos/<int:id>/editar", methods=["GET", "POST"])
def editar_producto(id):
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()

    cursor.execute("SELECT * FROM categorias")
    categorias = cursor.fetchall()

    if request.method == "POST":
        nombre = request.form["nombre"]
        descripcion = request.form["descripcion"]
        precio = request.form["precio"]
        imagen = request.form["imagen"]
        id_categoria = request.form["id_categoria"]

        sql = """
            UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, imagen=%s, id_categoria=%s
            WHERE id=%s
        """
        val = (nombre, descripcion, precio, imagen, id_categoria, id)
        cursor.execute(sql, val)
        db.commit()
        flash("✅ Producto actualizado.")
        return redirect("/admin/productos")

    return render_template("admin_producto_form.html", producto=producto, categorias=categorias)



@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        rut = s.loads(token, salt='recuperar-clave', max_age=900)  # 15 minutos
    except:
        return "❌ Enlace inválido o expirado"

    if request.method == "POST":
        nueva = request.form["password"]
        hash_pw = generate_password_hash(nueva)

        cursor = get_cursor()
        sql = "UPDATE clientes SET password = %s WHERE rut = %s"
        cursor.execute(sql, (hash_pw, rut))
        db.commit()

        return "✅ Tu contraseña ha sido actualizada exitosamente."

    return render_template("reset_password.html", token=token)

@app.route("/admin/producto", methods=["GET", "POST"])
def crear_producto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        descripcion = request.form["descripcion"]
        precio = int(request.form["precio"])
        imagen = request.form["imagen"]  # solo nombre del archivo
        stock = int(request.form["stock"])

        cursor = get_cursor()
        sql = "INSERT INTO productos (nombre, descripcion, precio, imagen, stock) VALUES (%s, %s, %s, %s, %s)"
        val = (nombre, descripcion, precio, imagen, stock)
        cursor.execute(sql, val)
        db.commit()

        return "✅ Producto creado correctamente"
    
    return render_template("crear_producto.html")


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    return render_template("admin_dashboard.html")

@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias")
    categorias = cursor.fetchall()

    if request.method == "POST":
        nombre = request.form["nombre"]
        descripcion = request.form["descripcion"]
        precio = request.form["precio"]
        imagen = request.form["imagen"]
        id_categoria = request.form["id_categoria"]

        try:
            sql = "INSERT INTO productos (nombre, descripcion, precio, imagen, id_categoria) VALUES (%s, %s, %s, %s, %s)"
            val = (nombre, descripcion, precio, imagen, id_categoria)
            cursor = get_cursor()
            cursor.execute(sql, val)
            db.commit()
            flash("✅ Producto agregado exitosamente.")
            return redirect("/admin/productos")
        except Exception as e:
            print("❌ Error al agregar producto:", e)
            flash("❌ No se pudo agregar el producto.")

    return render_template("admin_producto_form.html", categorias=categorias)


@app.route("/login", methods=["POST"])
def procesar_login():
    rut = request.form["rut"]
    password = request.form["password"]

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes WHERE rut = %s", (rut,))
    user = cursor.fetchone()

    if user and check_password_hash(user["password"], password):
        session["cliente"] = user["nombre"]
        session["rut"] = user["rut"]

    # ✅ Activar sesión de admin si corresponde
        if user.get("is_admin") == 1:
             session["admin"] = True
        else:
             session.pop("admin", None)

        return redirect("/")

    else:
        return render_template("inicio.html", error="RUT o contraseña incorrectos")


@app.route("/admin/productos")
def admin_productos():
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("""
        SELECT productos.*, categorias.nombre AS categoria
        FROM productos
        LEFT JOIN categorias ON productos.id_categoria = categorias.id
        ORDER BY productos.id DESC
    """)
    productos = cursor.fetchall()
    return render_template("admin_productos.html", productos=productos)



@app.route('/eliminar/<id>')
def eliminar_producto(id):
    carrito = session.get("carrito", [])
    carrito = [item for item in carrito if item["id"] != id]
    session["carrito"] = carrito
    return redirect("/carrito")

@app.route("/carrito/vaciar")
def vaciar_carrito():
    session["carrito"] = []
    return redirect("/carrito")

@app.route("/pago")
def pago():
    carrito = session.get("carrito", [])
    if not carrito:
        return redirect("/carrito")

    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    cliente = session.get("cliente", "Invitado")  # si no hay login

    # 1. Crear orden
    cursor = get_cursor()
    sql_orden = "INSERT INTO ordenes (cliente, total) VALUES (%s, %s)"
    cursor.execute(sql_orden, (cliente, total))
    orden_id = cursor.lastrowid  # ← obtener ID autoincrementado

    # 2. Insertar detalle
    for item in carrito:
        sql_detalle = """
        INSERT INTO orden_detalle (orden_id, producto_id, nombre_producto, cantidad, precio_unitario)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_detalle, (
            orden_id,
            item["id"],
            item["nombre"],
            item["cantidad"],
            item["precio"]
        ))

    db.commit()
    session["carrito"] = []  # Limpiar carrito

    return render_template("pago.html", total=total, orden_id=orden_id)


@app.context_processor
def notificaciones_admin():
    cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) FROM mensajes_contacto WHERE leido = FALSE")
    total_nuevos = cursor.fetchone()[0]
    return {"mensajes_nuevos": total_nuevos}




@app.route("/admin/productos/<int:id>/eliminar", methods=["POST"])
def eliminar_producto_admin(id):
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    cursor = get_cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    db.commit()
    flash("🗑 Producto eliminado.")
    return redirect("/admin/productos")

@app.route("/productos/<int:id>")
def producto_detalle(id):
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, c.nombre AS categoria, c.especificaciones_pdf
        FROM productos p
        JOIN categorias c ON p.id_categoria = c.id
        WHERE p.id = %s
    """, (id,))
    producto = cursor.fetchone()

    if not producto:
        flash("Producto no encontrado.")
        return redirect("/productos")

    # 🔁 Productos relacionados
    cursor.execute("""
        SELECT * FROM productos
        WHERE id_categoria = %s AND id != %s
        ORDER BY RAND() LIMIT 4
    """, (producto["id_categoria"], id))
    relacionados = cursor.fetchall()

    return render_template("producto_detalle.html", producto=producto, relacionados=relacionados)

@app.route("/mis-compras")
def mis_compras():
    if "cliente" not in session:
        return redirect("/")  # si no está logueado

    cliente = session["cliente"]
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM ordenes WHERE cliente = %s ORDER BY fecha DESC", (cliente,))
    ordenes = cursor.fetchall()
    return render_template("mis_compras.html", ordenes=ordenes)

@app.route("/mis-compras/<int:orden_id>")
def detalle_compra(orden_id):
    if "cliente" not in session:
        return redirect("/")

    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM ordenes WHERE id = %s", (orden_id,))
    orden = cursor.fetchone()

    cursor.execute("SELECT * FROM orden_detalle WHERE orden_id = %s", (orden_id,))
    detalles = cursor.fetchall()

    return render_template("detalle_compra.html", orden=orden, detalles=detalles)


@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "cliente" not in session:
        return redirect("/")

    rut = session.get("rut")  # rut debe haberse guardado en login
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes WHERE rut = %s", (rut,))
    usuario = cursor.fetchone()

    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion = request.form["direccion"]
        telefono = request.form["telefono"]
        nueva_pass = request.form["password"]

        if nueva_pass:
            password_hash = generate_password_hash(nueva_pass)
            cursor.execute("UPDATE clientes SET nombre=%s, direccion=%s, telefono=%s, password=%s WHERE rut=%s",
                           (nombre, direccion, telefono, password_hash, rut))
        else:
            cursor.execute("UPDATE clientes SET nombre=%s, direccion=%s, telefono=%s WHERE rut=%s",
                           (nombre, direccion, telefono, rut))

        db.commit()
        flash("✅ Datos actualizados con éxito")
        return redirect("/perfil")

    return render_template("perfil.html", usuario=usuario)

@app.route("/admin/categorias/editar/<int:id>", methods=["GET", "POST"])
def editar_categoria(id):
    cursor = cursor = get_cursor(dictionary=True)

    if request.method == "POST":
        nombre = request.form["nombre"]
        archivo = request.files.get("pdf")
        pdf_nombre = ""

        # Buscar el PDF actual
        cursor.execute("SELECT especificaciones_pdf FROM categorias WHERE id = %s", (id,))
        actual = cursor.fetchone()
        pdf_actual = actual["especificaciones_pdf"] if actual else ""

        if archivo and archivo.filename.endswith(".pdf"):
            from werkzeug.utils import secure_filename
            import os
            pdf_nombre = secure_filename(archivo.filename)
            archivo.save(os.path.join("static/pdf", pdf_nombre))
        else:
            pdf_nombre = pdf_actual

        cursor.execute("UPDATE categorias SET nombre=%s, especificaciones_pdf=%s WHERE id=%s",
                       (nombre, pdf_nombre, id))
        db.commit()
        return redirect("/admin/categorias")

    # GET: mostrar formulario
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (id,))
    categoria = cursor.fetchone()
    if not categoria:
        return "Categoría no encontrada", 404

    return render_template("admin_categoria_editar.html", categoria=categoria)


@app.route("/productos")
def productos():
    categoria_id = request.args.get("categoria", type=int)
    buscar = request.args.get("buscar", default="")
    orden = request.args.get("orden", default="")

    cursor = cursor = get_cursor(dictionary=True)

    sql = """
        SELECT p.*, c.nombre AS categoria_nombre
        FROM productos p
        JOIN categorias c ON p.id_categoria = c.id
        WHERE 1=1
    """
    params = []

    if categoria_id:
        sql += " AND c.id = %s"
        params.append(categoria_id)

    if buscar:
        sql += " AND p.nombre LIKE %s"
        params.append(f"%{buscar}%")

    # Ordenamientos
    if orden == "nombre_asc":
        sql += " ORDER BY p.nombre ASC"
    elif orden == "nombre_desc":
        sql += " ORDER BY p.nombre DESC"
    elif orden == "nuevo":
        sql += " ORDER BY p.id DESC"
    elif orden == "viejo":
        sql += " ORDER BY p.id ASC"
    else:
        sql += " ORDER BY p.nombre ASC"

    cursor.execute(sql, tuple(params))
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM categorias")
    categorias = cursor.fetchall()

    return render_template("productos.html", productos=productos, categorias=categorias,
                           seleccionada=categoria_id, buscar=buscar, orden=orden)


@app.route("/productos/ajax")
def productos_ajax():
     categoria_id = request.args.get("categoria", type=int)
     buscar = request.args.get("buscar", default="")
     orden = request.args.get("orden", default="")

     cursor = cursor = get_cursor(dictionary=True)
     sql = """
        SELECT p.*, c.nombre AS categoria_nombre
        FROM productos p
        JOIN categorias c ON p.id_categoria = c.id
        WHERE 1=1
     """
     params = []

     if categoria_id:
        sql += " AND c.id = %s"
        params.append(categoria_id)

     if buscar:
        sql += " AND p.nombre LIKE %s"
        params.append(f"%{buscar}%")

     # Agregar ordenamiento
     if orden == "nombre_asc":
        sql += " ORDER BY p.nombre ASC"
     elif orden == "nombre_desc":
        sql += " ORDER BY p.nombre DESC"
     elif orden == "nuevo":
        sql += " ORDER BY p.id DESC"
     elif orden == "viejo":
        sql += " ORDER BY p.id ASC"
     else:
        sql += " ORDER BY p.nombre ASC"  # valor por defecto

     cursor.execute(sql, tuple(params))
     productos = cursor.fetchall()

     cursor.execute("SELECT * FROM categorias")
     categorias = cursor.fetchall()

     return render_template("productos.html", productos=productos, categorias=categorias,
                           seleccionada=categoria_id, buscar=buscar, orden=orden)


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        correo = request.form.get("correo")
        mensaje = request.form.get("mensaje")

        try:
            # Guardar mensaje en la base de datos
            cursor = get_cursor()
            sql = "INSERT INTO mensajes_contacto (nombre, correo, mensaje) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nombre, correo, mensaje))
            db.commit()

            # Enviar correo
            try:
                msg = Message(
                    subject=f"Nuevo mensaje de contacto: {nombre}",
                    recipients=["francopyme2022@gmail.com"],
                    body=f"""
📩 Nuevo mensaje recibido:

Nombre: {nombre}
Correo: {correo}

Mensaje:
{mensaje}
"""
                )
                mail.send(msg)
                flash("✅ Tu mensaje fue enviado correctamente.")
            except Exception as e:
                print("⚠️ Error al enviar correo:", e)
                flash("⚠️ Tu mensaje fue guardado, pero no se pudo enviar por correo.")
        except Exception as e:
            print("❌ Error al guardar:", e)
            flash("❌ No se pudo guardar tu mensaje.")

        return redirect("/contacto")

    # Si GET, mostrar formulario
    return render_template("contacto.html")


@app.route("/admin/mensajes/eliminar/<int:id>", methods=["POST"])
def eliminar_mensaje(id):
    if not session.get("admin"):
        flash("Acceso denegado.")
        return redirect("/")

    try:
        cursor = get_cursor()
        cursor.execute("DELETE FROM mensajes_contacto WHERE id = %s", (id,))
        db.commit()
        flash("🗑 Mensaje eliminado correctamente.")
    except Exception as e:
        print("❌ Error al eliminar mensaje:", e)
        flash("❌ No se pudo eliminar el mensaje.")
    
    return redirect("/admin/mensajes")





@app.route("/producto/<int:id>")
def detalle_producto(id):
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    if producto:
        return render_template("detalle_producto.html", producto=producto)
    return "Producto no encontrado", 404
   

@app.route('/carrito')
def ver_carrito():
    carrito = session.get("carrito", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    return render_template("carrito.html", carrito=carrito, total=total)


@app.context_processor
def inyectar_mensajes_no_leidos():
    if session.get("admin"):
        cursor = get_cursor()
        cursor.execute("SELECT COUNT(*) FROM mensajes_contacto")
        total = cursor.fetchone()[0]
        return dict(mensajes_no_leidos=total)
    return dict(mensajes_no_leidos=0)



logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)



#@app.route("/register", methods=["GET", "POST"])
#ef register():
 #   if request.method == "POST":
  #      nombre = request.form["nombre"]
   #     direccion = request.form["direccion"]
    #    telefono = request.form["telefono"]
     #   rut = limpiar_rut(request.form["rut"])

     #   if not validar_rut(rut):
      #      flash("❌ El RUT ingresado no es válido", "error")
       #     return redirect("/register")

 #       cursor = get_cursor()
  #      cursor.execute("SELECT * FROM clientes WHERE rut = %s", (rut,))
   #     if cursor.fetchone():
    #        flash("❌ El RUT ya está registrado", "error")
  #          return redirect("/register")

   #     password = generate_password_hash(request.form["password"])
    #    sql = """
     #       INSERT INTO clientes (nombre, direccion, telefono, rut, password)
      #      VALUES (%s, %s, %s, %s, %s)
       # """
        #val = (nombre, direccion, telefono, rut, password)

        #try:
         #   cursor.execute(sql, val)
          #  db.commit()
           # flash("✅ Cliente registrado exitosamente")
            #return redirect("/")
        #except mysql.connector.Error as err:
         #   flash(f"❌ Error al registrar: {err}", "error")
          #  return redirect("/register")

    #return render_template("registro.html")


import re

def limpiar_rut(rut):
    return re.sub(r"[^\dkK]", "", rut).upper()

def validar_rut(rut_completo):
    rut = limpiar_rut(rut_completo)
    if not rut[:-1].isdigit() or len(rut) < 2:
        return False

    cuerpo = rut[:-1]
    dv_ingresado = rut[-1].upper()

    suma = 0
    multiplicador = 2

    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = suma % 11
    dv_calculado = "0" if resto == 0 else "K" if resto == 1 else str(11 - resto)

    return dv_calculado == dv_ingresado


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion = request.form["direccion"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        rut = limpiar_rut(request.form["rut"])

        if not validar_rut(rut):
            flash("❌ El RUT ingresado no es válido", "error")
            return redirect("/register")

        cursor = get_cursor()
        cursor.execute("SELECT * FROM clientes WHERE rut = %s", (rut,))
        if cursor.fetchone():
            flash("❌ El RUT ya está registrado", "error")
            return redirect("/register")

        password = generate_password_hash(request.form["password"])

        sql = """
            INSERT INTO clientes (nombre, direccion, telefono, rut, password, correo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        val = (nombre, direccion, telefono, rut, password, correo)

        try:
            cursor.execute(sql, val)
            db.commit()
            flash("✅ Cliente registrado exitosamente")
            return redirect("/")
        except mysql.connector.Error as err:
            flash(f"❌ Error al registrar: {err}", "error")
            return redirect("/register")

    return render_template("registro.html")

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors


@app.route("/cotizacion")
def generar_cotizacion():
    from io import BytesIO
    from flask import send_file
    import os

    carrito = session.get("carrito", [])
    if not carrito:
        flash("❌ El carrito está vacío.")
        return redirect("/carrito")

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.lib import colors
  

    cliente = session.get("cliente", "Invitado")
    direccion = session.get("direccion", "")
    telefono = session.get("telefono", "")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logo marca de agua (opcional)
    logo_path = os.path.join("static", "img", "logo.png")
    if os.path.exists(logo_path):
        pdf.saveState()
        pdf.translate(200, 400)
        pdf.rotate(30)
        pdf.setFillAlpha(0.05)
        pdf.drawImage(logo_path, 0, 0, width=200, preserveAspectRatio=True, mask='auto')
        pdf.restoreState()

    # Encabezado
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, 40, height - 100, width=120, preserveAspectRatio=True)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 60, "COTIZACIÓN")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, height - 120, f"Cliente: {cliente}")
    pdf.drawString(40, height - 135, f"Dirección: {direccion}")
    pdf.drawString(40, height - 150, f"Teléfono: {telefono}")
    pdf.drawString(40, height - 165, f"Fecha: {fecha}")

    # Tabla de productos
    y = height - 190
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Producto")
    pdf.drawString(250, y, "Cantidad")
    pdf.drawString(320, y, "Precio")
    pdf.drawString(400, y, "Subtotal")
    y -= 15
    pdf.line(40, y, 500, y)

    total = 0
    pdf.setFont("Helvetica", 10)
    y -= 20
    for item in carrito:
        subtotal = item["cantidad"] * item["precio"]
        pdf.drawString(40, y, item["nombre"][:35])
        pdf.drawString(250, y, str(item["cantidad"]))
        pdf.drawString(320, y, f"${item['precio']:,}")
        pdf.drawString(400, y, f"${subtotal:,}")
        total += subtotal
        y -= 20

        if y < 100:
            pdf.showPage()
            y = height - 50

    # Total
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(320, y - 10, "TOTAL:")
    pdf.drawString(400, y - 10, f"${total:,}")

    # Pie de página con datos empresa
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 40, "ALLTAK CHILE - Independencia 1518, Santiago - contacto@amg-alltak.cl - +56 9 9334 9975")

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="cotizacion.pdf", mimetype="application/pdf")


@app.route("/cotizar")
def cotizar():
    if "cliente" not in session:
        flash("Debes iniciar sesión para generar una cotización.")
        return redirect("/register")

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Tu carrito está vacío.")
        return redirect("/carrito")

    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    cliente = session.get("cliente")

    # Aquí puedes construir una página con resumen o generar un PDF de cotización
    return render_template("cotizacion.html", carrito=carrito, total=total, cliente=cliente)



@app.route("/admin/categorias")
def admin_categorias():
    cursor = cursor = get_cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall()
    return render_template("admin_categorias.html", categorias=categorias)


@app.route("/admin/categorias/agregar", methods=["POST"])
def agregar_categoria():
    nombre = request.form["nombre"]
    archivo = request.files.get("pdf")
    pdf_nombre = ""

    if archivo and archivo.filename.endswith(".pdf"):
        from werkzeug.utils import secure_filename
        import os
        pdf_nombre = secure_filename(archivo.filename)
        ruta = os.path.join("static/pdf", pdf_nombre)
        archivo.save(ruta)

    cursor = get_cursor()
    sql = "INSERT INTO categorias (nombre, especificaciones_pdf) VALUES (%s, %s)"
    cursor.execute(sql, (nombre, pdf_nombre))
    db.commit()
    return redirect("/admin/categorias")



@app.route("/admin/categorias/eliminar/<int:id>")
def eliminar_categoria(id):
    cursor = get_cursor()
    cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
    db.commit()
    return redirect("/admin/categorias")



   #  @app.route("/logout")
   #  def logout():
   # session.clear()
   # flash("✅ Sesión cerrada correctamente")
   #  return redirect("/")


# BLOQUE PRINCIPAL: debe estar fuera de cualquier función, sin indentación

@app.route("/logout")
def logout():
    carrito = session.get("carrito", [])
    session.clear()
    session["carrito"] = carrito
    return redirect("/")

@app.route("/galeria")
def galeria():
    categoria_id = request.args.get("categoria", type=int)
    cursor = db.cursor(dictionary=True)

    # Todas las categorías
    cursor.execute("SELECT * FROM categorias")
    categorias = cursor.fetchall()

    # Productos filtrados (si hay filtro)
    if categoria_id:
        cursor.execute("SELECT nombre, imagen, id_categoria FROM productos WHERE id_categoria = %s", (categoria_id,))
    else:
        cursor.execute("SELECT nombre, imagen, id_categoria FROM productos")
    productos = cursor.fetchall()

    return render_template("galeria.html", productos=productos, categorias=categorias, seleccionada=categoria_id)



@app.template_filter('formatear_precio')
def formatear_precio(valor):
    return f"${int(valor):,}".replace(",", ".")  # 1000000 → $1.000.000


@app.route("/catalogo")
def catalogo():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    return render_template("catalogo.html", productos=productos)



@app.route("/catalogo")
def catalogo_digital():
    buscar = request.args.get("buscar", "").strip()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall()

    catalogo = []
    for cat in categorias:
        if buscar:
            cursor.execute("""
                SELECT * FROM productos
                WHERE id_categoria = %s AND nombre LIKE %s
            """, (cat["id"], f"%{buscar}%"))
        else:
            cursor.execute("SELECT * FROM productos WHERE id_categoria = %s", (cat["id"],))
        productos = cursor.fetchall()
        if productos:
            catalogo.append({
                "nombre": cat["nombre"],
                "productos": productos
            })

    return render_template("catalogo.html", catalogo=catalogo, buscar=buscar)


@app.route("/catalogo/pdf")
def catalogo_pdf():
    from io import BytesIO
    from flask import send_file
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall()

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Catálogo de Productos - ALLTAK Chile")
    y -= 40

    for cat in categorias:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, cat["nombre"])
        y -= 20

        cursor.execute("SELECT * FROM productos WHERE id_categoria = %s", (cat["id"],))
        productos = cursor.fetchall()

        pdf.setFont("Helvetica", 10)
        for p in productos:
            texto = f"- {p['nombre']} - ${p['precio']:,}".replace(",", ".")
            pdf.drawString(60, y, texto)
            y -= 15
            if y < 50:
                pdf.showPage()
                y = height - 50

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=False, download_name="catalogo.pdf", mimetype="application/pdf")

@app.route("/catalogo")
def catalogo_galeria():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall()

    galeria = []
    for cat in categorias:
        cursor.execute("SELECT * FROM productos WHERE id_categoria = %s", (cat["id"],))
        productos = cursor.fetchall()
        for p in productos:
            galeria.append({
                "imagen": p["imagen"],
                "nombre": p["nombre"],
                "categoria": cat["nombre"]
            })

    return render_template("catalogo_galeria.html", galeria=galeria, auto_open=True)







if __name__ == '__main__':
    app.run(debug=True)

