import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_URL = "http://localhost:8070"
DB_NAME = "GestionCalidad"

API_CLIENTES = f"{BASE_URL}/api/clientes?db={DB_NAME}"
API_PRODUCTOS = f"{BASE_URL}/api/productos?db={DB_NAME}"
API_VENTAS = f"{BASE_URL}/api/ventas?db={DB_NAME}"

HILOS = 20


# ============================================================
# FUNCIÓN GENERAL PARA ENVIAR DATOS
# ============================================================

def enviar(url, datos):

    try:

        respuesta = requests.post(
            url,
            json=datos,
            timeout=30
        )

        if not respuesta.ok:
            return {
                "success": False,
                "status_code": respuesta.status_code,
                "error": respuesta.text[:500],
            }

        try:
            return respuesta.json()
        except ValueError:
            return {
                "success": False,
                "status_code": respuesta.status_code,
                "error": "La API no devolvió JSON",
                "response": respuesta.text[:500],
            }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# GENERAR 100 CLIENTES
# ============================================================

def generar_clientes():

    nombres = ["Carlos", "Ana", "Luis", "Maria", "Juan", "Elena", "Pedro", "Sofia", "Diego", "Lucia"]
    apellidos = ["Perez", "Gomez", "Lopez", "Rodriguez", "Morales", "Castillo", "Sanchez", "Vargas", "Torres", "Rojas"]

    clientes = []

    for i in range(1, 91):

        nombre_completo = f"{nombres[(i - 1) % len(nombres)]} {apellidos[((i - 1) // len(nombres)) % len(apellidos)]}"

        clientes.append({
            "name": nombre_completo,
            "cedula": f"180{i:07d}",
            "email": f"cliente{i:03d}@correo.com",
            "telefono": f"099{i:07d}",
            "activo": True
        })

    for i in range(10):

        cliente_repetido = random.choice(
            clientes
        ).copy()

        clientes.append(
            cliente_repetido
        )

    random.shuffle(
        clientes
    )

    return clientes


# ============================================================
# GENERAR 100 PRODUCTOS
# ============================================================

def generar_productos():

    productos = []

    for i in range(1, 91):

        stock = random.randint(
            1,
            500
        )

        productos.append({
            "name": f"Producto {i:03d}",
            "codigo": f"{i:08d}",

            "precio_unitario": round(
                random.uniform(
                    5,
                    1500
                ),
                2
            ),

            "stock_disponible": stock,

            "activo": True
        })

    for i in range(10):

        producto_repetido = random.choice(
            productos
        ).copy()

        productos.append(
            producto_repetido
        )

    random.shuffle(
        productos
    )

    return productos


# ============================================================
# CARGAR CLIENTES
# ============================================================

def cargar_clientes():

    clientes = generar_clientes()

    ids_clientes = []

    correctos = 0
    errores = 0

    print("\n======================================")
    print("CARGANDO 100 CLIENTES")
    print("======================================")

    with ThreadPoolExecutor(
        max_workers=HILOS
    ) as executor:

        futuros = [
            executor.submit(
                enviar,
                API_CLIENTES,
                cliente
            )
            for cliente in clientes
        ]

        for futuro in as_completed(
            futuros
        ):

            resultado = futuro.result()

            if resultado.get("success"):

                correctos += 1

                ids_clientes.append(
                    resultado["id"]
                )

            else:

                errores += 1

                print(
                    "ERROR CLIENTE:",
                    resultado
                )

    print("\n--------------------------------------")
    print(f"Clientes insertados : {correctos}")
    print(f"Clientes con error  : {errores}")
    print("--------------------------------------")

    return ids_clientes


# ============================================================
# CARGAR PRODUCTOS
# ============================================================

def cargar_productos():

    productos = generar_productos()

    ids_productos = []

    correctos = 0
    errores = 0

    print("\n======================================")
    print("CARGANDO 100 PRODUCTOS")
    print("======================================")

    with ThreadPoolExecutor(
        max_workers=HILOS
    ) as executor:

        futuros = [
            executor.submit(
                enviar,
                API_PRODUCTOS,
                producto
            )
            for producto in productos
        ]

        for futuro in as_completed(
            futuros
        ):

            resultado = futuro.result()

            if resultado.get("success"):

                correctos += 1

                ids_productos.append(
                    resultado["id"]
                )

            else:

                errores += 1

                print(
                    "ERROR PRODUCTO:",
                    resultado
                )

    print("\n--------------------------------------")
    print(f"Productos insertados : {correctos}")
    print(f"Productos con error  : {errores}")
    print("--------------------------------------")

    return ids_productos


# ============================================================
# GENERAR UNA VENTA
# ============================================================

def generar_venta(
    ids_clientes,
    ids_productos,
    numero
):

    cantidad = random.randint(1, 3)
    descuento = 0

    return {

        "name": f"VEN-{numero:05d}",

        "cliente_id": random.choice(
            ids_clientes
        ),

        "producto_id": random.choice(
            ids_productos
        ),

        "cantidad": cantidad,

        "descuento": descuento,

        "observacion":
            "Registro generado automáticamente"
    }


# ============================================================
# CARGAR 2000 VENTAS
# ============================================================

def cargar_ventas(
    ids_clientes,
    ids_productos
):

    ventas = []

    print("\n======================================")
    print("GENERANDO 2000 VENTAS")
    print("======================================")

    # 1900 ORIGINALES
    for i in range(
        1,
        1901
    ):

        venta = generar_venta(
            ids_clientes,
            ids_productos,
            i
        )

        ventas.append(
            venta
        )

    for i in range(100):

        venta_repetida = random.choice(
            ventas
        ).copy()

        ventas.append(
            venta_repetida
        )

    random.shuffle(
        ventas
    )

    correctas = 0
    errores = 0

    print("\n======================================")
    print("CARGANDO 2000 VENTAS")
    print("======================================")

    with ThreadPoolExecutor(
        max_workers=HILOS
    ) as executor:

        futuros = [
            executor.submit(
                enviar,
                API_VENTAS,
                venta
            )
            for venta in ventas
        ]

        for numero, futuro in enumerate(
            as_completed(futuros),
            start=1
        ):

            resultado = futuro.result()

            if resultado.get("success"):

                correctas += 1

            else:

                errores += 1

                print(
                    "ERROR VENTA:",
                    resultado
                )

            if numero % 100 == 0:

                print(
                    f"Procesadas: "
                    f"{numero}/2000"
                )

    print("\n======================================")
    print("RESULTADO VENTAS")
    print("======================================")

    print(
        f"Ventas insertadas : {correctas}"
    )

    print(
        f"Ventas con error  : {errores}"
    )

    return correctas, errores


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

if __name__ == "__main__":

    print("""
=========================================
       GENERADOR TECHSTORE
=========================================

CLIENTES : 100
PRODUCTOS: 100
VENTAS   : 2000

=========================================
""")

    # ========================================================
    # 1. CLIENTES
    # ========================================================

    ids_clientes = cargar_clientes()


    # ========================================================
    # 2. PRODUCTOS
    # ========================================================

    ids_productos = cargar_productos()


    # ========================================================
    # 3. VENTAS
    # ========================================================

    if ids_clientes and ids_productos:

        cargar_ventas(
            ids_clientes,
            ids_productos
        )

    else:

        print(
            "\nNo se pueden generar ventas."
        )

        print(
            "Revise primero la carga "
            "de clientes y productos."
        )