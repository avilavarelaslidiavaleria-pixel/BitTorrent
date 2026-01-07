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

# import socket, threading, json, time
# from rich.console import Console
# from rich.table import Table

# PUERTO_TRACKER = 6000
# nodos_activos = {} 
# console = Console()

# def manejar_nodo(conn, addr):
#     try:
#         data = conn.recv(4096).decode("utf-8")
#         if not data: return
#         msg = json.loads(data)
#         tipo = msg.get("tipo")
        
#         # AVISO DE CONEXIÓN (Para que sepas que el nodo llegó)
#         print(f"[*] Recibido {tipo} de {addr[0]}")

#         if tipo == "REGISTRO":
#             # Usamos la IP local reportada para que funcione en LAN
#             ip_a_usar = msg.get("ip_local", addr[0])
#             nid = f"{ip_a_usar}:{msg['puerto']}"
            
#             nodos_activos[nid] = {
#                 "ip": ip_a_usar, 
#                 "puerto": msg["puerto"],
#                 "progreso": msg.get("progreso", {}),
#                 "total_fragmentos": msg.get("total_fragmentos", {}),
#                 "ultima_vez": time.time()
#             }
#             console.print(f"[bold green][+] Nodo registrado: {nid}[/bold green]")
#             mostrar_estado_red()

#         elif msg.get("tipo") == "BUSQUEDA":
#             archivo = msg.get("archivo")
#             # Filtramos nodos que tienen al menos el 20% del archivo
#             encontrados = [{"ip": info["ip"], "puerto": info["puerto"], 
#                             "total_fragmentos": info.get("total_fragmentos", {}).get(archivo, 0)} 
#                            for info in nodos_activos.values() if info["progreso"].get(archivo, 0) >= 20]
#             conn.send(json.dumps(encontrados).encode("utf-8"))
#         elif msg.get("tipo") == "LISTAR_TODO":
#             archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
#             conn.send(json.dumps(archivos).encode("utf-8"))
#     except: pass
#     finally: conn.close()

# def iniciar_tracker():
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind(("0.0.0.0", PUERTO_TRACKER))
#     s.listen()
#     console.print(f"[bold green]✔ TRACKER GLOBAL ACTIVO EN PUERTO {PUERTO_TRACKER}[/bold green]")
#     while True:
#         c, a = s.accept()
#         threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

# if __name__ == "__main__":
#     iniciar_tracker()

# import socket, threading, json, time
# from rich.console import Console
# from rich.table import Table

# PUERTO_TRACKER = 6000
# nodos_activos = {}
# console = Console()

# def mostrar_estado_red():
#     """Limpia la pantalla y dibuja la tabla con los nodos actuales."""
#     console.clear() # Esto evita que se repita el texto hacia abajo
    
#     ahora = time.strftime('%H:%M:%S')
#     table = Table(
#         title=f"[bold magenta]ENJAMBRE BITTORRENT GLOBAL[/bold magenta] - {ahora}", 
#         header_style="bold cyan",
#         border_style="bright_blue"
#     )
    
#     table.add_column("PEER ID (IP:PORT)", style="cyan", justify="center")
#     table.add_column("IP LOCAL", style="green", justify="center")
#     table.add_column("PROGRESO POR ARCHIVO", style="yellow")
#     table.add_column("ESTADO", justify="center")

#     for nid, info in nodos_activos.items():
#         # Formatear el progreso: "archivo.mp4: 100%"
#         prog_detalles = []
#         estado = "[bold green]SEEDER[/bold green]" # Asumimos seeder por defecto
        
#         for arc, p in info["progreso"].items():
#             prog_detalles.append(f"{arc}: {p}%")
#             if p < 100:
#                 estado = "[bold blue]LEECHER[/bold blue]"
        
#         prog_str = "\n".join(prog_detalles) if prog_detalles else "Esperando..."
        
#         table.add_row(
#             nid, 
#             info["ip_privada"], 
#             prog_str, 
#             estado
#         )
    
#     console.print(table)

# def manejar_nodo(conn, addr):
#     try:
#         data = conn.recv(8192).decode("utf-8")
#         if not data: return
#         msg = json.loads(data)
#         tipo = msg.get("tipo")

#         if tipo == "REGISTRO":
#             # Guardamos la IP que detecta el socket (pública) y la que reporta el nodo (privada)
#             ip_publica = addr[0]
#             ip_privada = msg.get("ip_local", "N/A")
#             puerto = msg.get("puerto")
            
#             # El ID único será IP_PUBLICA:PUERTO para no confundir nodos de distintas casas
#             nid = f"{ip_publica}:{puerto}"
            
#             nodos_activos[nid] = {
#                 "ip_privada": ip_privada,
#                 "puerto": puerto,
#                 "progreso": msg.get("progreso", {}),
#                 "total_fragmentos": msg.get("total_fragmentos", {}),
#                 "ultima_vez": time.time()
#             }
#             mostrar_estado_red()

