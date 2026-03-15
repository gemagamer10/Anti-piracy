"""
Sistema Anti-Pirataria — Módulo de Autenticação v2 (CORRIGIDO)
==============================================================
BUGS CORRIGIDOS vs versão anterior:
  - _ip_bloqueado agora filtra por 24h (antes bloqueava para sempre)
  - DADOS_FILE usa caminho absoluto (antes podia perder-se)
  - Sessão local guardada em base64 segura (antes podia gerar chars inválidos)
  - Timeout em todas as chamadas de rede (antes podia ficar suspenso)
"""

import hashlib
import platform
import uuid
import socket
import requests
import json
import os
import base64
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────────
# CONFIGURAÇÃO — substitui com os teus dados
# ──────────────────────────────────────────────
SUPABASE_URL = "https://SEU_PROJETO.supabase.co"
SUPABASE_KEY = "SUA_CHAVE_ANON_PUBLICA"

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sessao_local")
MAX_FALHAS   = 5
TIMEOUT      = 8   # segundos para cada pedido de rede
# ──────────────────────────────────────────────


def _headers(token: str = None) -> dict:
    h = {
        "apikey":       SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer":       "return=minimal",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ══════════════════════════════════════════════
#  INFORMAÇÃO DO DISPOSITIVO
# ══════════════════════════════════════════════
def obter_mac_address() -> str:
    mac_int = uuid.getnode()
    return ":".join([f"{(mac_int >> (i * 8)) & 0xFF:02X}" for i in range(5, -1, -1)])


def obter_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "desconhecido"


def obter_sistema() -> str:
    try:
        s = platform.system()
        if s == "Windows":
            return f"Windows {platform.release()} ({platform.version()[:20]})"
        elif s == "Darwin":
            return f"macOS {platform.mac_ver()[0]}"
        return f"{s} {platform.release()}"
    except Exception:
        return platform.system() or "desconhecido"


def obter_ip_publico() -> str:
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=TIMEOUT)
        return r.json().get("ip", "desconhecido")
    except Exception:
        return "desconhecido"


def gerar_id_dispositivo() -> str:
    partes = [
        hex(uuid.getnode()),
        platform.node(),
        platform.processor(),
        platform.architecture()[0],
        platform.system(),
    ]
    return hashlib.sha256("-".join(partes).encode()).hexdigest()


def recolher_info_dispositivo() -> dict:
    return {
        "device_id":   gerar_id_dispositivo(),
        "mac_address": obter_mac_address(),
        "hostname":    obter_hostname(),
        "sistema":     obter_sistema(),
        "ip":          obter_ip_publico(),
        "visto_em":    datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════
#  ANTI-BRUTE-FORCE  (BUG CORRIGIDO: filtro por 24h)
# ══════════════════════════════════════════════
def _registar_falha(ip: str, email: str):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/login_falhas",
            headers=_headers(),
            json={"ip": ip, "email": email,
                  "criado_em": datetime.now(timezone.utc).isoformat()},
            timeout=TIMEOUT,
        )
    except Exception:
        pass  # falha silenciosa — não bloqueia o login


def _ip_bloqueado(ip: str) -> bool:
    # CORRIGIDO: filtra apenas falhas das últimas 24 horas
    desde = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/login_falhas"
            f"?ip=eq.{ip}&criado_em=gte.{desde}&select=id",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return resp.status_code == 200 and len(resp.json()) >= MAX_FALHAS
    except Exception:
        return False  # em caso de erro de rede, não bloquear


# ══════════════════════════════════════════════
#  SESSÃO LOCAL  (BUG CORRIGIDO: usa base64)
# ══════════════════════════════════════════════
def _guardar_sessao(dados: dict, device_id: str):
    """Guarda sessão encriptada com XOR + base64 (evita chars inválidos)."""
    conteudo = json.dumps(dados).encode("utf-8")
    chave    = (device_id[:32] * 10).encode("utf-8")
    xor      = bytes(b ^ chave[i % len(chave)] for i, b in enumerate(conteudo))
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        f.write(base64.b64encode(xor).decode("ascii"))


def _ler_sessao(device_id: str) -> dict | None:
    """Lê e desencripta a sessão local."""
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            xor  = base64.b64decode(f.read())
        chave    = (device_id[:32] * 10).encode("utf-8")
        conteudo = bytes(b ^ chave[i % len(chave)] for i, b in enumerate(xor))
        return json.loads(conteudo.decode("utf-8"))
    except Exception:
        return None


