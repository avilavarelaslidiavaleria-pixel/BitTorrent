# import socket, threading, json, time
# from rich.console import Console
# from rich.table import Table

# # ================= CONFIGURACIÓN =================
# TIEMPO_LIMITE = 45 # Aumentamos el margen para evitar desconexiones falsas
# PUERTO_TRACKER = 6000
# nodos_activos = {}
# console = Console()

# def mostrar_estado_red():
#     ahora = time.strftime('%H:%M:%S')
#     table = Table(title=f"ENJAMBRE BITTORRENT - {ahora}", header_style="bold magenta")
#     table.add_column("PEER ID (IP:PUERTO)", style="cyan")
#     table.add_column("PROGRESO POR ARCHIVO", style="green")
#     table.add_column("LATIDO", style="dim")

#     for nid, info in nodos_activos.items():
#         progreso = ", ".join([f"{a}:{p}%" for a, p in info["progreso"].items()]) or "0%"
#         table.add_row(nid, progreso, time.strftime('%H:%M:%S', time.localtime(info["ultima_vez"])))
#     console.print(table)

# def monitor_de_limpieza():
#     while True:
#         ahora = time.time()
#         inactivos = [nid for nid, info in nodos_activos.items() if ahora - info["ultima_vez"] > TIEMPO_LIMITE]
#         for nid in inactivos: 
#             del nodos_activos[nid]
#         if inactivos: mostrar_estado_red()
#         time.sleep(5)

# def manejar_nodo(conn, addr):
#     try:
#         data = conn.recv(4096).decode("utf-8")
#         if not data: return
#         msg = json.loads(data)
#         tipo = msg.get("tipo")

#         if tipo == "REGISTRO":
#             # Identificación única por IP y Puerto
#             ip_reportada = msg.get("ip_local", addr[0])
#             nodo_id = f"{ip_reportada}:{msg['puerto']}"
#             nodos_activos[nodo_id] = {
#                 "ip": ip_reportada,
#                 "puerto": msg["puerto"],
#                 "progreso": msg.get("progreso", {}),
#                 "total_fragmentos": msg.get("total_fragmentos", {}),
#                 "ultima_vez": time.time()
#             }
#             mostrar_estado_red()

#         elif tipo == "BUSQUEDA":
#             archivo = msg.get("archivo")
#             encontrados = []
#             for info in nodos_activos.values():
#                 if info["progreso"].get(archivo, 0) >= 20: # Regla del 20%
#                     encontrados.append({
#                         "ip": info["ip"], "puerto": info["puerto"],
#                         "total_fragmentos": info["total_fragmentos"].get(archivo, 0)
#                     })
#             conn.send(json.dumps(encontrados).encode("utf-8"))

#         elif tipo == "LISTAR_TODO":
#             archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
#             conn.send(json.dumps(archivos).encode("utf-8"))
#     except: pass
#     finally: conn.close()

# if __name__ == "__main__":
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     server.bind(("0.0.0.0", PUERTO_TRACKER))
#     server.listen()
#     threading.Thread(target=monitor_de_limpieza, daemon=True).start()
#     print(f"--- TRACKER LISTO EN PUERTO {PUERTO_TRACKER} ---")
#     while True:
#         c, a = server.accept()
#         threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

import socket, threading, json, time
from rich.console import Console
from rich.table import Table

TIEMPO_LIMITE = 30
PUERTO_TRACKER = 6000
nodos_activos = {}
console = Console()

def mostrar_estado_red():
    ahora = time.strftime('%H:%M:%S')
    table = Table(title=f"ENJAMBRE BITTORRENT - {ahora}", header_style="bold magenta")
    table.add_column("PEER ID", style="cyan")
    table.add_column("PROGRESO", style="green")
    table.add_column("ARCHIVOS", style="yellow")
    
    for nid, info in nodos_activos.items():
        prog = ", ".join([f"{a}:{p}%" for a, p in info["progreso"].items()])
        table.add_row(nid, prog or "0%", ", ".join(info["progreso"].keys()) or "Ninguno")
    console.print(table)

def manejar_nodo(conn, addr):
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data: return
        msg = json.loads(data)
        tipo = msg.get("tipo")

        if tipo == "REGISTRO":
            # PRIORIDAD: Usar la IP local que reporta el nodo para evitar el NAT Loopback
            ip_a_usar = msg.get("ip_local", addr[0])
            nid = f"{ip_a_usar}:{msg['puerto']}"
            nodos_activos[nid] = {
                "ip": ip_a_usar, "puerto": msg["puerto"],
                "progreso": msg.get("progreso", {}),
                "total_fragmentos": msg.get("total_fragmentos", {}),
                "ultima_vez": time.time()
            }
            mostrar_estado_red()

        elif tipo == "BUSQUEDA":
            archivo = msg.get("archivo")
            encontrados = [{"ip": info["ip"], "puerto": info["puerto"], 
                            "total_fragmentos": info.get("total_fragmentos", {}).get(archivo, 0)} 
                           for info in nodos_activos.values() if info["progreso"].get(archivo, 0) >= 20]
            conn.send(json.dumps(encontrados).encode("utf-8"))

        elif tipo == "LISTAR_TODO":
            archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
            conn.send(json.dumps(archivos).encode("utf-8"))
    except: pass
    finally: conn.close()

def iniciar_tracker():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PUERTO_TRACKER))
    s.listen()
    print(f"--- TRACKER ACTIVO EN PUERTO {PUERTO_TRACKER} ---")
    while True:
        c, a = s.accept()
        threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

if __name__ == "__main__": iniciar_tracker()