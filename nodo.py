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

import os, json, math, socket, threading, time, hashlib
from rich.progress import Progress
from rich.console import Console
from rich.panel import Panel

# ================= CONFIGURACIÓN =================
console = Console()
CARPETA_ORIGINALES = "archivos"
CARPETA_METADATOS = "torrents"
CARPETA_DESCARGAS = "descargas"
TAMANO_PIEZA = 512 * 1024 

# Asegurar que existan las carpetas
for c in [CARPETA_ORIGINALES, CARPETA_METADATOS, CARPETA_DESCARGAS]:
    os.makedirs(c, exist_ok=True)

archivos_compartiendo, progreso_por_archivo, total_fragmentos_por_archivo = [], {}, {}

def obtener_mi_ip():
    """Detecta la IP de Tailscale (100.x.x.x) para Transparencia"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('100.100.100.100', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

MI_IP_LOCAL = obtener_mi_ip()

# ================= COMUNICACIÓN Y SERVIDOR =================
def anunciar_tracker(ip_t, mi_p):
    try:
        s = socket.socket(); s.settimeout(2); s.connect((ip_t, 6000))
        msg = {
            "tipo": "REGISTRO", "puerto": mi_p, "ip_local": MI_IP_LOCAL,
            "archivos_compartidos": archivos_compartiendo,
            "progreso": progreso_por_archivo,
            "total_fragmentos": total_fragmentos_por_archivo
        }
        s.send(json.dumps(msg).encode()); s.close()
    except: pass

def atender_cliente(conn):
    try:
        data = conn.recv(1024).decode()
        if not data: return
        pet = json.loads(data)
        if pet["tipo"] == "PEDIR_PIEZA":
            nombre, num = pet["archivo"], pet["num_pieza"]
            r1, r2 = os.path.join(CARPETA_ORIGINALES, nombre), os.path.join(CARPETA_DESCARGAS, f"descargado_{nombre}")
            ruta = r1 if os.path.exists(r1) else r2
            if os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    f.seek(num * TAMANO_PIEZA)
                    contenido = f.read(TAMANO_PIEZA)
                    conn.sendall(len(contenido).to_bytes(4, byteorder='big') + contenido)
    except: pass
    finally: conn.close()

def servidor_de_piezas(puerto):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", puerto))
    s.listen(10)
    while True:
        conn, _ = s.accept()
        threading.Thread(target=atender_cliente, args=(conn,), daemon=True).start()

# ================= DESCARGA Y BUSQUEDA =================
def pedir_lista(ip_t):
    try:
        s = socket.socket(); s.settimeout(2); s.connect((ip_t, 6000))
        s.send(json.dumps({"tipo": "LISTAR_TODO"}).encode())
        res = s.recv(4096).decode()
        s.close()
        return json.loads(res) if res else []
    except: return []

def buscar_fuentes(ip_t, n):
    try:
        s = socket.socket(); s.connect((ip_t, 6000))
        s.send(json.dumps({"tipo": "BUSQUEDA", "archivo": n}).encode())
        res = json.loads(s.recv(4096).decode()); s.close()
        return res
    except: return []

def descargar(ip_t, fuentes, nombre, total_piezas, mi_p):
    ruta = os.path.join(CARPETA_DESCARGAS, f"descargado_{nombre}")
    pieza_ini = os.path.getsize(ruta) // TAMANO_PIEZA if os.path.exists(ruta) else 0
    with Progress() as prog:
        t = prog.add_task(f"[cyan]Descargando {nombre}", total=total_piezas, completed=pieza_ini)
        with open(ruta, "ab" if pieza_ini > 0 else "wb") as f:
            for i in range(pieza_ini, total_piezas):
                fuente = fuentes[i % len(fuentes)]
                try:
                    c = socket.socket(); c.settimeout(5); c.connect((fuente["ip"], fuente["puerto"]))
                    c.send(json.dumps({"tipo":"PEDIR_PIEZA","archivo":nombre,"num_pieza":i}).encode())
                    tam = int.from_bytes(c.recv(4), byteorder='big')
                    data = b''
                    while len(data) < tam: data += c.recv(tam - len(data))
                    if data:
                        f.write(data); prog.update(t, advance=1)
                        progreso_por_archivo[nombre] = int(((i + 1) / total_piezas) * 100)
                        if progreso_por_archivo[nombre] >= 20 and nombre not in archivos_compartiendo:
                            archivos_compartiendo.append(nombre); anunciar_tracker(ip_t, mi_p)
                    c.close()
                except: continue
    console.print(f"[bold green]✔ {nombre} completo[/bold green]")

# ================= MENÚ CON GENERACIÓN DE JSON =================
def menu(ip_t, mi_p):
    while True:
        console.print(Panel(f"NODO {MI_IP_LOCAL} | Puerto {mi_p} | Tracker {ip_t}"))
        op = input("1. Compartir\n2. Descargar\n3. Salir\n> ")
        if op == "1":
            n = input("Archivo en /archivos: ")
            ruta = os.path.join(CARPETA_ORIGINALES, n)
            if os.path.exists(ruta):
                # ===== LÓGICA DE CREACIÓN DE JSON (TORRENT) =====
                tamano_total = os.path.getsize(ruta)
                total = math.ceil(tamano_total / TAMANO_PIEZA)
                hashes = []
                with open(ruta, "rb") as f:
                    for _ in range(total):
                        pieza = f.read(TAMANO_PIEZA)
                        hashes.append(hashlib.sha1(pieza).hexdigest())

                torrent = {
                    "nombre": n, "tamano": tamano_total, 
                    "total_piezas": total, "hashes": hashes
                }
                
                with open(os.path.join(CARPETA_METADATOS, f"{n}.json"), "w") as f:
                    json.dump(torrent, f, indent=4)
                
                # Actualizar estado local y avisar al tracker
                total_fragmentos_por_archivo[n], progreso_por_archivo[n] = total, 100
                if n not in archivos_compartiendo: archivos_compartiendo.append(n)
                anunciar_tracker(ip_t, mi_p)
                console.print(f"[bold green]✔ JSON creado en /torrents y compartiendo {n}[/bold green]")
            else: console.print("[red]No existe el archivo en /archivos[/red]")

        elif op == "2":
            lista = pedir_lista(ip_t)
            console.print(f"[bold cyan]Enjambre: {lista}[/bold cyan]")
            if lista:
                n = input("Archivo a descargar: ")
                fuentes = buscar_fuentes(ip_t, n)
                if fuentes: descargar(ip_t, fuentes, n, fuentes[0]['total_fragmentos'], mi_p)
        elif op == "3": os._exit(0)

if __name__ == "__main__":
    ip_t = input("IP Tracker: ")
    mi_p = int(input("Mi puerto: "))
    threading.Thread(target=lambda: servidor_de_piezas(mi_p), daemon=True).start()
    def heartbeat():
        while True: anunciar_tracker(ip_t, mi_p); time.sleep(5)
    threading.Thread(target=heartbeat, daemon=True).start()
    menu(ip_t, mi_p)