# ══════════════════════════════════════════════
#  LOGIN PRINCIPAL
# ══════════════════════════════════════════════
def login(email: str, password: str) -> tuple[bool, str]:
    """Autentica o utilizador. Retorna (sucesso, mensagem)."""

    info      = recolher_info_dispositivo()
    ip        = info["ip"]
    device_id = info["device_id"]
    agora     = info["visto_em"]

    # 1. Verificar bloqueio de IP (últimas 24h)
    if _ip_bloqueado(ip):
        return False, (
            f"🚫 IP bloqueado: {ip}\n"
            "Demasiadas tentativas falhadas nas últimas 24h.\n"
            "Contacta o administrador."
        )

    # 2. Autenticar no Supabase
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        return False, "❌ Sem ligação à internet. Verifica a tua ligação."
    except requests.exceptions.Timeout:
        return False, "❌ Tempo de espera esgotado. Tenta novamente."

    if resp.status_code != 200:
        _registar_falha(ip, email)
        return False, "❌ Email ou password incorretos."

    dados   = resp.json()
    token   = dados["access_token"]
    user_id = dados["user"]["id"]
    hdrs    = _headers(token)

    # 3. Verificar/Registar dispositivo
    try:
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/dispositivos?user_id=eq.{user_id}",
            headers=hdrs, timeout=TIMEOUT,
        )
        dispositivos = check.json() if check.status_code == 200 else []
    except Exception:
        return False, "❌ Erro ao verificar dispositivo. Tenta novamente."

    if len(dispositivos) == 0:
        # Primeiro login — registar este PC
        requests.post(
            f"{SUPABASE_URL}/rest/v1/dispositivos",
            headers=hdrs,
            json={"user_id": user_id, **info},
            timeout=TIMEOUT,
        )
    else:
        device_registado = dispositivos[0]["device_id"]
        if device_registado != device_id:
            _registar_falha(ip, email)
            disp = dispositivos[0]
            return False, (
                "🔒 Licença bloqueada!\n\n"
                "Esta conta já está associada a outro PC:\n"
                f"  🖥️  {disp.get('hostname', '?')}\n"
                f"  💻  {disp.get('sistema', '?')}\n"
                f"  🌍  {disp.get('ip', '?')}\n\n"
                "Contacta o administrador para transferir a licença."
            )
        else:
            # Mesmo PC — atualizar info
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/dispositivos?user_id=eq.{user_id}",
                headers=hdrs,
                json={"ip": ip, "visto_em": agora,
                      "sistema": info["sistema"], "hostname": info["hostname"]},
                timeout=TIMEOUT,
            )

    # 4. Token de sessão único (invalida sessões anteriores)
    session_token = hashlib.sha256(f"{user_id}-{device_id}-{agora}".encode()).hexdigest()

    payload = {"session_token": session_token, "device_id": device_id,
               "ip": ip, "criado_em": agora}
    try:
        check_s = requests.get(
            f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{user_id}",
            headers=hdrs, timeout=TIMEOUT,
        )
        if check_s.status_code == 200 and len(check_s.json()) > 0:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{user_id}",
                headers=hdrs, json=payload, timeout=TIMEOUT,
            )
        else:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/sessoes",
                headers=hdrs, json={"user_id": user_id, **payload}, timeout=TIMEOUT,
            )
    except Exception:
        pass  # sessão no servidor falhou mas login local prossegue

    # 5. Guardar sessão local
    _guardar_sessao({"user_id": user_id, "session_token": session_token,
                     "token": token, "device_id": device_id}, device_id)

    return True, "Login efetuado com sucesso! Bem-vindo."


# ══════════════════════════════════════════════
#  VERIFICAÇÃO DE SESSÃO
# ══════════════════════════════════════════════
def verificar_sessao() -> tuple[bool, str]:
    """Verifica se a sessão local ainda é válida."""
    if not os.path.exists(SESSION_FILE):
        return False, "Nenhuma sessão ativa."

    device_id_local = gerar_id_dispositivo()
    dados = _ler_sessao(device_id_local)

    if not dados:
        try: os.remove(SESSION_FILE)
        except: pass
        return False, "Sessão corrompida. Faz login novamente."

    if dados.get("device_id") != device_id_local:
        try: os.remove(SESSION_FILE)
        except: pass
        return False, "🚫 Sessão inválida neste dispositivo."

    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{dados['user_id']}",
            headers=_headers(dados["token"]),
            timeout=TIMEOUT,
        )
        if resp.status_code != 200 or not resp.json():
            return False, "Sessão expirada. Faz login novamente."

        if resp.json()[0]["session_token"] != dados["session_token"]:
            try: os.remove(SESSION_FILE)
            except: pass
            return False, (
                "⚠️ Sessão encerrada remotamente.\n"
                "Pode ter sido pelo administrador ou\n"
                "detetado login noutro dispositivo."
            )
        return True, "Sessão válida."
    except Exception:
        return False, "Sem ligação. Verifica a internet."


def logout():
    """Encerra a sessão local."""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass
