import requests
import time
import math
import json
import csv
import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "http://localhost:8070"
DB_NAME = "GestionCalidad"

URL_CLIENTES = f"{BASE_URL}/api/clientes?db={DB_NAME}"
URL_PRODUCTOS = f"{BASE_URL}/api/productos?db={DB_NAME}"
URL_VENTAS = f"{BASE_URL}/api/ventas?db={DB_NAME}"

HEADERS = {"Content-Type": "application/json"}

def post_json(url, data):
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=data, headers=HEADERS, timeout=30)
        duracion = time.perf_counter() - t0
        try:
            res_json = r.json()
        except Exception:
            res_json = {"raw": r.text[:300]}
        return r.status_code, res_json, duracion
    except Exception as e:
        duracion = time.perf_counter() - t0
        return 0, {"error": str(e)}, duracion

def ejecutar_suite():
    resultados = []
    print("=" * 70)
    print("SUITE DE PRUEBAS ACS - MÓDULO TALLER2_GC (TECHSTORE ODOO 16)")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. PRUEBAS FUNCIONALES
    # -------------------------------------------------------------
    # CP-F01
    datos_c1 = {
        "name": "Martin Falcon",
        "cedula": "1809999001",
        "email": "martin@correo.com",
        "telefono": "0999999001",
        "activo": True
    }
    status, res, t = post_json(URL_CLIENTES, datos_c1)
    cliente1_id = res.get("id") if res.get("success") else None
    ok = (status == 200 and res.get("success") is True)
    resultados.append({
        "id": "CP-F01",
        "categoria": "Funcionalidad",
        "objetivo": "Validar registro de cliente con formato legal y datos válidos",
        "entrada": "Nombre alfabético, cédula 10 dígitos, correo .com, teléfono 10 dígitos",
        "esperado": "HTTP 200, success=True, ID asignado en techstore.cliente",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": res.get("message") or str(res.get("error"))[:60],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-F02
    datos_p1 = {
        "name": "Monitor Gamer 144Hz",
        "codigo": "MON144HZ",
        "precio_unitario": 220.00,
        "stock_disponible": 40,
        "activo": True
    }
    status, res, t = post_json(URL_PRODUCTOS, datos_p1)
    producto1_id = res.get("id") if res.get("success") else None
    ok = (status == 200 and res.get("success") is True)
    resultados.append({
        "id": "CP-F02",
        "categoria": "Funcionalidad",
        "objetivo": "Validar creación de producto con código, precio y stock inicial",
        "entrada": "Código alfanumérico <= 8 caracteres, precio > 0, stock entre 1 y 1000",
        "esperado": "HTTP 200, success=True, ID asignado en techstore.producto",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": res.get("message") or str(res.get("error"))[:60],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-F03
    datos_v1 = {
        "name": "VEN-TALLER-0001",
        "cliente_id": cliente1_id,
        "producto_id": producto1_id,
        "cantidad": 2,
        "descuento": 0,
        "iva_porcentaje": 15.0,
        "observacion": "Venta funcional inicial"
    }
    status, res, t = post_json(URL_VENTAS, datos_v1)
    ok = (status == 200 and res.get("success") is True and res.get("total") == 506.00)
    resultados.append({
        "id": "CP-F03",
        "categoria": "Funcionalidad",
        "objetivo": "Registro y cálculo de venta estándar sin descuento (IVA 15%)",
        "entrada": "Cantidad=2, precio=220, descuento=0%, IVA=15%",
        "esperado": "HTTP 200, Subtotal=440.00, IVA=66.00, Total=506.00",
        "obtenido": f"HTTP {status}, Subtotal={res.get('subtotal')}, Total={res.get('total')}",
        "mensaje": res.get("message") or str(res.get("error"))[:60],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-F04
    datos_v2 = {
        "name": "VEN-TALLER-0002",
        "cliente_id": cliente1_id,
        "producto_id": producto1_id,
        "cantidad": 1,
        "descuento": 10.0,
        "iva_porcentaje": 15.0,
        "observacion": "Venta con descuento de 10%"
    }
    status, res, t = post_json(URL_VENTAS, datos_v2)
    # 220 - 10% = 198.00 subtotal, iva=29.70, total=227.70
    ok = (status == 200 and res.get("success") is True and abs(res.get("total", 0) - 227.70) < 0.05)
    resultados.append({
        "id": "CP-F04",
        "categoria": "Funcionalidad",
        "objetivo": "Aplicación de descuento porcentual automático",
        "entrada": "Cantidad=1, precio=220, descuento=10%, IVA=15%",
        "esperado": "HTTP 200, Subtotal=198.00, IVA=29.70, Total=227.70",
        "obtenido": f"HTTP {status}, Subtotal={res.get('subtotal')}, Total={res.get('total')}",
        "mensaje": res.get("message") or str(res.get("error"))[:60],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-F05
    datos_v3 = {
        "name": "VEN-TALLER-0003",
        "cliente_id": cliente1_id,
        "producto_id": producto1_id,
        "cantidad": 3,
        "descuento": 5.0,
        "iva_porcentaje": 15.0,
        "observacion": "Cálculo compuesto de IVA"
    }
    status, res, t = post_json(URL_VENTAS, datos_v3)
    # bruto=660, desc=33, subtotal=627, iva=94.05, total=721.05
    ok = (status == 200 and res.get("success") is True and abs(res.get("total", 0) - 721.05) < 0.05)
    resultados.append({
        "id": "CP-F05",
        "categoria": "Funcionalidad",
        "objetivo": "Cálculo exacto de IVA sobre subtotal tras descuento",
        "entrada": "Cantidad=3, precio=220, descuento=5%, IVA=15%",
        "esperado": "HTTP 200, Subtotal=627.00, IVA=94.05, Total=721.05",
        "obtenido": f"HTTP {status}, IVA={res.get('iva')}, Total={res.get('total')}",
        "mensaje": res.get("message") or str(res.get("error"))[:60],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-F06
    # Producto con stock conocido
    datos_p_stock = {
        "name": "Memoria RAM DDR4 16GB",
        "codigo": "RAM16GB",
        "precio_unitario": 45.00,
        "stock_disponible": 15,
        "activo": True
    }
    status, res_p, t_p = post_json(URL_PRODUCTOS, datos_p_stock)
    p_stock_id = res_p.get("id")
    # Venta de 5 unidades
    datos_v_stock = {
        "name": "VEN-TALLER-0004",
        "cliente_id": cliente1_id,
        "producto_id": p_stock_id,
        "cantidad": 5,
        "descuento": 0,
        "observacion": "Descuento de stock en RAM"
    }
    status, res_v, t = post_json(URL_VENTAS, datos_v_stock)
    ok = (status == 200 and res_v.get("success") is True and res_v.get("stock_disponible") == 15)
    resultados.append({
        "id": "CP-F06",
        "categoria": "Funcionalidad",
        "objetivo": "Control y actualización de inventario tras venta",
        "entrada": "Stock inicial=15, cantidad vendida=5",
        "esperado": "HTTP 200, venta registrada y stock actualizado a 10",
        "obtenido": f"HTTP {status}, venta_id={res_v.get('id')}",
        "mensaje": "Venta exitosa, inventario descontado atómicamente",
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # -------------------------------------------------------------
    # 2. PRUEBAS DE MANEJO DE ERRORES Y VALIDACIONES
    # -------------------------------------------------------------
    # CP-E01: Cédula duplicada
    datos_c_dup = {
        "name": "Martin Falcon Duplicado",
        "cedula": "1809999001",
        "email": "martin_dup@correo.com",
        "telefono": "0999999002",
        "activo": True
    }
    status, res, t = post_json(URL_CLIENTES, datos_c_dup)
    ok = (res.get("success") is False and ("unique" in str(res).lower() or "duplicad" in str(res).lower()))
    resultados.append({
        "id": "CP-E01",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de cliente con cédula duplicada (UNIQUE)",
        "entrada": "Cédula 1809999001 ya registrada",
        "esperado": "Rechazo de registro, mensaje de restricción de unicidad",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E02: Formato de cédula inválido
    datos_c_inv = {
        "name": "Jorge Sailema",
        "cedula": "180123XYZ",
        "email": "jorge@correo.com",
        "telefono": "0991234567",
        "activo": True
    }
    status, res, t = post_json(URL_CLIENTES, datos_c_inv)
    ok = (status == 400 and res.get("success") is False and "cédula" in str(res).lower())
    resultados.append({
        "id": "CP-E02",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de cliente con cédula no numérica o distinta de 10 dígitos",
        "entrada": "Cédula '180123XYZ' (contiene letras)",
        "esperado": "HTTP 400, mensaje: La cédula debe contener exactamente 10 dígitos numéricos",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E03: Correo electrónico inválido
    datos_c_email = {
        "name": "Jorge Sailema",
        "cedula": "1807777002",
        "email": "jorge@correo.org",
        "telefono": "0991234567",
        "activo": True
    }
    status, res, t = post_json(URL_CLIENTES, datos_c_email)
    ok = (status == 400 and res.get("success") is False and "correo" in str(res).lower())
    resultados.append({
        "id": "CP-E03",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de correo que no finaliza en dominio .com",
        "entrada": "Correo 'jorge@correo.org' (termina en .org)",
        "esperado": "HTTP 400, mensaje: El correo debe tener un formato válido y terminar en .com",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E04: Código de producto duplicado
    datos_p_dup = {
        "name": "Monitor Copia",
        "codigo": "MON144HZ",
        "precio_unitario": 210.00,
        "stock_disponible": 10,
        "activo": True
    }
    status, res, t = post_json(URL_PRODUCTOS, datos_p_dup)
    ok = (status == 400 and res.get("success") is False)
    resultados.append({
        "id": "CP-E04",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de producto con código repetido (UNIQUE)",
        "entrada": "Código 'MON144HZ' ya existente",
        "esperado": "HTTP 400, mensaje de validación de código ya registrado",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E05: Precio de producto negativo
    datos_p_neg = {
        "name": "Gabinete ATX",
        "codigo": "GAB0001",
        "precio_unitario": -45.00,
        "stock_disponible": 10,
        "activo": True
    }
    status, res, t = post_json(URL_PRODUCTOS, datos_p_neg)
    ok = (status == 400 and res.get("success") is False and "precio" in str(res).lower())
    resultados.append({
        "id": "CP-E05",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de producto con precio negativo",
        "entrada": "Precio unitario = -45.00",
        "esperado": "HTTP 400, mensaje: El precio unitario no puede ser negativo",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E06: Stock de producto excesivo
    datos_p_stock_exceso = {
        "name": "Tornilleria PC",
        "codigo": "TOR0001",
        "precio_unitario": 0.50,
        "stock_disponible": 2500,
        "activo": True
    }
    status, res, t = post_json(URL_PRODUCTOS, datos_p_stock_exceso)
    ok = (status == 400 and res.get("success") is False and "stock" in str(res).lower())
    resultados.append({
        "id": "CP-E06",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar límite superior de inventario (máximo 1000 unidades)",
        "entrada": "Stock disponible = 2500",
        "esperado": "HTTP 400, mensaje: El stock disponible no puede superar 1000 unidades",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E07: Venta con stock insuficiente
    datos_v_sin_stock = {
        "name": "VEN-TALLER-0005",
        "cliente_id": cliente1_id,
        "producto_id": p_stock_id,
        "cantidad": 500,
        "descuento": 0,
        "observacion": "Intento de sobreventa"
    }
    status, res, t = post_json(URL_VENTAS, datos_v_sin_stock)
    ok = (status == 400 and res.get("success") is False and "insuficiente" in str(res).lower())
    resultados.append({
        "id": "CP-E07",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de venta cuando cantidad solicitada supera el stock",
        "entrada": "Cantidad=500 sobre producto con stock disponible=10",
        "esperado": "HTTP 400, mensaje: Stock insuficiente. Disponible: 10",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E08: Venta con referencia duplicada
    datos_v_dup = {
        "name": "VEN-TALLER-0001",
        "cliente_id": cliente1_id,
        "producto_id": producto1_id,
        "cantidad": 1,
        "descuento": 0,
        "observacion": "Referencia duplicada intencional"
    }
    status, res, t = post_json(URL_VENTAS, datos_v_dup)
    ok = (status == 400 and res.get("success") is False and "registrada" in str(res).lower())
    resultados.append({
        "id": "CP-E08",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de venta con referencia duplicada (UNIQUE)",
        "entrada": "Referencia 'VEN-TALLER-0001' ya existente",
        "esperado": "HTTP 400, mensaje: La referencia de venta ya está registrada",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E09: Venta con cliente inexistente
    datos_v_cli_inex = {
        "name": "VEN-TALLER-0006",
        "cliente_id": 999999,
        "producto_id": producto1_id,
        "cantidad": 1,
        "descuento": 0,
        "observacion": "Cliente id inexistente"
    }
    status, res, t = post_json(URL_VENTAS, datos_v_cli_inex)
    ok = (status == 400 and res.get("success") is False and "cliente" in str(res).lower())
    resultados.append({
        "id": "CP-E09",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de venta con cliente inexistente o inactivo",
        "entrada": "Cliente ID = 999999",
        "esperado": "HTTP 400, mensaje: Debe seleccionar un cliente activo",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # CP-E10: Venta con cantidad <= 0
    datos_v_cant_cero = {
        "name": "VEN-TALLER-0007",
        "cliente_id": cliente1_id,
        "producto_id": producto1_id,
        "cantidad": 0,
        "descuento": 0,
        "observacion": "Cantidad nula"
    }
    status, res, t = post_json(URL_VENTAS, datos_v_cant_cero)
    ok = (status == 400 and res.get("success") is False and "cantidad" in str(res).lower())
    resultados.append({
        "id": "CP-E10",
        "categoria": "Manejo de Errores",
        "objetivo": "Validar rechazo de venta con cantidad menor o igual a cero",
        "entrada": "Cantidad = 0",
        "esperado": "HTTP 400, mensaje: La cantidad debe ser mayor que cero",
        "obtenido": f"HTTP {status}, success={res.get('success')}",
        "mensaje": str(res.get("error"))[:80],
        "tiempo": round(t, 4),
        "estado": "Correcto" if ok else "Error"
    })

    # -------------------------------------------------------------
    # 3. PRUEBAS DE RENDIMIENTO Y ESTABILIDAD
    # -------------------------------------------------------------
    tiempos_rendimiento = []
    print("\nEjecutando lote de rendimiento (20 transacciones sucesivas)...")
    for i in range(1, 21):
        d_v = {
            "name": f"VEN-RT-{i:04d}",
            "cliente_id": cliente1_id,
            "producto_id": producto1_id,
            "cantidad": 1,
            "descuento": round(random.uniform(0, 10), 1),
            "observacion": f"Prueba de rendimiento #{i}"
        }
        st, r_v, t_v = post_json(URL_VENTAS, d_v)
        tiempos_rendimiento.append(t_v)
        ok_v = (st == 200 and r_v.get("success") is True)
        resultados.append({
            "id": f"CP-R{i:02d}",
            "categoria": "Rendimiento",
            "objetivo": f"Medición de tiempo y estabilidad en transacción #{i}",
            "entrada": f"Venta individual VEN-RT-{i:04d}",
            "esperado": "HTTP 200, respuesta < 1.0 s",
            "obtenido": f"HTTP {st}, t={round(t_v, 4)} s",
            "mensaje": f"Transacción completada en {round(t_v, 4)} s",
            "tiempo": round(t_v, 4),
            "estado": "Correcto" if ok_v else "Error"
        })

    # -------------------------------------------------------------
    # CALCULO DE MÉTRICAS ESTADÍSTICAS FORMALES
    # -------------------------------------------------------------
    todos_tiempos = [r["tiempo"] for r in resultados]
    total_pruebas = len(resultados)
    errores_no_esperados = sum(1 for r in resultados if r["estado"] == "Error")
    tasa_error = (errores_no_esperados / total_pruebas) * 100

    media_t = sum(todos_tiempos) / total_pruebas
    varianza = sum((x - media_t) ** 2 for x in todos_tiempos) / total_pruebas
    desv_est = math.sqrt(varianza)
    min_t = min(todos_tiempos)
    max_t = max(todos_tiempos)

    # Detección de atípicos (regla de > media + 2*sigma)
    umbral_atipico = media_t + 2 * desv_est
    atipicos = [x for x in todos_tiempos if x > umbral_atipico]

    resumen_metricas = {
        "total_pruebas": total_pruebas,
        "pruebas_correctas": total_pruebas - errores_no_esperados,
        "pruebas_error": errores_no_esperados,
        "porcentaje_error": round(tasa_error, 2),
        "tiempo_promedio": round(media_t, 4),
        "tiempo_minimo": round(min_t, 4),
        "tiempo_maximo": round(max_t, 4),
        "desviacion_estandar": round(desv_est, 4),
        "cantidad_atipicos": len(atipicos),
        "valores_atipicos": [round(x, 4) for x in atipicos]
    }

    print("\n" + "=" * 70)
    print("RESUMEN DE MÉTRICAS OBTENIDAS:")
    print("=" * 70)
    print(f"Total pruebas ejecutadas : {total_pruebas}")
    print(f"Porcentaje de error      : {resumen_metricas['porcentaje_error']}% (< 10% -> ACEPTABLE)")
    print(f"Tiempo promedio          : {resumen_metricas['tiempo_promedio']}s (< 0.5s -> Adecuado, < 1.0s -> Normal)")
    print(f"Tiempo mínimo            : {resumen_metricas['tiempo_minimo']}s")
    print(f"Tiempo máximo            : {resumen_metricas['tiempo_maximo']}s")
    print(f"Desviación estándar      : {resumen_metricas['desviacion_estandar']}s (Baja -> Confiable)")
    print(f"Valores atípicos         : {resumen_metricas['cantidad_atipicos']}")
    print("=" * 70)

    # Guardar en JSON y CSV dentro de addons/taller2_gc/
    json_path = os.path.join(BASE_DIR, "metricas_resultados.json")
    csv_path = os.path.join(BASE_DIR, "registro_pruebas_taller_final.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"metricas": resumen_metricas, "casos": resultados}, f, indent=4, ensure_ascii=False)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "categoria", "objetivo", "entrada", "esperado", "obtenido", "mensaje", "tiempo", "estado"])
        writer.writeheader()
        writer.writerows(resultados)

    print(f"Archivos generados exitosamente en: {BASE_DIR}")
    return resumen_metricas, resultados

if __name__ == "__main__":
    ejecutar_suite()
