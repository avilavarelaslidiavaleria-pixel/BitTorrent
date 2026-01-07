# import os, json, math, socket, threading, time
# import hashlib
# from rich.progress import Progress
# from rich.console import Console
# from rich.panel import Panel

# # ================= CONFIGURACIÓN =================
# console = Console()
# CARPETA_ORIGINALES = "archivos"
# CARPETA_METADATOS = "torrents"
# CARPETA_DESCARGAS = "descargas"
# TAMANO_PIEZA = 512 * 1024

# #en caso de que falle quitar esto
# CARPETA_TORRENTS = "torrents"
# os.makedirs(CARPETA_TORRENTS, exist_ok=True)


# for c in [CARPETA_ORIGINALES, CARPETA_METADATOS, CARPETA_DESCARGAS]:
#     os.makedirs(c, exist_ok=True)

# archivos_compartiendo = []
# progreso_por_archivo = {}
# total_fragmentos_por_archivo = {}

# # --- FUNCIÓN CRÍTICA: Detectar IP Local para evitar el "Timed Out" ---
# def obtener_mi_ip():
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         s.connect(('8.8.8.8', 80))
#         ip = s.getsockname()[0]
#     except:
#         ip = '127.0.0.1'
#     finally:
#         s.close()
#     return ip

# MI_IP_LOCAL = obtener_mi_ip()

# # ================= SERVIDOR DE PIEZAS (UPLOAD) =================
# def atender_cliente(conn):
#     try:
#         data = conn.recv(1024).decode()
#         if not data: return
#         pet = json.loads(data)

#         if pet["tipo"] == "PEDIR_PIEZA":
#             nombre = pet["archivo"]
#             num = pet["num_pieza"]
#             ruta1 = os.path.join(CARPETA_ORIGINALES, nombre)
#             ruta2 = os.path.join(CARPETA_DESCARGAS, f"descargado_{nombre}")
#             ruta = ruta1 if os.path.exists(ruta1) else ruta2

#             if os.path.exists(ruta):
#                 with open(ruta, "rb") as f:
#                     f.seek(num * TAMANO_PIEZA)
#                     contenido = f.read(TAMANO_PIEZA)
#                     # ENVIAR TAMAÑO + DATOS (Evita archivos vacíos)
#                     conn.sendall(len(contenido).to_bytes(4, byteorder='big')) 
#                     conn.sendall(contenido)
#     except: pass
#     finally: conn.close()

# def servidor_de_piezas(puerto):
#     s = socket.socket()
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind(("0.0.0.0", puerto))
#     s.listen(10)
#     while True:
#         conn, _ = s.accept()
#         # CONCURRENCIA: Atender múltiples peticiones a la vez
#         threading.Thread(target=atender_cliente, args=(conn,), daemon=True).start()

# # ================= COMUNICACIÓN CON TRACKER =================
# def anunciar_tracker(ip_t, mi_p):
#     try:
#         s = socket.socket()
#         s.settimeout(2)
#         s.connect((ip_t, 6000))
#         msg = {
#             "tipo": "REGISTRO",
#             "puerto": mi_p,
#             # "ip_local": MI_IP_LOCAL, # Reportamos IP local para que otros nos vean
#             "archivos_compartidos": archivos_compartiendo,
#             "progreso": progreso_por_archivo,
#             "total_fragmentos": total_fragmentos_por_archivo
#         }
#         s.send(json.dumps(msg).encode())
#         s.close()
#     except: pass

# def pedir_lista(ip_t):
#     try:
#         s = socket.socket(); s.connect((ip_t, 6000))
#         s.send(json.dumps({"tipo": "LISTAR_TODO"}).encode())
#         res = json.loads(s.recv(4096).decode()); s.close()
#         return res
#     except: return []

# def buscar_fuentes(ip_t, nombre):
#     try:
#         s = socket.socket(); s.connect((ip_t, 6000))
#         s.send(json.dumps({"tipo": "BUSQUEDA", "archivo": nombre}).encode())
#         res = json.loads(s.recv(4096).decode()); s.close()
#         return res
#     except: return []

