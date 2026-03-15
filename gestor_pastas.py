"""
Gestor de Pastas Protegidas
============================
Ferramenta gráfica para proteger qualquer pasta com autenticação.

Como funciona:
  1. Selecionas uma pasta
  2. Clicas em "Proteger"
  3. É criado um lançador (.bat no Windows, .sh no Linux/Mac)
  4. Quando alguém clica no lançador → pede login antes de abrir a pasta

A pasta em si fica acessível normalmente pelo sistema (proteção é pelo lançador).
Para segurança máxima, move a pasta para um local escondido e distribui só o lançador.

Uso:
    python gestor_pastas.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# Ficheiro onde guardamos as pastas protegidas
# ──────────────────────────────────────────────
DADOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pastas_protegidas.json")

# Caminho absoluto para pasta_guard.py (mesmo diretório que este ficheiro)
DIR_BASE    = os.path.dirname(os.path.abspath(__file__))
GUARD_PATH  = os.path.join(DIR_BASE, "pasta_guard.py")
AUTH_PATH   = os.path.join(DIR_BASE, "auth_v2.py")


# ══════════════════════════════════════════════
#  GESTÃO DOS DADOS
# ══════════════════════════════════════════════
def carregar_pastas() -> list:
    if not os.path.exists(DADOS_FILE):
        return []
    try:
        with open(DADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def guardar_pastas(pastas: list):
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(pastas, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════
#  CRIAÇÃO DO LANÇADOR
# ══════════════════════════════════════════════
def criar_lancador(pasta_path: str, nome_custom: str = None) -> str:
    """
    Cria um ficheiro lançador que abre a janela de login antes da pasta.
    Retorna o caminho do lançador criado.
    """
    nome   = nome_custom or os.path.basename(pasta_path)
    python = sys.executable   # caminho do Python atual

    sistema = platform.system()

    if sistema == "Windows":
        # Cria um .bat na mesma pasta que o gestor
        lancador_path = os.path.join(DIR_BASE, f"Abrir — {nome}.bat")
        conteudo = (
            f'@echo off\n'
            f'"{python}" "{GUARD_PATH}" "{pasta_path}"\n'
        )
    else:
        # Cria um .sh no Linux / macOS
        lancador_path = os.path.join(DIR_BASE, f"Abrir_{nome}.sh")
        conteudo = (
            f'#!/bin/bash\n'
            f'"{python}" "{GUARD_PATH}" "{pasta_path}"\n'
        )

    with open(lancador_path, "w", encoding="utf-8") as f:
        f.write(conteudo)

    # No Linux/macOS torna executável
    if sistema != "Windows":
        os.chmod(lancador_path, 0o755)

    return lancador_path


def remover_lancador(lancador_path: str):
    """Remove o ficheiro lançador se existir."""
    try:
        if lancador_path and os.path.exists(lancador_path):
            os.remove(lancador_path)
    except Exception:
        pass


# ══════════════════════════════════════════════
#  INTERFACE GRÁFICA
# ══════════════════════════════════════════════
CORES = {
    "bg":       "#0d0f18",
    "painel":   "#141720",
    "card":     "#1c2030",
    "borda":    "#252a40",
    "texto":    "#dde3f8",
    "sub":      "#6c7bb5",
    "verde":    "#3dd68c",
    "vermelho": "#f05454",
    "laranja":  "#f0a854",
    "azul":     "#4d7cfe",
    "branco":   "#ffffff",
}


class GestorPastas(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔐 Gestor de Pastas Protegidas")
        self.geometry("820x580")
        self.minsize(700, 460)
        self.configure(bg=CORES["bg"])

        self.pastas = carregar_pastas()
        self._construir_ui()
        self._atualizar_lista()

    # ── UI ────────────────────────────────────
    def _construir_ui(self):
        # Cabeçalho
        header = tk.Frame(self, bg=CORES["painel"], height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🔐  Gestor de Pastas Protegidas",
                 font=("Segoe UI", 15, "bold"),
                 bg=CORES["painel"], fg=CORES["texto"]).pack(
                     side="left", padx=24, pady=18)

        tk.Label(header,
                 text="Seleciona uma pasta → fica protegida por login",
                 font=("Segoe UI", 9),
                 bg=CORES["painel"], fg=CORES["sub"]).pack(
                     side="left", padx=0, pady=18)

        # Barra de ações
        barra = tk.Frame(self, bg=CORES["bg"], pady=14)
        barra.pack(fill="x", padx=20)

        self._btn("➕  Adicionar Pasta", CORES["azul"],
                  self.adicionar_pasta, barra).pack(side="left")

        self._btn("🚀  Abrir com Login", CORES["verde"],
                  self.abrir_pasta, barra).pack(side="left", padx=8)

        self._btn("🗑️  Remover Proteção", CORES["vermelho"],
                  self.remover_pasta, barra).pack(side="left")

        self._btn("📋  Copiar Lançador", CORES["laranja"],
                  self.copiar_lancador, barra).pack(side="right")

        # Tabela
        frame_tab = tk.Frame(self, bg=CORES["bg"])
        frame_tab.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Estilo
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("P.Treeview",
                        background=CORES["card"],
                        foreground=CORES["texto"],
                        fieldbackground=CORES["card"],
                        rowheight=38,
                        font=("Segoe UI", 10))
        style.configure("P.Treeview.Heading",
                        background=CORES["painel"],
                        foreground=CORES["sub"],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat", padding=8)
        style.map("P.Treeview",
                  background=[("selected", CORES["azul"])],
                  foreground=[("selected", CORES["branco"])])

        colunas = ("icone", "nome", "caminho", "lancador", "adicionado")
        self.tree = ttk.Treeview(frame_tab, columns=colunas,
                                  show="headings", style="P.Treeview")

        cfg = {
            "icone":     ("",              40),
            "nome":      ("Nome da Pasta", 160),
            "caminho":   ("Caminho",       280),
            "lancador":  ("Lançador",      200),
            "adicionado":("Adicionado",    130),
        }
        for col, (label, w) in cfg.items():
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, minwidth=40)

        vsb = ttk.Scrollbar(frame_tab, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", lambda e: self.abrir_pasta())

        # Rodapé / estado
        rodape = tk.Frame(self, bg=CORES["painel"], height=36)
        rodape.pack(fill="x", side="bottom")
        rodape.pack_propagate(False)

        self.lbl_estado = tk.Label(rodape, text="",
                                    font=("Segoe UI", 9),
                                    bg=CORES["painel"], fg=CORES["sub"])
        self.lbl_estado.pack(side="left", padx=16, pady=8)

        tk.Label(rodape,
                 text="Double-click para abrir  |  Clique direito para mais opções",
                 font=("Segoe UI", 8),
                 bg=CORES["painel"], fg=CORES["borda"]).pack(
                     side="right", padx=16)

        # Menu de contexto
        self.menu_ctx = tk.Menu(self, tearoff=0,
                                 bg=CORES["card"], fg=CORES["texto"],
                                 font=("Segoe UI", 10),
                                 activebackground=CORES["azul"],
                                 activeforeground=CORES["branco"])
        self.menu_ctx.add_command(label="🚀 Abrir com Login",
                                   command=self.abrir_pasta)
        self.menu_ctx.add_command(label="📁 Revelar no Explorador",
                                   command=self.revelar_no_explorador)
        self.menu_ctx.add_separator()
        self.menu_ctx.add_command(label="📋 Copiar caminho do Lançador",
                                   command=self.copiar_lancador)
        self.menu_ctx.add_separator()
        self.menu_ctx.add_command(label="🗑️ Remover Proteção",
                                   command=self.remover_pasta,
                                   foreground=CORES["vermelho"])

        self.tree.bind("<Button-3>",
                       lambda e: self.menu_ctx.post(e.x_root, e.y_root))

    def _btn(self, texto, cor, cmd, parent):
        return tk.Button(parent, text=texto,
                         font=("Segoe UI", 10, "bold"),
                         bg=cor, fg=CORES["branco"],
                         relief="flat", cursor="hand2",
                         padx=14, pady=8, command=cmd)

    # ── Lógica ───────────────────────────────
    def _atualizar_lista(self):
        self.tree.delete(*self.tree.get_children())
        for i, p in enumerate(self.pastas):
            existe      = os.path.exists(p["caminho"])
            lancador_ok = os.path.exists(p.get("lancador", ""))
            icone = "✅" if existe else "⚠️"

            nome_lancador = (
                os.path.basename(p.get("lancador", ""))
                if lancador_ok else "—  (não encontrado)"
            )

            tag = "par" if i % 2 == 0 else "impar"
            self.tree.insert("", "end", values=(
                icone,
                p.get("nome", "—"),
                p.get("caminho", "—"),
                nome_lancador,
                p.get("adicionado", "—"),
            ), tags=(tag,))

        self.tree.tag_configure("par",   background=CORES["card"])
        self.tree.tag_configure("impar", background=CORES["painel"])

        n = len(self.pastas)
        self.lbl_estado.config(
            text=f"{n} pasta{'s' if n != 1 else ''} protegida{'s' if n != 1 else ''}")

    def _selecao(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nenhuma seleção",
                                   "Seleciona uma pasta da lista.")
            return None
        idx = self.tree.index(sel[0])
        return self.pastas[idx]

    def adicionar_pasta(self):
        path = filedialog.askdirectory(
            title="Seleciona a pasta que queres proteger"
        )
        if not path:
            return

        path = os.path.normpath(path)

        # Verificar se já existe
        if any(p["caminho"] == path for p in self.pastas):
            messagebox.showinfo("Já protegida",
                                "Esta pasta já está na lista de proteção.")
            return

        # Pedir nome personalizado (opcional)
        nome = os.path.basename(path)
        nome_custom = self._pedir_nome(nome)
        if nome_custom is None:
            return   # cancelou
        if nome_custom.strip():
            nome = nome_custom.strip()

        # Criar lançador
        try:
            lancador = criar_lancador(path, nome)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar o lançador:\n{e}")
            return

        entrada = {
            "nome":       nome,
            "caminho":    path,
            "lancador":   lancador,
            "adicionado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        self.pastas.append(entrada)
        guardar_pastas(self.pastas)
        self._atualizar_lista()

        # Selecionar a linha recém-criada
        ultimo = self.tree.get_children()[-1]
        self.tree.selection_set(ultimo)
        self.tree.see(ultimo)

        messagebox.showinfo(
            "✅ Pasta Protegida!",
            f"A pasta foi protegida com sucesso.\n\n"
            f"📁 Pasta: {nome}\n"
            f"🚀 Lançador criado:\n{lancador}\n\n"
            f"Distribui o lançador aos utilizadores.\n"
            f"Ao clicarem nele, será pedido o login."
        )

    def _pedir_nome(self, sugestao: str):
        """Janela simples para pedir nome personalizado."""
        janela = tk.Toplevel(self)
        janela.title("Nome da Pasta")
        janela.geometry("380x180")
        janela.configure(bg=CORES["bg"])
        janela.resizable(False, False)
        janela.grab_set()

        resultado = [None]

        tk.Label(janela, text="Nome para o lançador (opcional):",
                 font=("Segoe UI", 10),
                 bg=CORES["bg"], fg=CORES["texto"]).pack(
                     padx=24, pady=(20, 6), anchor="w")

        var = tk.StringVar(value=sugestao)
        entry = tk.Entry(janela, textvariable=var,
                          font=("Segoe UI", 12),
                          bg=CORES["card"], fg=CORES["texto"],
                          insertbackground=CORES["texto"],
                          relief="flat", bd=10)
        entry.pack(fill="x", padx=24)
        entry.select_range(0, "end")
        entry.focus()

        frame_btn = tk.Frame(janela, bg=CORES["bg"])
        frame_btn.pack(pady=16, padx=24, fill="x")

        def confirmar():
            resultado[0] = var.get()
            janela.destroy()

        def cancelar():
            janela.destroy()

        tk.Button(frame_btn, text="Cancelar",
                  font=("Segoe UI", 10),
                  bg=CORES["card"], fg=CORES["sub"],
                  relief="flat", cursor="hand2", padx=12, pady=6,
                  command=cancelar).pack(side="right", padx=(8, 0))

        tk.Button(frame_btn, text="Confirmar",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["azul"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=12, pady=6,
                  command=confirmar).pack(side="right")

        entry.bind("<Return>", lambda e: confirmar())
        entry.bind("<Escape>", lambda e: cancelar())

        self.wait_window(janela)
        return resultado[0]

    def abrir_pasta(self):
        pasta = self._selecao()
        if not pasta:
            return

        caminho = pasta["caminho"]
        if not os.path.exists(caminho):
            messagebox.showerror("Pasta não encontrada",
                                  f"A pasta já não existe:\n{caminho}")
            return

        # Corre pasta_guard.py que mostra o login
        python = sys.executable
        subprocess.Popen([python, GUARD_PATH, caminho])

    def remover_pasta(self):
        pasta = self._selecao()
        if not pasta:
            return

        if not messagebox.askyesno(
            "Remover Proteção",
            f"Vais remover a proteção da pasta:\n\n"
            f"📁 {pasta['nome']}\n\n"
            f"O lançador também será eliminado.\n"
            f"A pasta em si NÃO é apagada. Confirmas?"
        ):
            return

        remover_lancador(pasta.get("lancador", ""))
        self.pastas = [p for p in self.pastas
                       if p["caminho"] != pasta["caminho"]]
        guardar_pastas(self.pastas)
        self._atualizar_lista()
        messagebox.showinfo("Removido", "Proteção removida com sucesso.")

    def revelar_no_explorador(self):
        pasta = self._selecao()
        if not pasta:
            return
        caminho = pasta["caminho"]
        if not os.path.exists(caminho):
            messagebox.showerror("Não encontrada",
                                  "A pasta não foi encontrada no sistema.")
            return
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(caminho)
        elif sistema == "Darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])

    def copiar_lancador(self):
        pasta = self._selecao()
        if not pasta:
            return
        lancador = pasta.get("lancador", "")
        if not lancador:
            messagebox.showwarning("Sem lançador",
                                    "Não há lançador associado a esta pasta.")
            return
        self.clipboard_clear()
        self.clipboard_append(lancador)
        self.lbl_estado.config(
            text=f"✓ Caminho copiado: {os.path.basename(lancador)}",
            fg=CORES["verde"]
        )
        self.after(3000, lambda: self.lbl_estado.config(
            text=f"{len(self.pastas)} pastas protegidas",
            fg=CORES["sub"]
        ))


# ══════════════════════════════════════════════
if __name__ == "__main__":
    app = GestorPastas()
    app.mainloop()
