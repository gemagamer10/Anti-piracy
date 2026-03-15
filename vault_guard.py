"""
Vault Guard — vault_guard.py
=============================
Janela de login que desencripta o cofre após autenticação.

Fluxo:
  1. Utilizador abre o lançador (.bat)
  2. Aparece janela de login
  3. Após login válido → cofre desencriptado para pasta temporária
  4. Pasta temporária abre no explorador
  5. Uma janela pequena fica na barra de tarefas a monitorizar
  6. Quando o utilizador clica "Fechar Sessão" (ou fecha a janela) →
     pasta temporária é completamente apagada (shred)

Uso:
    python vault_guard.py "C:/caminho/para/cofre.vault"
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import subprocess
import threading
import time
import platform
from pathlib import Path

# Importar módulos do sistema
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth_v2 as auth
from vault_system import abrir_cofre, fechar_cofre

# ──────────────────────────────────────────────
CORES = {
    "bg":       "#0d0f18",
    "card":     "#1c2030",
    "texto":    "#dde3f8",
    "sub":      "#6c7bb5",
    "verde":    "#3dd68c",
    "vermelho": "#f05454",
    "azul":     "#4d7cfe",
    "laranja":  "#f0a854",
    "branco":   "#ffffff",
}


# ══════════════════════════════════════════════
#  JANELA DE LOGIN
# ══════════════════════════════════════════════
class JanelaLogin(tk.Tk):
    def __init__(self, vault_path: str):
        super().__init__()
        self.vault_path  = vault_path
        self.pasta_temp  = None
        self.autenticado = False

        nome_cofre = Path(vault_path).stem

        self.title(f"🔐 Acesso — {nome_cofre}")
        self.geometry("420x520")
        self.configure(bg=CORES["bg"])
        self.resizable(False, False)

        # Centrar na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 420) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"420x520+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self._construir()
        self.mainloop()

    def _construir(self):
        nome = Path(self.vault_path).stem

        # Ícone
        tk.Label(self, text="🔒",
                 font=("Segoe UI Emoji", 44),
                 bg=CORES["bg"]).pack(pady=(32, 0))

        tk.Label(self, text=nome,
                 font=("Segoe UI", 16, "bold"),
                 bg=CORES["bg"], fg=CORES["texto"]).pack(pady=(8, 2))

        tk.Label(self, text="Este conteúdo está encriptado.\nFaz login para aceder.",
                 font=("Segoe UI", 10),
                 bg=CORES["bg"], fg=CORES["sub"],
                 justify="center").pack(pady=(0, 24))

        # Formulário
        form = tk.Frame(self, bg=CORES["bg"])
        form.pack(padx=36, fill="x")

        tk.Label(form, text="EMAIL",
                 font=("Segoe UI", 8, "bold"),
                 bg=CORES["bg"], fg=CORES["sub"]).pack(anchor="w")
        self.v_email = tk.StringVar()
        self.e_email = tk.Entry(form, textvariable=self.v_email,
                                 font=("Segoe UI", 12),
                                 bg=CORES["card"], fg=CORES["texto"],
                                 insertbackground=CORES["texto"],
                                 relief="flat", bd=10)
        self.e_email.pack(fill="x", pady=(3, 14))

        tk.Label(form, text="PASSWORD",
                 font=("Segoe UI", 8, "bold"),
                 bg=CORES["bg"], fg=CORES["sub"]).pack(anchor="w")
        self.v_pwd = tk.StringVar()
        self.e_pwd = tk.Entry(form, textvariable=self.v_pwd,
                               show="•", font=("Segoe UI", 12),
                               bg=CORES["card"], fg=CORES["texto"],
                               insertbackground=CORES["texto"],
                               relief="flat", bd=10)
        self.e_pwd.pack(fill="x", pady=(3, 0))

        # Barra de loading
        self.barra = ttk.Progressbar(form, mode="indeterminate")

        # Mensagem
        self.v_msg = tk.StringVar()
        self.lbl_msg = tk.Label(form, textvariable=self.v_msg,
                                 font=("Segoe UI", 9),
                                 bg=CORES["bg"], fg=CORES["vermelho"],
                                 wraplength=340, justify="center")
        self.lbl_msg.pack(pady=(10, 0))

        # Botão
        self.btn = tk.Button(self, text="DESENCRIPTAR E ABRIR",
                              font=("Segoe UI", 11, "bold"),
                              bg=CORES["azul"], fg=CORES["branco"],
                              relief="flat", cursor="hand2",
                              pady=13, command=self._login)
        self.btn.pack(fill="x", padx=36, pady=(16, 8))

        tk.Button(self, text="Cancelar",
                  font=("Segoe UI", 9),
                  bg=CORES["bg"], fg=CORES["sub"],
                  relief="flat", cursor="hand2",
                  command=self._cancelar).pack()

        self.e_email.bind("<Return>", lambda e: self.e_pwd.focus())
        self.e_pwd.bind("<Return>",  lambda e: self._login())
        self.e_email.focus()

    def _msg(self, texto, erro=True):
        self.v_msg.set(texto)
        self.lbl_msg.config(fg=CORES["vermelho"] if erro else CORES["verde"])

    def _login(self):
        email = self.v_email.get().strip()
        pwd   = self.v_pwd.get().strip()

        if not email or not pwd:
            self._msg("Preenche email e password.")
            return

        self.btn.config(state="disabled", text="A verificar…")
        self.barra.pack(fill="x", pady=(8, 0))
        self.barra.start(10)
        self.v_msg.set("")
        self.update()

        sucesso, mensagem = auth.login(email, pwd)

        self.barra.stop()
        self.barra.pack_forget()
        self.btn.config(state="normal", text="DESENCRIPTAR E ABRIR")

        if not sucesso:
            self._msg(mensagem)
            return

        # Login OK — desencriptar cofre
        self._msg("✅ Autenticado! A desencriptar…", erro=False)
        self.update()

        try:
            self.pasta_temp = abrir_cofre(self.vault_path)
        except Exception as e:
            self._msg(f"Erro ao desencriptar: {e}")
            return

        self.autenticado = True
        self.destroy()

    def _cancelar(self):
        self.autenticado = False
        self.destroy()


# ══════════════════════════════════════════════
#  JANELA DE SESSÃO ATIVA (fica na barra)
# ══════════════════════════════════════════════
class JanelaSessao(tk.Tk):
    """
    Pequena janela que fica aberta enquanto o utilizador usa os ficheiros.
    Monitoriza a sessão e apaga a pasta temp ao fechar.
    """
    def __init__(self, vault_path: str, pasta_temp: str):
        super().__init__()
        self.vault_path = vault_path
        self.pasta_temp = pasta_temp
        self.a_fechar   = False

        nome = Path(vault_path).stem
        self.title(f"🔓 Sessão Ativa — {nome}")
        self.geometry("360x200")
        self.configure(bg=CORES["bg"])
        self.resizable(False, False)

        # Posicionar no canto inferior direito
        self.update_idletasks()
        x = self.winfo_screenwidth()  - 380
        y = self.winfo_screenheight() - 240
        self.geometry(f"360x200+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._fechar_sessao)
        self._construir()

        # Verificar sessão periodicamente
        self._verificar_sessao()

        # Abrir a pasta no explorador
        self._abrir_explorador()

        self.mainloop()

    def _construir(self):
        tk.Label(self, text="🔓  SESSÃO ATIVA",
                 font=("Segoe UI", 11, "bold"),
                 bg=CORES["bg"], fg=CORES["verde"]).pack(pady=(18, 4))

        nome = Path(self.vault_path).stem
        tk.Label(self, text=nome,
                 font=("Segoe UI", 10),
                 bg=CORES["bg"], fg=CORES["texto"]).pack()

        tk.Label(self,
                 text="Os ficheiros estão desencriptados.\nFecha esta janela para encerrar a sessão\ne apagar os ficheiros temporários.",
                 font=("Segoe UI", 9),
                 bg=CORES["bg"], fg=CORES["sub"],
                 justify="center").pack(pady=(8, 14))

        tk.Button(self, text="🔒  FECHAR SESSÃO E ENCRIPTAR",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["vermelho"], fg=CORES["branco"],
                  relief="flat", cursor="hand2",
                  pady=10, command=self._fechar_sessao).pack(
                      fill="x", padx=20)

    def _abrir_explorador(self):
        """Abre a pasta temporária no explorador de ficheiros."""
        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(self.pasta_temp)
            elif sistema == "Darwin":
                subprocess.Popen(["open", self.pasta_temp])
            else:
                subprocess.Popen(["xdg-open", self.pasta_temp])
        except Exception:
            pass

    def _verificar_sessao(self):
        """Verifica periodicamente se a sessão ainda é válida."""
        if self.a_fechar:
            return

        def verificar():
            try:
                valida, msg = auth.verificar_sessao()
                if not valida:
                    self.after(0, lambda: self._sessao_expirada(msg))
            except Exception:
                pass

        t = threading.Thread(target=verificar, daemon=True)
        t.start()

        # Verifica a cada 30 segundos
        self.after(30_000, self._verificar_sessao)

    def _sessao_expirada(self, msg: str):
        messagebox.showwarning(
            "Sessão Expirada",
            f"{msg}\n\nA sessão vai ser fechada e os ficheiros temporários apagados.",
            parent=self
        )
        self._fechar_sessao()

    def _fechar_sessao(self):
        if self.a_fechar:
            return
        self.a_fechar = True

        if not messagebox.askyesno(
            "Fechar Sessão",
            "Vais fechar a sessão.\n\n"
            "⚠️ Os ficheiros temporários serão APAGADOS.\n"
            "Certifica-te de que guardaste o teu trabalho.\n\n"
            "Continuar?",
            parent=self
        ):
            self.a_fechar = False
            return

        self.configure(bg="#1a0000")
        for widget in self.winfo_children():
            widget.destroy()

        tk.Label(self, text="🔒  A encriptar e limpar…",
                 font=("Segoe UI", 11, "bold"),
                 bg="#1a0000", fg=CORES["laranja"]).pack(expand=True)
        self.update()

        def limpar():
            fechar_cofre(self.pasta_temp)
            auth.logout()
            self.after(800, self.destroy)

        t = threading.Thread(target=limpar, daemon=True)
        t.start()


# ══════════════════════════════════════════════
#  PONTO DE ENTRADA
# ══════════════════════════════════════════════
def main():
    if len(sys.argv) < 2:
        print("Uso: python vault_guard.py <caminho_do_cofre.vault>")
        sys.exit(1)

    vault_path = sys.argv[1]

    if not os.path.exists(vault_path):
        tk.Tk().withdraw()
        messagebox.showerror("Erro", f"Cofre não encontrado:\n{vault_path}")
        sys.exit(1)

    if not vault_path.endswith(".vault"):
        tk.Tk().withdraw()
        messagebox.showerror("Erro", "O ficheiro não é um cofre .vault válido.")
        sys.exit(1)

    # 1. Mostrar login
    login = JanelaLogin(vault_path)

    if not login.autenticado or not login.pasta_temp:
        sys.exit(0)

    # 2. Mostrar janela de sessão ativa (abre a pasta e monitoriza)
    JanelaSessao(vault_path, login.pasta_temp)


if __name__ == "__main__":
    main()