#         elif tipo == "BUSQUEDA":
#             archivo = msg.get("archivo")
#             # Devolvemos la IP local si están en la misma red, o la pública si no
#             encontrados = [{"ip": info["ip_privada"], "puerto": info["puerto"], "total_fragmentos": info.get("total_fragmentos", {}).get(archivo, 0)} 
#                            for info in nodos_activos.values() if info["progreso"].get(archivo, 0) >= 20]
#             conn.send(json.dumps(encontrados).encode("utf-8"))

#         elif tipo == "LISTAR_TODO":
#             archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
#             conn.send(json.dumps(archivos).encode("utf-8"))
#     except:
#         pass
#     finally:
#         conn.close()

# def iniciar_tracker():
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind(("0.0.0.0", PUERTO_TRACKER))
#     s.listen()
#     console.print(f"[bold green]✔ TRACKER GLOBAL LISTO EN PUERTO {PUERTO_TRACKER}[/bold green]")
    
#     while True:
#         c, a = s.accept()
#         threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

# if __name__ == "__main__":
#     iniciar_tracker()

import socket, threading, json, time
from rich.console import Console
from rich.table import Table

PUERTO_TRACKER = 6000
nodos_activos = {}
console = Console()

def mostrar_estado_red():
    """Limpia la pantalla y dibuja la tabla con los nodos actuales."""
    console.clear()
    
    ahora = time.strftime('%H:%M:%S')
    table = Table(
        title=f"[bold magenta]ENJAMBRE BITTORRENT GLOBAL[/bold magenta] - {ahora}", 
        header_style="bold cyan",
        border_style="bright_blue"
    )
    
    table.add_column("PEER ID (PÚBLICO)", style="cyan", justify="center")
    table.add_column("IP LOCAL", style="green", justify="center")
    table.add_column("PROGRESO POR ARCHIVO", style="yellow")
    table.add_column("ESTADO", justify="center")

    for nid, info in nodos_activos.items():
        prog_detalles = []
        # Asumimos SEEDER si todos los archivos están al 100%
        estado = "[bold green]SEEDER[/bold green]"
        
        for arc, p in info["progreso"].items():
            prog_detalles.append(f"{arc}: {p}%")
            if p < 100:
                estado = "[bold blue]LEECHER[/bold blue]"
        
        prog_str = "\n".join(prog_detalles) if prog_detalles else "Conectado"
        
        table.add_row(
            nid, 
            info["ip_privada"], 
            prog_str, 
            estado
        )
    
    console.print(table)

def manejar_nodo(conn, addr):
    try:
        # Aumentamos un poco el buffer por si hay muchos archivos
        data = conn.recv(16384).decode("utf-8")
        if not data: return
        msg = json.loads(data)
        tipo = msg.get("tipo")

        if tipo == "REGISTRO":
            ip_publica = addr[0]
            # Extraemos la IP local que envía el nodo
            ip_privada = msg.get("ip_local", "N/A")
            puerto = msg.get("puerto")
            nid = f"{ip_publica}:{puerto}"
            
            nodos_activos[nid] = {
                "ip_publica": ip_publica,
                "ip_privada": ip_privada,
                "puerto": puerto,
                "progreso": msg.get("progreso", {}),
                "total_fragmentos": msg.get("total_fragmentos", {}),
                "ultima_vez": time.time()
            }
            mostrar_estado_red()

        elif tipo == "BUSQUEDA":
            archivo = msg.get("archivo")
            # Devolvemos la IP local si están en la misma red, o la pública si no
            # IMPORTANTE: Aquí enviamos 'ip_privada' porque en LAN es la única que conecta
            encontrados = []
            for info in nodos_activos.values():
                if info["progreso"].get(archivo, 0) >= 0: # Enviamos a todos los que tengan algo o estén compartiendo
                    encontrados.append({
                        "ip": info["ip_privada"], 
                        "puerto": info["puerto"],
                        "total_fragmentos": info.get("total_fragmentos", {}).get(archivo, 0)
                    })
            conn.send(json.dumps(encontrados).encode("utf-8"))

        elif tipo == "LISTAR_TODO":
            archivos = list(set(a for info in nodos_activos.values() for a in info["progreso"].keys()))
            conn.send(json.dumps(archivos).encode("utf-8"))
    except:
        pass
    finally:
        conn.close()

def iniciar_tracker():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PUERTO_TRACKER))
    s.listen()
    console.print(Panel(f"[bold green]✔ TRACKER GLOBAL LISTO EN PUERTO {PUERTO_TRACKER}[/bold green]\nEsperando conexiones de nodos..."))
    
    while True:
        c, a = s.accept()
        threading.Thread(target=manejar_nodo, args=(c, a), daemon=True).start()

if __name__ == "__main__":
    from rich.panel import Panel
    iniciar_tracker()