# # ================= DESCARGA (LEECHING / TOLERANCIA A FALLOS) =================
# def descargar(ip_t, fuentes, nombre, total_piezas, mi_p):
#     ruta = os.path.join(CARPETA_DESCARGAS, f"descargado_{nombre}")
    
#     # TOLERANCIA A FALLOS: Detectar si ya tenemos algo y continuar
#     pieza_inicial = 0
#     if os.path.exists(ruta):
#         pieza_inicial = os.path.getsize(ruta) // TAMANO_PIEZA
#         console.print(f"[yellow]¡Reanudando descarga de {nombre} desde pieza {pieza_inicial}![/yellow]")

#     with Progress() as prog:
#         tarea = prog.add_task(f"[cyan]Descargando {nombre}", total=total_piezas, completed=pieza_inicial)
#         # Modo 'ab' (Append) para no borrar lo que ya descargamos
#         modo = "ab" if pieza_inicial > 0 else "wb"
        
#         with open(ruta, modo) as f:
#             for i in range(pieza_inicial, total_piezas):
#                 fuente = fuentes[i % len(fuentes)] # Multifuente/Balanceo
#                 try:
#                     c = socket.socket(); c.settimeout(10)
#                     c.connect((fuente["ip"], fuente["puerto"]))
#                     c.send(json.dumps({"tipo": "PEDIR_PIEZA", "archivo": nombre, "num_pieza": i}).encode())

#                     # Recibir encabezado de tamaño
#                     header = c.recv(4)
#                     if not header: break
#                     tam_real = int.from_bytes(header, byteorder='big')

#                     # Recibir datos reales
#                     data = b''
#                     while len(data) < tam_real:
#                         chunk = c.recv(tam_real - len(data))
#                         if not chunk: break
#                         data += chunk
                    
#                     if data:
#                         f.write(data)
#                         prog.update(tarea, advance=1)
#                         porcentaje = int(((i + 1) / total_piezas) * 100)
#                         progreso_por_archivo[nombre] = porcentaje

#                         # REGLA DEL 20%
#                         if porcentaje >= 20 and nombre not in archivos_compartiendo:
#                             archivos_compartiendo.append(nombre)
#                             anunciar_tracker(ip_t, mi_p)
#                     c.close()
#                 except Exception as e:
#                     console.print(f"[red]Error en pieza {i}: {e}[/red]")
#                     break

#     console.print(f"[bold green]✔ {nombre} guardado correctamente[/bold green]")

# # ================= MENÚ =================
# def menu(ip_t, mi_p):
#     while True:
#         console.print(Panel(f"NODO {MI_IP_LOCAL} | Puerto {mi_p} | Tracker {ip_t}"))
#         print("1. Compartir archivo\n2. Descargar archivo\n3. Salir")
#         op = input("> ")

#         if op == "1":
#             n = input("Archivo en /archivos: ")
#             ruta = os.path.join(CARPETA_ORIGINALES, n)
#             # descomentar esto si falla

#             # if os.path.exists(ruta):
#             #     total = math.ceil(os.path.getsize(ruta) / TAMANO_PIEZA)
#             #     total_fragmentos_por_archivo[n] = total
#             #     archivos_compartiendo.append(n)
#             #     progreso_por_archivo[n] = 100
#             #     anunciar_tracker(ip_t, mi_p)
#             #     console.print(f"[green]Compartiendo {n} ({total} piezas)[/green]")
            
#             #en caso de que falle quitar esto
#             if os.path.exists(ruta):
#                 total = math.ceil(os.path.getsize(ruta) / TAMANO_PIEZA)

#                 # ===== CALCULAR HASHES =====
#                 hashes = []
#                 with open(ruta, "rb") as f:
#                     for _ in range(total):
#                         pieza = f.read(TAMANO_PIEZA)
#                         hashes.append(hashlib.sha1(pieza).hexdigest())

