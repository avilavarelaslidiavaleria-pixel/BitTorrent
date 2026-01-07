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

import socket, threading, json, time
from rich.console import Console
from rich.table import Table
from rich.live import Live

# ================= CONFIGURACIÓN =================
TIEMPO_LIMITE = 15  # Segundos para limpiar nodos offline
PUERTO_TRACKER = 6000
nodos_activos = {}
lock = threading.Lock()
console = Console()

def generar_tabla():
    """Genera la tabla visual con columnas de Estado y Progreso"""
    table = Table(title=f"📡 ENJAMBRE BITTORRENT - {time.strftime('%H:%M:%S')}", header_style="bold magenta")
    table.add_column("PEER (IP:PUERTO)", style="cyan", no_wrap=True)
    table.add_column("ESTADO", justify="center")
    table.add_column("PROGRESO", style="green")
    table.add_column("ARCHIVOS COMPARTIENDO", style="yellow")
    
    with lock:
        # TOLERANCIA A FALLOS: Limpiar los que ya no mandan registro
        ahora = time.time()
        nodos_muertos = [nid for nid, info in nodos_activos.items() if ahora - info["ultima_vez"] > TIEMPO_LIMITE]
        for nid in nodos_muertos:
            del nodos_activos[nid]

        for nid, info in nodos_activos.items():
            # Determinar Seeder o Leecher
            prog_dict = info.get("progreso", {})
            estado = "[bold green]Seeder[/bold green]" if all(p == 100 for p in prog_dict.values()) and prog_dict else "[bold yellow]Leecher[/bold yellow]"
            if not prog_dict: estado = "[bold red]Inactivo[/bold red]"
            
            prog_texto = ", ".join([f"{a}:{p}%" for a, p in prog_dict.items()])
            arch_texto = ", ".join(info.get("archivos_compartidos", []))
            
            table.add_row(nid, estado, prog_texto or "0%", arch_texto or "Ninguno")
    return table

def manejar_nodo(conn, addr):
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data: return
        msg = json.loads(data)
        
        if msg.get("tipo") == "REGISTRO":
            # TRANSPARENCIA: Usar la IP reportada (Tailscale)
            ip_a_usar = msg.get("ip_local", addr[0])
            nid = f"{ip_a_usar}:{msg['puerto']}"
            with lock:
                nodos_activos[nid] = {
                    "progreso": msg.get("progreso", {}),
                    "archivos_compartidos": msg.get("archivos_compartidos", []),
                    "ultima_vez": time.time()
                }
        # ... (puedes añadir BUSQUEDA y LISTAR_TODO aquí)
    except: pass
    finally: conn.close()

def iniciar_tracker():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PUERTO_TRACKER))
    s.listen()
    
    # LIVE DISPLAY: Esto hace que la tabla se actualice sin llenar la terminal de texto
    with Live(generar_tabla(), refresh_per_second=1, console=console) as live:
        while True:
            s.settimeout(1)
            try:
                c, a = s.accept()
                threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()
            except socket.timeout: pass
            live.update(generar_tabla())

if __name__ == "__main__": iniciar_tracker()