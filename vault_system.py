"""
Sistema de Cofre Encriptado — vault_system.py
==============================================
Encripta pastas inteiras num ficheiro .vault ilegível.
Só abre após autenticação válida.

Como funciona:
  1. Admin seleciona pasta → sistema comprime + encripta tudo num .vault
  2. A pasta original é apagada (só o .vault fica)
  3. Cliente faz login → sistema desencripta para pasta temporária
  4. Cliente usa os ficheiros normalmente
  5. Ao fechar → pasta temporária é apagada completamente (shred)

Instalar dependência:
    pip install cryptography

Uso (admin — criar cofre):
    python vault_system.py --criar "C:/minha/pasta"

Uso (cliente — abrir cofre):
    python vault_system.py --abrir "C:/cofre.vault"
"""

import os
import sys
import zipfile
import shutil
import tempfile
import threading
import time
import argparse
import base64
import hashlib
from pathlib import Path

# ── Encriptação ──────────────────────────────
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ── Importar autenticação ────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────
# CHAVE MESTRA — muda para algo secreto teu!
# Esta chave é usada para encriptar os cofres.
# Guarda-a em segurança — sem ela não abres os ficheiros.
# ──────────────────────────────────────────────
CHAVE_MESTRA = "muda-esta-chave-para-algo-secreto-e-longo-2024!"