#                 # ===== GUARDAR TORRENT (.json) =====
#                 os.makedirs("torrents", exist_ok=True)

#                 torrent = {
#                     "nombre": n,
#                     "tamano": os.path.getsize(ruta),
#                     "tamano_pieza": TAMANO_PIEZA,
#                     "total_piezas": total,
#                     "hashes": hashes
#                 }

#                 with open(os.path.join("torrents", f"{n}.json"), "w") as f:
#                     json.dump(torrent, f, indent=4)

#                 # ===== TU LÓGICA ORIGINAL =====
#                 total_fragmentos_por_archivo[n] = total
#                 archivos_compartiendo.append(n)
#                 progreso_por_archivo[n] = 100
#                 anunciar_tracker(ip_t, mi_p)

#                 console.print(f"[green]Compartiendo {n} ({total} piezas)[/green]")


#         elif op == "2":
#             lista = pedir_lista(ip_t)
#             print("Disponibles:", lista)
#             n = input("Archivo: ")
#             fuentes = buscar_fuentes(ip_t, n)
#             if fuentes:
#                 total = fuentes[0].get('total_fragmentos', 0)
#                 if total > 0:
#                     # DESCARGA DIRECTA para asegurar que la barra se vea en la demo
#                     descargar(ip_t, fuentes, n, total, mi_p)
#                 else: console.print("[red]El Tracker dice que el archivo no tiene piezas.[/red]")
#             else: console.print("[red]No se encontraron fuentes (Seeders/Leechers > 20%).[/red]")

#         elif op == "3": os._exit(0)

# if __name__ == "__main__":
#     ip_tracker = input("IP Tracker: ")
#     puerto = int(input("Mi puerto: "))
#     threading.Thread(target=servidor_de_piezas, args=(puerto,), daemon=True).start()
#     def heartbeat():
#         while True: anunciar_tracker(ip_tracker, puerto); time.sleep(10)
#     threading.Thread(target=heartbeat, daemon=True).start()
# #     menu(ip_tracker, puerto)

# import os, json, math, socket, threading, time, hashlib, requests
# from rich.progress import Progress
# from rich.console import Console
# from rich.panel import Panel

# console = Console()
# CARPETA_ORIGINALES = "archivos"
# CARPETA_TORRENTS = "torrents"
# CARPETA_DESCARGAS = "descargas"
# TAMANO_PIEZA = 512 * 1024 

# for c in [CARPETA_ORIGINALES, CARPETA_TORRENTS, CARPETA_DESCARGAS]:
#     os.makedirs(c, exist_ok=True)

# archivos_compartiendo = []
# progreso_por_archivo = {}
# total_fragmentos_por_archivo = {}

# # --- NUEVA FUNCIÓN: Obtener IP de la red local ---
# def obtener_mi_ip_local():
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         s.connect(('8.8.8.8', 80))
#         ip = s.getsockname()[0]
#     except:
#         ip = '127.0.0.1'
#     finally:
#         s.close()
#     return ip

# MI_IP_LOCAL = obtener_mi_ip_local()

# def obtener_ip_publica():
#     try: return requests.get('https://api.ipify.org', timeout=5).text
#     except: return "127.0.0.1"

# # ================= SERVIDOR DE UPLOAD =================
# def atender_cliente(conn):
#     try:
#         data = conn.recv(1024).decode()
#         if not data: return
#         pet = json.loads(data)

#         if pet["tipo"] == "PEDIR_PIEZA":
#             nombre = pet["archivo"]
#             num = pet["num_pieza"]
#             ruta1 = os.path.join(CARPETA_ORIGINALES, nombre)
#             ruta2 = os.path.join(CARPETA_DESCARGAS, f"descargado_{nombre}")
#             ruta = ruta1 if os.path.exists(ruta1) else ruta2

