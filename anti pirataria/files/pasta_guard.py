"""
Proteção de Pasta — Sistema Anti-Pirataria
==========================================
Bloqueia o acesso a uma pasta com autenticação.

Ao tentar aceder à pasta protegida:
  1. Abre diálogo de login
  2. Verifica credenciais + dispositivo
  3. Regista MAC, IP, hostname, OS no servidor
  4. Marca dispositivo como "em uso"
  5. Liberta acesso à pasta

Uso rápido:
    python pasta_guard.py                    # seleciona pasta com diálogo
    python pasta_guard.py "C:/minha/pasta"   # especifica pasta diretamente

Integração no teu código:
    from pasta_guard import proteger_pasta
    pasta = proteger_pasta()                 # retorna path se OK, None se falhar
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import subprocess

# Importa o módulo de autenticação da mesma pasta
sys.path.insert(0, os.path.dirname(__file__))
import auth_v2 as auth


# ══════════════════════════════════════════════
#  JANELA DE LOGIN — PROTEÇÃO DE PASTA
# ══════════════════════════════════════════════
class JanelaLogin(tk.Tk):
    def __init__(self, pasta_path: str = None):
        super().__init__()
        self.pasta_path   = pasta_path
        self.pasta_final  = None
        self.resultado    = None

        self.title("Acesso Protegido")
        self.geometry("440x560")
        self.configure(bg="#0f1117")
        self.resizable(False, False)

        # Centrar janela no ecrã
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 440) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"440x560+{x}+{y}")

        self._construir()
        self.mainloop()

    def _construir(self):
        # Ícone / cabeçalho
        tk.Label(self, text="🔐",
                 font=("Segoe UI", 48),
                 bg="#0f1117", fg="#7986cb").pack(pady=(30, 0))

        tk.Label(self, text="Pasta Protegida",
                 font=("Segoe UI", 18, "bold"),
                 bg="#0f1117", fg="#e8eaf6").pack(pady=(8, 2))

        tk.Label(self, text="Faz login para aceder ao conteúdo",
                 font=("Segoe UI", 10),
                 bg="#0f1117", fg="#7986cb").pack()

        # Seletor de pasta (se não foi especificada)
        if not self.pasta_path:
            frame_pasta = tk.Frame(self, bg="#1a1d27", pady=12, padx=20)
            frame_pasta.pack(fill="x", padx=30, pady=(20, 0))

            tk.Label(frame_pasta, text="Pasta a proteger:",
                     font=("Segoe UI", 9),
                     bg="#1a1d27", fg="#7986cb").pack(anchor="w")

            linha = tk.Frame(frame_pasta, bg="#1a1d27")
            linha.pack(fill="x", pady=(4, 0))

            self.var_pasta = tk.StringVar(value="Nenhuma pasta selecionada")
            tk.Label(linha, textvariable=self.var_pasta,
                     font=("Segoe UI", 9),
                     bg="#1a1d27", fg="#e8eaf6",
                     width=28, anchor="w").pack(side="left")

            tk.Button(linha, text="📁",
                      font=("Segoe UI", 11),
                      bg="#2196f3", fg="white",
                      relief="flat", cursor="hand2", padx=8,
                      command=self._selecionar_pasta).pack(side="right")
        else:
            nome = os.path.basename(self.pasta_path) or self.pasta_path
            frame_pasta = tk.Frame(self, bg="#1a1d27", pady=10, padx=20)
            frame_pasta.pack(fill="x", padx=30, pady=(20, 0))
            tk.Label(frame_pasta,
                     text=f"📁  {nome}",
                     font=("Segoe UI", 10, "bold"),
                     bg="#1a1d27", fg="#e8eaf6").pack()
            self.pasta_final = self.pasta_path

        # Formulário de login
        form = tk.Frame(self, bg="#0f1117")
        form.pack(padx=30, pady=20, fill="x")

        tk.Label(form, text="Email",
                 font=("Segoe UI", 9),
                 bg="#0f1117", fg="#7986cb").pack(anchor="w")
        self.email_var = tk.StringVar()
        self.entry_email = tk.Entry(form, textvariable=self.email_var,
                                    font=("Segoe UI", 12),
                                    bg="#22263a", fg="#e8eaf6",
                                    insertbackground="#e8eaf6",
                                    relief="flat", bd=10)
        self.entry_email.pack(fill="x", pady=(4, 14))

        tk.Label(form, text="Password",
                 font=("Segoe UI", 9),
                 bg="#0f1117", fg="#7986cb").pack(anchor="w")
        self.pwd_var = tk.StringVar()
        self.entry_pwd = tk.Entry(form, textvariable=self.pwd_var,
                                   show="•", font=("Segoe UI", 12),
                                   bg="#22263a", fg="#e8eaf6",
                                   insertbackground="#e8eaf6",
                                   relief="flat", bd=10)
        self.entry_pwd.pack(fill="x", pady=(4, 0))

        # Barra de progresso (escondida por defeito)
        self.barra = ttk.Progressbar(form, mode="indeterminate")

        # Mensagem de erro/sucesso
        self.lbl_msg = tk.Label(form, text="",
                                 font=("Segoe UI", 9),
                                 bg="#0f1117", fg="#f44336",
                                 wraplength=360)
        self.lbl_msg.pack(pady=(10, 0))

        # Botão de login
        self.btn_login = tk.Button(self, text="ENTRAR",
                                    font=("Segoe UI", 12, "bold"),
                                    bg="#2196f3", fg="white",
                                    relief="flat", cursor="hand2",
                                    pady=14,
                                    command=self._fazer_login)
        self.btn_login.pack(fill="x", padx=30, pady=(0, 10))

        tk.Button(self, text="Cancelar",
                  font=("Segoe UI", 9),
                  bg="#0f1117", fg="#7986cb",
                  relief="flat", cursor="hand2",
                  command=self.destroy).pack()

        # Enter para submeter
        self.entry_email.bind("<Return>", lambda e: self.entry_pwd.focus())
        self.entry_pwd.bind("<Return>",  lambda e: self._fazer_login())
        self.entry_email.focus()

    def _selecionar_pasta(self):
        path = filedialog.askdirectory(title="Seleciona a pasta protegida")
        if path:
            self.pasta_final = path
            nome = os.path.basename(path) or path
            self.var_pasta.set(nome[:35] + ("…" if len(nome) > 35 else ""))

    def _fazer_login(self):
        email = self.email_var.get().strip()
        pwd   = self.pwd_var.get().strip()

        if not email or not pwd:
            self._mostrar_msg("Preenche o email e a password.", erro=True)
            return

        if not self.pasta_final and not self.pasta_path:
            self._mostrar_msg("Seleciona uma pasta primeiro.", erro=True)
            return

        # Mostrar loading
        self.btn_login.config(state="disabled", text="A verificar…")
        self.barra.pack(fill="x", pady=(8, 0))
        self.barra.start(10)
        self.lbl_msg.config(text="")
        self.update()

        # Autenticar
        sucesso, mensagem = auth.login(email, pwd)

        self.barra.stop()
        self.barra.pack_forget()
        self.btn_login.config(state="normal", text="ENTRAR")

        if sucesso:
            self._mostrar_msg("✅ " + mensagem, erro=False)
            self.resultado = self.pasta_final or self.pasta_path
            self.after(1200, self._abrir_pasta_e_fechar)
        else:
            self._mostrar_msg(mensagem, erro=True)

    def _mostrar_msg(self, txt: str, erro: bool = True):
        self.lbl_msg.config(
            text=txt,
            fg="#f44336" if erro else "#4caf50"
        )

    def _abrir_pasta_e_fechar(self):
        """Abre a pasta no explorador de ficheiros e fecha a janela."""
        pasta = self.resultado
        if pasta and os.path.exists(pasta):
            if sys.platform == "win32":
                os.startfile(pasta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pasta])
            else:
                subprocess.Popen(["xdg-open", pasta])
        self.destroy()


# ══════════════════════════════════════════════
#  FUNÇÃO DE INTEGRAÇÃO FÁCIL
# ══════════════════════════════════════════════
def proteger_pasta(pasta_path: str = None) -> str | None:
    """
    Mostra o diálogo de login e retorna o path da pasta se autenticado.
    Retorna None se o utilizador cancelar ou falhar.

    Exemplos:
        pasta = proteger_pasta()                    # seleciona pasta
        pasta = proteger_pasta("C:/minha/pasta")    # pasta fixa

    Se 'pasta' não for None, o utilizador está autenticado e podes abrir
    os ficheiros dentro dessa pasta livremente.
    """
    janela = JanelaLogin(pasta_path=pasta_path)
    return janela.resultado


# ══════════════════════════════════════════════
#  EXECUÇÃO DIRETA
# ══════════════════════════════════════════════
if __name__ == "__main__":
    # Aceita pasta como argumento da linha de comandos
    pasta = sys.argv[1] if len(sys.argv) > 1 else None
    resultado = proteger_pasta(pasta)

    if resultado:
        print(f"✅ Acesso concedido: {resultado}")
    else:
        print("❌ Acesso negado ou cancelado.")