def _derivar_chave(chave_mestra: str, salt: bytes) -> bytes:
    """Deriva uma chave Fernet a partir da chave mestra + salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    chave_bytes = kdf.derive(chave_mestra.encode())
    return base64.urlsafe_b64encode(chave_bytes)


def criar_cofre(pasta_origem: str, destino: str = None,
                apagar_original: bool = True) -> str:
    """
    Encripta uma pasta inteira num ficheiro .vault.

    pasta_origem   — pasta que queres encriptar
    destino        — caminho do .vault (opcional; por defeito ao lado da pasta)
    apagar_original — se True, apaga a pasta original após encriptar

    Retorna o caminho do ficheiro .vault criado.
    """
    pasta_origem = os.path.normpath(pasta_origem)

    if not os.path.isdir(pasta_origem):
        raise ValueError(f"Pasta não encontrada: {pasta_origem}")

    nome = os.path.basename(pasta_origem)

    if destino is None:
        pai = os.path.dirname(pasta_origem)
        destino = os.path.join(pai, f"{nome}.vault")

    print(f"[Cofre] A encriptar: {pasta_origem}")
    print(f"[Cofre] Destino: {destino}")

    # 1. Comprimir pasta para ZIP em memória
    zip_tmp = destino + ".tmp.zip"
    try:
        with zipfile.ZipFile(zip_tmp, "w",
                             compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as zf:
            for raiz, dirs, ficheiros in os.walk(pasta_origem):
                for ficheiro in ficheiros:
                    caminho_abs  = os.path.join(raiz, ficheiro)
                    caminho_rel  = os.path.relpath(caminho_abs, pasta_origem)
                    print(f"  + {caminho_rel}")
                    zf.write(caminho_abs, caminho_rel)

        print(f"[Cofre] ZIP criado ({os.path.getsize(zip_tmp):,} bytes)")

        # 2. Encriptar o ZIP
        salt = os.urandom(16)
        chave = _derivar_chave(CHAVE_MESTRA, salt)
        fernet = Fernet(chave)

        with open(zip_tmp, "rb") as f:
            dados_zip = f.read()

        dados_encriptados = fernet.encrypt(dados_zip)

        # 3. Guardar: [4 bytes magic] + [16 bytes salt] + [dados encriptados]
        magic = b"VALT"
        with open(destino, "wb") as f:
            f.write(magic)
            f.write(salt)
            f.write(dados_encriptados)

        print(f"[Cofre] Cofre criado: {destino} ({os.path.getsize(destino):,} bytes)")

    finally:
        if os.path.exists(zip_tmp):
            os.remove(zip_tmp)

    # 4. Apagar pasta original (com sobrescrita segura dos ficheiros)
    if apagar_original:
        print(f"[Cofre] A apagar pasta original...")
        _apagar_seguro(pasta_origem)
        print(f"[Cofre] Pasta original apagada.")

    return destino


def abrir_cofre(caminho_vault: str, pasta_destino: str = None) -> str:
    """
    Desencripta um ficheiro .vault para uma pasta temporária.

    Retorna o caminho da pasta temporária com os ficheiros.
    Chama fechar_cofre(pasta_temp) quando terminares.
    """
    if not os.path.exists(caminho_vault):
        raise FileNotFoundError(f"Cofre não encontrado: {caminho_vault}")

    with open(caminho_vault, "rb") as f:
        magic = f.read(4)
        if magic != b"VALT":
            raise ValueError("Ficheiro inválido — não é um cofre .vault deste sistema.")
        salt   = f.read(16)
        dados_enc = f.read()

    chave  = _derivar_chave(CHAVE_MESTRA, salt)
    fernet = Fernet(chave)

    try:
        dados_zip = fernet.decrypt(dados_enc)
    except Exception:
        raise ValueError("Chave mestra incorreta — não foi possível desencriptar.")

    # Descomprime para pasta temporária
    if pasta_destino is None:
        nome = Path(caminho_vault).stem
        pasta_destino = tempfile.mkdtemp(prefix=f"vault_{nome}_")

    zip_tmp = pasta_destino + "_tmp.zip"
    try:
        with open(zip_tmp, "wb") as f:
            f.write(dados_zip)

        with zipfile.ZipFile(zip_tmp, "r") as zf:
            zf.extractall(pasta_destino)
    finally:
        if os.path.exists(zip_tmp):
            os.remove(zip_tmp)

    print(f"[Cofre] Aberto em: {pasta_destino}")
    return pasta_destino


def fechar_cofre(pasta_temp: str):
    """Apaga completamente a pasta temporária com os ficheiros desencriptados."""
    if pasta_temp and os.path.exists(pasta_temp):
        print(f"[Cofre] A fechar e limpar: {pasta_temp}")
        _apagar_seguro(pasta_temp)
        print("[Cofre] Fechado e limpo.")


def _apagar_seguro(caminho: str):
    """
    Apaga ficheiros sobrescrevendo com zeros antes de eliminar.
    Impede recuperação por software de recuperação de dados.
    """
    if os.path.isfile(caminho):
        tamanho = os.path.getsize(caminho)
        try:
            with open(caminho, "r+b") as f:
                f.write(b"\x00" * tamanho)
                f.flush()
        except Exception:
            pass
        os.remove(caminho)

    elif os.path.isdir(caminho):
        for raiz, dirs, ficheiros in os.walk(caminho, topdown=False):
            for ficheiro in ficheiros:
                _apagar_seguro(os.path.join(raiz, ficheiro))
            for d in dirs:
                dp = os.path.join(raiz, d)
                try:
                    os.rmdir(dp)
                except Exception:
                    pass
        try:
            shutil.rmtree(caminho, ignore_errors=True)
        except Exception:
            pass


# ══════════════════════════════════════════════
#  USO EM LINHA DE COMANDOS
# ══════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de Cofre Encriptado")
    grupo  = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--criar", metavar="PASTA",
                       help="Encripta uma pasta num cofre .vault")
    grupo.add_argument("--abrir", metavar="VAULT",
                       help="Abre um cofre (apenas para teste — usa o vault_guard.py)")
    parser.add_argument("--destino", metavar="CAMINHO",
                        help="Caminho de destino (opcional)")
    parser.add_argument("--manter-original", action="store_true",
                        help="Não apaga a pasta original após criar o cofre")

    args = parser.parse_args()

    if args.criar:
        try:
            vault = criar_cofre(
                args.criar,
                destino=args.destino,
                apagar_original=not args.manter_original,
            )
            print(f"\n✅ Cofre criado: {vault}")
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            sys.exit(1)

    elif args.abrir:
        try:
            pasta = abrir_cofre(args.abrir, pasta_destino=args.destino)
            print(f"\n✅ Cofre aberto em: {pasta}")
            input("\nPrime ENTER para fechar e apagar a pasta temporária...")
            fechar_cofre(pasta)
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            sys.exit(1)