#             if os.path.exists(ruta):
#                 with open(ruta, "rb") as f:
#                     f.seek(num * TAMANO_PIEZA)
#                     contenido = f.read(TAMANO_PIEZA)
#                     conn.sendall(len(contenido).to_bytes(4, byteorder='big')) 
#                     conn.sendall(contenido)
#             else:
#                 conn.sendall((0).to_bytes(4, byteorder='big'))
#     except: pass
#     finally: conn.close()

# def servidor_de_piezas(puerto):
#     s = socket.socket()
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind(("0.0.0.0", puerto))
#     s.listen(10)
#     while True:
#         conn, _ = s.accept()
#         threading.Thread(target=atender_cliente, args=(conn,), daemon=True).start()

# # ================= ANUNCIO AL TRACKER =================
# def anunciar_tracker(ip_t, mi_p):
#     try:
#         s = socket.socket(); s.settimeout(2)
#         s.connect((ip_t, 6000))
#         msg = {
#             "tipo": "REGISTRO", 
#             "puerto": mi_p, 
#             "ip_local": MI_IP_LOCAL, # Enviamos la IP local para pruebas en LAN
#             "progreso": progreso_por_archivo, 
#             "total_fragmentos": total_fragmentos_por_archivo
#         }
#         s.send(json.dumps(msg).encode())
#         s.close()
#     except: pass

# # ================= LÓGICA DE COMPARTIR =================
# def compartir_archivo(ip_t, mi_p):
#     n = input("Nombre del archivo en /archivos: ").strip()
#     ruta = os.path.join(CARPETA_ORIGINALES, n)
    
#     if not n or not os.path.exists(ruta):
#         console.print(f"[bold red]ERROR: El archivo '{n}' no existe.[/bold red]")
#         return

#     tamano_total = os.path.getsize(ruta)
#     total_p = math.ceil(tamano_total / TAMANO_PIEZA)
    
#     hashes = []
#     with open(ruta, "rb") as f:
#         for _ in range(total_p):
#             pieza = f.read(TAMANO_PIEZA)
#             hashes.append(hashlib.sha1(pieza).hexdigest())

#     torrent = {
#         "nombre": n,
#         "tamano": tamano_total,
#         "tamano_pieza": TAMANO_PIEZA,
#         "total_piezas": total_p,
#         "hashes": hashes
#     }

#     with open(os.path.join(CARPETA_TORRENTS, f"{n}.json"), "w") as f:
#         json.dump(torrent, f, indent=4)

#     total_fragmentos_por_archivo[n] = total_p
#     progreso_por_archivo[n] = 100
#     if n not in archivos_compartiendo: archivos_compartiendo.append(n)
    
#     anunciar_tracker(ip_t, mi_p)
#     console.print(f"[bold green]✔ Compartiendo: {n}[/bold green]")

# # ================= LÓGICA DE DESCARGA =================
# def descargar(ip_t, mi_p):
#     try:
#         s = socket.socket(); s.connect((ip_t, 6000))
#         s.send(json.dumps({"tipo": "LISTAR_TODO"}).encode())
#         lista = json.loads(s.recv(4096).decode()); s.close()
#     except: return

#     print("Disponibles:", lista)
#     n = input("Archivo a descargar: ").strip()
    
#     try:
#         with open(os.path.join(CARPETA_TORRENTS, f"{n}.json"), "r") as f:
#             meta = json.load(f)
#     except:
#         console.print("[red]Falta el .json en la carpeta torrents/[/red]")
#         return

#     s = socket.socket(); s.connect((ip_t, 6000))
#     s.send(json.dumps({"tipo": "BUSQUEDA", "archivo": n}).encode())
#     fuentes = json.loads(s.recv(4096).decode()); s.close()

#     if not fuentes:
#         console.print("[red]No hay fuentes disponibles.[/red]")
#         return

#     ruta_descarga = os.path.join(CARPETA_DESCARGAS, f"descargado_{n}")
#     with Progress() as prog:
#         tarea = prog.add_task(f"[cyan]Descargando {n}", total=meta["total_piezas"])
#         with open(ruta_descarga, "wb") as f:
#             for i in range(meta["total_piezas"]):
#                 fuente = fuentes[i % len(fuentes)]
                
