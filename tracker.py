# import socket, threading, json, time
# from rich.console import Console
# from rich.table import Table

# TIEMPO_LIMITE = 30
# PUERTO_TRACKER = 6000
# nodos_activos = {}
# console = Console()

# def mostrar_estado_red():
#     ahora = time.strftime('%H:%M:%S')
#     table = Table(title=f"ENJAMBRE BITTORRENT - {ahora}", header_style="bold magenta")
#     table.add_column("PEER ID", style="cyan")
#     table.add_column("PROGRESO", style="green")
#     table.add_column("ARCHIVOS", style="yellow")
    
#     for nid, info in nodos_activos.items():
#         prog = ", ".join([f"{a}:{p}%" for a, p in info["progreso"].items()])
#         table.add_row(nid, prog or "0%", ", ".join(info["progreso"].keys()) or "Ninguno")
#     console.print(table)

# def manejar_nodo(conn, addr):
#     print("Nodo conectado desde:", addr)

#     try:
#         data = conn.recv(4096).decode("utf-8")
#         if not data: return
#         msg = json.loads(data)
#         tipo = msg.get("tipo")

#         if tipo == "REGISTRO":
#             # PRIORIDAD: Usar la IP local que reporta el nodo para evitar el NAT Loopback
#             # ip_a_usar = msg.get("ip_local", addr[0])
#             ip_a_usar = addr[0]   # SIEMPRE la IP vista por el tracker
#             nid = f"{ip_a_usar}:{msg['puerto']}"
#             nodos_activos[nid] = {
#                 "ip": ip_a_usar, "puerto": msg["puerto"],
#                 "progreso": msg.get("progreso", {}),
#                 "total_fragmentos": msg.get("total_fragmentos", {}),
#                 "ultima_vez": time.time()
#             }
#             mostrar_estado_red()

#         elif tipo == "BUSQUEDA":
#             archivo = msg.get("archivo")
#             encontrados = [{"ip": info["ip"], "puerto": info["puerto"], 
#                             "total_fragmentos": info.get("total_fragmentos", {}).get(archivo, 0)} 
#                            for info in nodos_activos.values() if info["progreso"].get(archivo, 0) >= 20]
#             conn.send(json.dumps(encontrados).encode("utf-8"))

#         elif tipo == "LISTAR_TODO":
#             archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
#             conn.send(json.dumps(archivos).encode("utf-8"))
#     except: pass
#     finally: conn.close()

# def iniciar_tracker():
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind(("0.0.0.0", PUERTO_TRACKER))
#     s.listen()
#     print(f"--- TRACKER ACTIVO EN PUERTO {PUERTO_TRACKER} ---")
#     while True:
#         c, a = s.accept()
#         threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

# if __name__ == "__main__": iniciar_tracker()

import socket
import threading
from rich.console import Console
from rich.table import Table
from rich.live import Live
import json
import time

console = Console()
# Diccionario para guardar el estado de la red
# { "100.x.x.x": {"archivos_completos": [], "descargando": {"file": %, "rol": "Leecher"}} }
nodos_activos = {}
lock = threading.Lock()

def manejar_nodo(conn, addr):
    global nodos_activos
    try:
        data = conn.recv(4096).decode('utf-8')
        mensaje = json.loads(data)
        ip_nodo = addr[0]
        
        with lock:
            nodos_activos[ip_nodo] = {
                "archivos": mensaje.get("archivos", []),
                "descargas": mensaje.get("descargas", {}),
                "rol": mensaje.get("rol", "Peer"),
                "last_seen": time.time()
            }
            # Si el nodo ya tiene el archivo al 100%, es Seeder, si no, Leecher
            # Responder con la lista de otros nodos para que pueda conectar
            respuesta = json.dumps(nodos_activos)
            conn.send(respuesta.encode('utf-8'))
    except Exception as e:
        console.print(f"[red]Error con nodo {addr}: {e}[/red]")
    finally:
        conn.close()

def mostrar_dashboard():
    with Live(refresh_per_second=1) as live:
        while True:
            table = Table(title="[bold blue]TRACKER - PROYECTO SISTEMAS DISTRIBUIDOS[/bold blue]")
            table.add_column("IP Nodo (Tailscale)", style="cyan")
            table.add_column("Rol", style="magenta")
            table.add_column("Archivos Completos (Seed)", style="green")
            table.add_column("Progreso Descargas (Leech)", style="yellow")
            
            with lock:
                for ip, info in nodos_activos.items():
                    archivos_str = ", ".join(info['archivos'])
                    descargas_str = ""
                    for f, p in info['descargas'].items():
                        descargas_str += f"{f}: {p}% "
                    
                    table.add_row(ip, info['rol'], archivos_str, descargas_str)
            
            live.update(table)
            time.sleep(1)

def iniciar_tracker():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # IMPORTANTE: Escuchar en todas las interfaces para que Tailscale lo vea
    server.bind(('0.0.0.0', 5000))
    server.listen()
    console.print("[bold green]Tracker escuchando en puerto 5000 (Red Tailscale)...[/bold green]")
    
    threading.Thread(target=mostrar_dashboard, daemon=True).start()
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_nodo, args=(conn, addr)).start()

if __name__ == "__main__":
    iniciar_tracker()