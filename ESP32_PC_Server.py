import socket
import threading
import queue
import time
import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

HOST = '0.0.0.0'  # 接收所有 IP
PORT = 8080
executor = ThreadPoolExecutor(max_workers=1)

log_fp = None

class SystemState(Enum):
    Idle = 1  
    LogUpload = 2
STATE = SystemState.Idle


def process_data(data: str, conn, addr) -> str:
    if(STATE == SystemState.Idle):
        conn.sendall((f"Processed({data})\n").encode())
        print(f"[{addr}] Replied: Processed({data})")
        return 
    elif (STATE == SystemState.LogUpload):
        global log_fp
        if log_fp:
            log_fp.write(data + "\n")
            # log_fp.flush()
        else:
            print(f"[{addr}] Logged: ERROR: Log file not open")
        return

    print(f"[{addr}] Unhandled data: {data}")

def async_process(data, conn, addr):
    try:
        process_data(data, conn, addr)
    except Exception as e:
        print(f"[!] Error processing data from {addr}: {e}")

def eventHandler(event, conn, addr):
    global log_fp, STATE
    
    if event == "LOG_UPLOAD_START":
        STATE = SystemState.LogUpload
        fname = time.strftime("log_%Y%m%d_%H%M%S.txt")
        log_fp = open(fname, "w", encoding="utf-8")
        return True

    if event == "LOG_UPLOAD_END":
        STATE = SystemState.Idle
        if log_fp:
            log_fp.close()
            log_fp = None
        return True
    
    if event == "GET_TIME":
        now = datetime.datetime.now()
        resp = now.strftime("updateTimer %Y/%m/%d %H:%M:%S")
        print(f"Get Time : {resp}")
        conn.sendall((resp + "\n").encode())
        return True
    
    return False

def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            msg = data.decode().strip()
            print(f"[{addr}] Received: {msg}")
            if(eventHandler(msg, conn, addr)): continue
            executor.submit(async_process, msg, conn, addr)

    except Exception as e:
        print(f"[!] Error from {addr}: {e}")
    finally:
        if log_fp:
            log_fp.close()
        conn.close()
        print(f"[-] Connection closed from {addr}")

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10.0)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[+] Server listening on {HOST}:{PORT}")
        while True:
            try:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                print("\n[!] Server shutting down.")
                break
            except Exception as e:
                print(f"[!] Error: {e}")

if __name__ == "__main__":
    start_server()