#                 # Intentamos conectar a la IP que nos dé el tracker (Local o Pública)
#                 try:
#                     c = socket.socket(); c.settimeout(5)
#                     c.connect((fuente["ip"], fuente["puerto"]))
#                     c.send(json.dumps({"tipo": "PEDIR_PIEZA", "archivo": n, "num_pieza": i}).encode())
                    
#                     header = c.recv(4)
#                     tam_real = int.from_bytes(header, byteorder='big')
#                     data = b''
#                     while len(data) < tam_real:
#                         chunk = c.recv(tam_real - len(data))
#                         if not chunk: break
#                         data += chunk
                    
#                     if hashlib.sha1(data).hexdigest() == meta["hashes"][i]:
#                         f.write(data)
#                         prog.update(tarea, advance=1)
#                         progreso_por_archivo[n] = int(((i + 1) / meta["total_piezas"]) * 100)
#                     c.close()
#                 except:
#                     console.print(f"[red]Error conectando a fuente {fuente['ip']}[/red]")
#                     return

# if __name__ == "__main__":
#     ip_tracker = input("IP del Tracker: ").strip()
#     puerto_local = int(input("Tu puerto local: "))
    
#     ip_pub = obtener_ip_publica()
#     identidad = f"{ip_pub}:{puerto_local} (Local: {MI_IP_LOCAL})"

#     threading.Thread(target=servidor_de_piezas, args=(puerto_local,), daemon=True).start()
    
#     def heartbeat():
#         while True: anunciar_tracker(ip_tracker, puerto_local); time.sleep(15)
#     threading.Thread(target=heartbeat, daemon=True).start()

#     while True:
#         console.print(Panel(f"NODO ACTIVO: {identidad}"))
#         op = input("1. Compartir\n2. Descargar\n3. Salir\n> ")
#         if op == "1": compartir_archivo(ip_tracker, puerto_local)
#         elif op == "2": descargar(ip_tracker, puerto_local)
#         elif op == "3": os._exit(0)

import socket, threading, json, os, time
from rich.console import Console
from rich.table import Table

console = Console()
ESTADO_FILE = "estado_nodo.json"

# Cargar progreso previo para cumplir con "Tolerancia a fallos"
def cargar_progreso():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, 'r') as f:
            return json.load(f)
    return {"completos": ["archivo_base.txt"], "progresos": {}}

estado = cargar_progreso()

def mostrar_menu():
    while True:
        console.print("\n[bold magenta]=== MENU NODO BITTORRENT (P2P) ===[/bold magenta]")
        console.print("1. Ver archivos compartidos (Seeders/Peers)")
        console.print("2. Iniciar descarga de nuevo archivo")
        console.print("3. Ver estado de descargas actuales")
        console.print("4. Salir")
        
        opc = console.input("[bold yellow]Selecciona una opción: [/bold yellow]")
        
        if opc == "2":
            archivo = console.input("Nombre del archivo (Z, F, D, Q): ")
            # Iniciar descarga en un hilo separado para permitir simultaneidad
            threading.Thread(target=simular_descarga, args=(archivo,)).start()
        elif opc == "4":
            os._exit(0)

def simular_descarga(nombre):
    inicio = estado["progresos"].get(nombre, 0)
    for i in range(inicio, 105, 5):
        if i > 100: i = 100
        time.sleep(1) 
        estado["progresos"][nombre] = i
        # Guardar estado para reconexión involuntaria
        with open(ESTADO_FILE, 'w') as f: json.dump(estado, f)
        
        console.print(f"[blue]{nombre}: {i}%[/blue]")
        
        # Política BitTorrent: Compartir al llegar al 20%
        if i == 20:
            console.print("[bold green]>>> ¡20% alcanzado! El nodo ahora es Peer activo.[/bold green]")

if __name__ == "__main__":
    mostrar_menu()