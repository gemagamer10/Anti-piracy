"""
Gestor de Cofres — gestor_cofres.py
=====================================
Interface gráfica para o administrador criar e gerir cofres encriptados.

Funcionalidades:
  ✅ Selecionar pasta → encriptar em .vault
  ✅ Ver todos os cofres criados
  ✅ Testar abertura de um cofre (com login)
  ✅ Criar lançador .bat para distribuir ao cliente
  ✅ Remover/eliminar cofre

Uso:
    python gestor_cofres.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import platform
import subprocess
import threading
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_system import criar_cofre, CHAVE_MESTRA

DIR_BASE   = os.path.dirname(os.path.abspath(__file__))
DADOS_FILE = os.path.join(DIR_BASE, "cofres.json")

CORES = {
    "bg":        "#0d0f18",
    "painel":    "#141720",
    "card":      "#1c2030",
    "borda":     "#252a40",
    "texto":     "#dde3f8",
    "sub":       "#6c7bb5",
    "verde":     "#3dd68c",
    "verdeBg":   "#0d2818",
    "vermelho":  "#f05454",
    "vermBg":    "#280d0d",
    "laranja":   "#f0a854",
    "azul":      "#4d7cfe",
    "azulBg":    "#0d1628",
    "branco":    "#ffffff",
}


# ── Dados ────────────────────────────────────
def carregar_cofres():
    if not os.path.exists(DADOS_FILE):
        return []
    try:
        with open(DADOS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def guardar_cofres(cofres):
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(cofres, f, indent=2, ensure_ascii=False)


def criar_lancador_vault(vault_path: str, nome: str) -> str:
    """Cria um .bat que abre o vault_guard com o cofre."""
    python     = sys.executable
    guard_path = os.path.join(DIR_BASE, "vault_guard.py")

    sistema = platform.system()
    if sistema == "Windows":
        lancador = os.path.join(DIR_BASE, f"Abrir — {nome}.bat")
        conteudo = f'@echo off\n"{python}" "{guard_path}" "{vault_path}"\n'
    else:
        lancador = os.path.join(DIR_BASE, f"Abrir_{nome}.sh")
        conteudo = f'#!/bin/bash\n"{python}" "{guard_path}" "{vault_path}"\n'

    with open(lancador, "w", encoding="utf-8") as f:
        f.write(conteudo)

    if sistema != "Windows":
        os.chmod(lancador, 0o755)

    return lancador


def formatar_tamanho(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


# ══════════════════════════════════════════════
#  DIÁLOGO DE PROGRESSO
# ══════════════════════════════════════════════
class DialogoProgresso(tk.Toplevel):
    def __init__(self, parent, titulo):
        super().__init__(parent)
        self.title(titulo)
        self.geometry("380x140")
        self.configure(bg=CORES["bg"])
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 380) // 2
        y = (self.winfo_screenheight() - 140) // 2
        self.geometry(f"380x140+{x}+{y}")

        self.lbl = tk.Label(self, text="A preparar…",
                             font=("Segoe UI", 10),
                             bg=CORES["bg"], fg=CORES["texto"])
        self.lbl.pack(pady=(28, 12))

        style = ttk.Style()
        style.configure("V.Horizontal.TProgressbar",
                        troughcolor=CORES["card"],
                        background=CORES["azul"])
        self.bar = ttk.Progressbar(self, style="V.Horizontal.TProgressbar",
                                    mode="indeterminate", length=300)
        self.bar.pack()
        self.bar.start(8)

    def set_msg(self, msg):
        self.lbl.config(text=msg)
        self.update()


# ══════════════════════════════════════════════
#  INTERFACE PRINCIPAL
# ══════════════════════════════════════════════
class GestorCofres(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔒 Gestor de Cofres Encriptados")
        self.geometry("900x580")
        self.minsize(720, 440)
        self.configure(bg=CORES["bg"])

        self.cofres = carregar_cofres()
        self._construir()
        self._atualizar()

    def _construir(self):
        # Header
        hdr = tk.Frame(self, bg=CORES["painel"], height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🔒  Gestor de Cofres Encriptados",
                 font=("Segoe UI", 14, "bold"),
                 bg=CORES["painel"], fg=CORES["texto"]).pack(
                     side="left", padx=22, pady=18)

        tk.Label(hdr, text="Pasta → cofre ilegível • Login obrigatório para abrir",
                 font=("Segoe UI", 9),
                 bg=CORES["painel"], fg=CORES["sub"]).pack(
                     side="left", pady=18)

        # Aviso de chave mestra
        aviso = tk.Frame(self, bg=CORES["vermBg"], pady=7)
        aviso.pack(fill="x", padx=0)
        tk.Label(aviso,
                 text=f"⚠️  Chave mestra atual (em vault_system.py): "
                      f"{'*' * 8}{CHAVE_MESTRA[-6:]}  —  "
                      "Guarda-a em segurança! Sem ela não abres os cofres.",
                 font=("Segoe UI", 9),
                 bg=CORES["vermBg"], fg=CORES["laranja"]).pack()

        # Barra de ações
        barra = tk.Frame(self, bg=CORES["bg"], pady=12)
        barra.pack(fill="x", padx=18)

        self._btn("➕  Nova Pasta → Cofre", CORES["azul"],
                  self.criar_cofre, barra).pack(side="left")
        self._btn("🚀  Abrir com Login", CORES["verde"],
                  self.abrir_cofre, barra).pack(side="left", padx=8)
        self._btn("📋  Criar Lançador .bat", CORES["laranja"],
                  self.criar_lancador, barra).pack(side="left")
        self._btn("🗑️  Eliminar Cofre", CORES["vermelho"],
                  self.eliminar_cofre, barra).pack(side="right")

        # Tabela
        frame_t = tk.Frame(self, bg=CORES["bg"])
        frame_t.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Treeview",
                        background=CORES["card"],
                        foreground=CORES["texto"],
                        fieldbackground=CORES["card"],
                        rowheight=36,
                        font=("Segoe UI", 10))
        style.configure("C.Treeview.Heading",
                        background=CORES["painel"],
                        foreground=CORES["sub"],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("C.Treeview",
                  background=[("selected", CORES["azul"])],
                  foreground=[("selected", CORES["branco"])])

        colunas = ("estado", "nome", "vault", "tamanho", "lancador", "criado")
        self.tree = ttk.Treeview(frame_t, columns=colunas,
                                  show="headings", style="C.Treeview")

        cfg = {
            "estado":   ("",              36),
            "nome":     ("Nome",         160),
            "vault":    ("Ficheiro .vault", 260),
            "tamanho":  ("Tamanho",       90),
            "lancador": ("Lançador .bat", 160),
            "criado":   ("Criado em",     130),
        }
        for col, (lbl, w) in cfg.items():
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w, minwidth=30)

        vsb = ttk.Scrollbar(frame_t, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.abrir_cofre())

        # Rodapé
        rod = tk.Frame(self, bg=CORES["painel"], height=34)
        rod.pack(fill="x", side="bottom")
        rod.pack_propagate(False)
        self.lbl_estado = tk.Label(rod, text="",
                                    font=("Segoe UI", 9),
                                    bg=CORES["painel"], fg=CORES["sub"])
        self.lbl_estado.pack(side="left", padx=16, pady=8)

    def _btn(self, txt, cor, cmd, parent):
        return tk.Button(parent, text=txt,
                         font=("Segoe UI", 10, "bold"),
                         bg=cor, fg=CORES["branco"],
                         relief="flat", cursor="hand2",
                         padx=13, pady=7, command=cmd)

    def _atualizar(self):
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.cofres):
            vault   = c.get("vault", "")
            existe  = os.path.exists(vault)
            estado  = "🔒" if existe else "⚠️"
            tam     = formatar_tamanho(os.path.getsize(vault)) if existe else "—"
            lanc    = os.path.basename(c.get("lancador", "")) or "—"
            tag     = "par" if i % 2 == 0 else "impar"
            self.tree.insert("", "end", values=(
                estado, c.get("nome", "?"),
                vault, tam, lanc,
                c.get("criado", "—"),
            ), tags=(tag,))

        self.tree.tag_configure("par",   background=CORES["card"])
        self.tree.tag_configure("impar", background=CORES["painel"])

        n = len(self.cofres)
        self.lbl_estado.config(
            text=f"{n} cofre{'s' if n != 1 else ''} registado{'s' if n != 1 else ''}")

    def _selecao(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sem seleção",
                                    "Seleciona um cofre na lista.")
            return None
        return self.cofres[self.tree.index(sel[0])]

    # ── Ações ─────────────────────────────────
    def criar_cofre(self):
        pasta = filedialog.askdirectory(
            title="Seleciona a pasta que queres encriptar"
        )
        if not pasta:
            return

        pasta = os.path.normpath(pasta)
        nome  = os.path.basename(pasta)

        # Confirmar
        n_fichs = sum(
            len(fs) for _, _, fs in os.walk(pasta)
        )
        if not messagebox.askyesno(
            "Criar Cofre Encriptado",
            f"Vais encriptar a pasta:\n\n"
            f"📁 {nome}\n"
            f"   {pasta}\n"
            f"   {n_fichs} ficheiro(s)\n\n"
            f"⚠️ A pasta ORIGINAL será APAGADA após encriptar.\n"
            f"Só o ficheiro .vault ficará.\n\n"
            f"Tens a certeza?"
        ):
            return

        dlg = DialogoProgresso(self, "A criar cofre…")
        dlg.set_msg(f"A encriptar {nome}…")

        resultado = [None, None]

        def encriptar():
            try:
                vault = criar_cofre(pasta)
                resultado[0] = vault
            except Exception as e:
                resultado[1] = str(e)
            finally:
                self.after(0, fim)

        def fim():
            dlg.destroy()
            if resultado[1]:
                messagebox.showerror("Erro",
                                      f"Erro ao criar cofre:\n{resultado[1]}")
                return

            vault   = resultado[0]
            lancador = criar_lancador_vault(vault, nome)

            entrada = {
                "nome":     nome,
                "vault":    vault,
                "lancador": lancador,
                "criado":   datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            self.cofres.append(entrada)
            guardar_cofres(self.cofres)
            self._atualizar()

            messagebox.showinfo(
                "✅ Cofre Criado!",
                f"Cofre criado com sucesso!\n\n"
                f"🔒 Ficheiro: {os.path.basename(vault)}\n"
                f"🚀 Lançador: {os.path.basename(lancador)}\n\n"
                f"Distribui o lançador .bat (e os ficheiros\n"
                f"auth_v2.py, vault_guard.py, vault_system.py)\n"
                f"ao cliente."
            )

        t = threading.Thread(target=encriptar, daemon=True)
        t.start()

    def abrir_cofre(self):
        cofre = self._selecao()
        if not cofre:
            return
        vault = cofre.get("vault", "")
        if not os.path.exists(vault):
            messagebox.showerror("Não encontrado",
                                  f"O ficheiro .vault não foi encontrado:\n{vault}")
            return
        subprocess.Popen([sys.executable,
                          os.path.join(DIR_BASE, "vault_guard.py"),
                          vault])

    def criar_lancador(self):
        cofre = self._selecao()
        if not cofre:
            return
        vault = cofre.get("vault", "")
        if not os.path.exists(vault):
            messagebox.showerror("Erro", "O ficheiro .vault não existe.")
            return
        nome    = cofre.get("nome", "cofre")
        lancador = criar_lancador_vault(vault, nome)
        cofre["lancador"] = lancador
        guardar_cofres(self.cofres)
        self._atualizar()
        messagebox.showinfo("✅ Lançador Criado",
                             f"Lançador criado:\n{lancador}")

    def eliminar_cofre(self):
        cofre = self._selecao()
        if not cofre:
            return
        nome = cofre.get("nome", "?")

        if not messagebox.askyesno(
            "⚠️ Eliminar Cofre",
            f"Vais ELIMINAR permanentemente o cofre:\n\n"
            f"🔒 {nome}\n\n"
            f"ATENÇÃO: Os ficheiros dentro do cofre serão\n"
            f"PERDIDOS para sempre se não tiveres backup!\n\n"
            f"Tens a certeza ABSOLUTA?"
        ):
            return

        vault   = cofre.get("vault", "")
        lancador = cofre.get("lancador", "")

        if vault and os.path.exists(vault):
            os.remove(vault)
        if lancador and os.path.exists(lancador):
            os.remove(lancador)

        self.cofres = [c for c in self.cofres
                       if c.get("vault") != vault]
        guardar_cofres(self.cofres)
        self._atualizar()
        messagebox.showinfo("Eliminado", f"Cofre '{nome}' eliminado.")


if __name__ == "__main__":
    GestorCofres().mainloop()
