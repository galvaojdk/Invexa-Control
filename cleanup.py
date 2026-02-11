import os
import subprocess
import re
import sys

def kill_process_on_port(port):
    print(f"--- Limpando processos na porta {port} ---")
    try:
        # Tenta encontrar PIDs na porta usando netstat
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode()
        
        # Filtra linhas "LISTENING"
        lines = [line for line in output.strip().split('\n') if "LISTENING" in line]
        
        pids = set()
        for line in lines:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 5:
                pid = parts[-1]
                if pid != "0":
                    pids.add(pid)
        
        if pids:
            for pid in pids:
                print(f"Encerrando processo zumbi PID {pid} na porta {port}...")
                subprocess.run(f"taskkill /PID {pid} /F /T", shell=True, capture_output=True)
        else:
            print(f"Nenhum processo ouvindo na porta {port}.")
            
    except subprocess.CalledProcessError:
        print(f"Porta {port} ja esta livre.")
    except Exception as e:
        print(f"Erro ao limpar porta {port}: {e}")

def kill_python_zombies():
    print(f"--- Procurando por processos Python/Uvicorn perdidos ---")
    try:
        # Tenta matar processos uvicorn e python que possam estar travados
        # No Windows, as vezes o uvicorn deixa processos filhos
        subprocess.run('taskkill /F /IM "uvicorn.exe" /T', shell=True, capture_output=True)
        # Nao matamos todos os python.exe para nao afetar outras ferramentas do usuario,
        # mas a limpeza por porta ja deve ser suficiente.
    except:
        pass

if __name__ == "__main__":
    kill_python_zombies()
    # Limpa as duas portas mais comuns para evitar conflitos com outros projetos Invexa
    kill_process_on_port(8000)
    kill_process_on_port(8001)
    print("--- Limpeza concluida ---")
