"""
Motor de Cofre Encriptado
=========================
Encripta uma pasta inteira num único ficheiro .vault (AES-256).
A chave de desencriptação fica guardada no servidor Supabase —
sem login válido, o ficheiro .vault é completamente ilegível.

Fluxo:
  PROTEGER:   pasta/ → pasta.vault  (original pode ser apagado)
  ACEDER:     login OK → servidor devolve chave → desencripta para pasta temp
  FECHAR:     pasta temp é apagada automaticamente

Requer: pip install cryptography requests
"""

import os
import io
import json
import struct
import shutil
import hashlib
import tempfile
import zipfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets
import base64


# ── Constantes ───────────────────────────────
MAGIC     = b"VAULT001"   # cabeçalho de identificação
SALT_SIZE = 32
KEY_SIZE  = 32            # AES-256
NONCE_SIZE= 12


def _derivar_chave(chave_bytes: bytes, salt: bytes) -> bytes:
    """Deriva uma chave AES-256 a partir da chave do servidor + salt único."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(chave_bytes)


def encriptar_pasta(pasta_path: str, vault_path: str, chave_servidor: bytes) -> dict:
    """
    Encripta todos os ficheiros de uma pasta num ficheiro .vault.

    Args:
        pasta_path:    caminho da pasta a encriptar
        vault_path:    caminho do ficheiro .vault a criar
        chave_servidor: chave de 32 bytes obtida do servidor

    Returns:
        dict com estatísticas (n_ficheiros, tamanho_original, tamanho_vault)
    """
    pasta_path = Path(pasta_path)
    vault_path = Path(vault_path)

    if not pasta_path.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta_path}")

    # 1. Comprimir todos os ficheiros para ZIP em memória
    buf_zip = io.BytesIO()
    n_ficheiros  = 0
    tam_original = 0

    with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for ficheiro in sorted(pasta_path.rglob("*")):
            if ficheiro.is_file():
                caminho_relativo = ficheiro.relative_to(pasta_path)
                zf.write(ficheiro, caminho_relativo)
                tam_original += ficheiro.stat().st_size
                n_ficheiros  += 1

    if n_ficheiros == 0:
        raise ValueError("A pasta está vazia — nada para encriptar.")

    dados_zip = buf_zip.getvalue()

    # 2. Encriptar com AES-256-GCM
    salt  = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    chave = _derivar_chave(chave_servidor, salt)

    aesgcm     = AESGCM(chave)
    dados_enc  = aesgcm.encrypt(nonce, dados_zip, None)

    # 3. Escrever ficheiro .vault
    # Formato: MAGIC (8) | salt (32) | nonce (12) | tamanho_enc (8) | dados_enc
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    with open(vault_path, "wb") as f:
        f.write(MAGIC)
        f.write(salt)
        f.write(nonce)
        f.write(struct.pack(">Q", len(dados_enc)))
        f.write(dados_enc)

    tam_vault = vault_path.stat().st_size

    return {
        "n_ficheiros":   n_ficheiros,
        "tam_original":  tam_original,
        "tam_vault":     tam_vault,
        "vault_path":    str(vault_path),
    }


def desencriptar_vault(vault_path: str, chave_servidor: bytes) -> str:
    """
    Desencripta um ficheiro .vault para uma pasta temporária segura.

    Args:
        vault_path:     caminho do ficheiro .vault
        chave_servidor: chave de 32 bytes obtida do servidor após login

    Returns:
        caminho da pasta temporária com os ficheiros desencriptados
        (APAGAR esta pasta quando o utilizador terminar!)
    """
    vault_path = Path(vault_path)

    if not vault_path.exists():
        raise FileNotFoundError(f"Ficheiro vault não encontrado: {vault_path}")

    with open(vault_path, "rb") as f:
        # Verificar cabeçalho
        magic = f.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Ficheiro inválido ou corrompido.")

        salt       = f.read(SALT_SIZE)
        nonce      = f.read(NONCE_SIZE)
        tam_enc    = struct.unpack(">Q", f.read(8))[0]
        dados_enc  = f.read(tam_enc)

    # Desencriptar
    chave = _derivar_chave(chave_servidor, salt)
    aesgcm = AESGCM(chave)

    try:
        dados_zip = aesgcm.decrypt(nonce, dados_enc, None)
    except Exception:
        raise PermissionError(
            "Chave incorreta ou ficheiro adulterado. Acesso negado."
        )

    # Extrair ZIP para pasta temporária
    pasta_temp = tempfile.mkdtemp(prefix="vault_aberto_")

    buf_zip = io.BytesIO(dados_zip)
    with zipfile.ZipFile(buf_zip, "r") as zf:
        zf.extractall(pasta_temp)

    return pasta_temp


def limpar_pasta_temp(pasta_temp: str):
    """
    Apaga de forma segura a pasta temporária desencriptada.
    Sobrescreve os dados antes de apagar (evita recuperação).
    """
    pasta = Path(pasta_temp)
    if not pasta.exists():
        return

    # Sobrescrever cada ficheiro com zeros antes de apagar
    for f in pasta.rglob("*"):
        if f.is_file():
            try:
                tamanho = f.stat().st_size
                with open(f, "r+b") as fh:
                    fh.write(b"\x00" * tamanho)
            except Exception:
                pass

    shutil.rmtree(pasta_temp, ignore_errors=True)


def gerar_chave_vault() -> str:
    """Gera uma chave aleatória de 32 bytes em base64 para guardar no servidor."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def chave_de_string(chave_b64: str) -> bytes:
    """Converte chave base64 (vinda do servidor) para bytes."""
    return base64.urlsafe_b64decode(chave_b64.encode())
