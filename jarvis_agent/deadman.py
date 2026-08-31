import threading
import time
import os
import signal

class DeadManSwitch:
    """
    Watchdog que monitora se o fluxo principal está avançando.
    Se o heartbeat não for atualizado dentro do timeout, kill subprocesses pendentes.
    """
    def __init__(self, timeout=60):
        self.timeout = timeout
        self._heartbeat = time.time()
        self._lock = threading.Lock()
        self._active = False
        self._pending_procs = []
        self._timer = None

    def start(self):
        self._heartbeat = time.time()
        self._active = True
        self._timer = threading.Timer(self.timeout, self._check)
        self._timer.daemon = True
        self._timer.start()

    def heartbeat(self):
        with self._lock:
            self._heartbeat = time.time()

    def stop(self):
        self._active = False
        if self._timer:
            self._timer.cancel()

    def register_proc(self, proc):
        with self._lock:
            self._pending_procs.append(proc)

    def _check(self):
        if not self._active:
            return
        with self._lock:
            elapsed = time.time() - self._heartbeat
            if elapsed >= self.timeout:
                print(f"[DeadManSwitch] TIMEOUT! ({elapsed:.1f}s > {self.timeout}s). Matando processos pendentes...")
                self._kill_pending()
                self._active = False
                return
        # Reagenda se ainda ativo
        self._timer = threading.Timer(self.timeout - elapsed, self._check)
        self._timer.daemon = True
        self._timer.start()

    def _kill_pending(self):
        for proc in self._pending_procs:
            try:
                if proc.poll() is None:
                    print(f"[DeadManSwitch] Matando PID {proc.pid}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
            except Exception as e:
                print(f"[DeadManSwitch] Erro ao matar processo: {e}")
        self._pending_procs.clear()

    @property
    def timed_out(self):
        with self._lock:
            return (time.time() - self._heartbeat) >= self.timeout

# Singleton global
deadman = DeadManSwitch(timeout=60)
