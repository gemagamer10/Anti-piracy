"""
Painel de Administrador — Sistema Anti-Pirataria
=================================================
Interface gráfica para gerir utilizadores, dispositivos e sessões.

Funcionalidades:
  ✅ Ver todos os utilizadores e os seus dispositivos
  ✅ Ver MAC, IP, hostname, OS, última atividade
  ✅ Desvincular PC de uma conta (permite mudar de dispositivo)
  ✅ Forçar logout (invalidar sessão ativa)
  ✅ Ver histórico de IPs suspeitos / tentativas bloqueadas
  ✅ Copiar informação de qualquer campo

Requer: pip install requests
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import json
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIGURAÇÃO — usa a SERVICE ROLE KEY (não a anon key!)
# A service role ignora o RLS e permite ver todos os dados
# ──────────────────────────────────────────────
SUPABASE_URL      = "https://SEU_PROJETO.supabase.co"
SUPABASE_SERV_KEY = "SUA_SERVICE_ROLE_KEY"   # Settings → API → service_role
ADMIN_PASSWORD    = "admin1234"               # Muda isto para algo seguro!
# ──────────────────────────────────────────────

CORES = {
    "fundo":       "#0f1117",
    "painel":      "#1a1d27",
    "card":        "#22263a",
    "borda":       "#2e3350",
    "texto":       "#e8eaf6",
    "sub":         "#7986cb",
    "verde":       "#4caf50",
    "vermelho":    "#f44336",
    "laranja":     "#ff9800",
    "azul":        "#2196f3",
    "branco":      "#ffffff",
}

def headers_admin():
    return {
        "apikey":        SUPABASE_SERV_KEY,
        "Authorization": f"Bearer {SUPABASE_SERV_KEY}",
        "Content-Type":  "application/json",
    }

def formatar_data(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_str


# ══════════════════════════════════════════════
#  JANELA DE LOGIN DO ADMINISTRADOR
# ══════════════════════════════════════════════
class LoginAdmin(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Acesso Restrito")
        self.geometry("380x260")
        self.configure(bg=CORES["fundo"])
        self.resizable(False, False)
        self.grab_set()

        tk.Label(self, text="🔐", font=("Segoe UI", 36),
                 bg=CORES["fundo"], fg=CORES["sub"]).pack(pady=(30, 0))
        tk.Label(self, text="Painel de Administrador",
                 font=("Segoe UI", 14, "bold"),
                 bg=CORES["fundo"], fg=CORES["texto"]).pack(pady=(5, 20))

        frame = tk.Frame(self, bg=CORES["fundo"])
        frame.pack(padx=40, fill="x")

        tk.Label(frame, text="Password de Administrador",
                 font=("Segoe UI", 9), bg=CORES["fundo"],
                 fg=CORES["sub"]).pack(anchor="w")
        self.pwd_var = tk.StringVar()
        self.entry = tk.Entry(frame, textvariable=self.pwd_var,
                              show="•", font=("Segoe UI", 12),
                              bg=CORES["card"], fg=CORES["texto"],
                              insertbackground=CORES["texto"],
                              relief="flat", bd=8)
        self.entry.pack(fill="x", pady=(4, 16))
        self.entry.bind("<Return>", lambda e: self.verificar())

        tk.Button(frame, text="ENTRAR",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["azul"], fg=CORES["branco"],
                  relief="flat", cursor="hand2",
                  pady=8, command=self.verificar).pack(fill="x")

        self.entry.focus()

    def verificar(self):
        if self.pwd_var.get() == ADMIN_PASSWORD:
            self.destroy()
            self.callback()
        else:
            messagebox.showerror("Acesso Negado",
                                 "Password incorreta!", parent=self)
            self.pwd_var.set("")


# ══════════════════════════════════════════════
#  PAINEL PRINCIPAL
# ══════════════════════════════════════════════
class PainelAdmin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Painel de Administrador — Anti-Pirataria")
        self.geometry("1100x680")
        self.configure(bg=CORES["fundo"])
        self.withdraw()   # Esconde até ao login

        LoginAdmin(self, self.mostrar_painel)
        self.mainloop()

    def mostrar_painel(self):
        self.deiconify()
        self._construir_ui()
        self.atualizar_tudo()

    # ── Construção da UI ──────────────────────
    def _construir_ui(self):
        # Barra de topo
        topo = tk.Frame(self, bg=CORES["painel"], height=60)
        topo.pack(fill="x")
        topo.pack_propagate(False)

        tk.Label(topo, text="🛡️  PAINEL DE ADMINISTRADOR",
                 font=("Segoe UI", 14, "bold"),
                 bg=CORES["painel"], fg=CORES["texto"]).pack(side="left", padx=20, pady=15)

        self.lbl_status = tk.Label(topo, text="",
                                   font=("Segoe UI", 9),
                                   bg=CORES["painel"], fg=CORES["sub"])
        self.lbl_status.pack(side="left", padx=10)

        tk.Button(topo, text="🔄  Atualizar",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["azul"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=14, pady=6,
                  command=self.atualizar_tudo).pack(side="right", padx=20, pady=10)

        # Estatísticas rápidas
        self.frame_stats = tk.Frame(self, bg=CORES["fundo"])
        self.frame_stats.pack(fill="x", padx=20, pady=10)

        # Abas
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=CORES["fundo"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=CORES["card"], foreground=CORES["sub"],
                        padding=[16, 8], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", CORES["azul"])],
                  foreground=[("selected", CORES["branco"])])

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.aba_dispositivos = tk.Frame(self.abas, bg=CORES["fundo"])
        self.aba_sessoes      = tk.Frame(self.abas, bg=CORES["fundo"])
        self.aba_falhas       = tk.Frame(self.abas, bg=CORES["fundo"])

        self.abas.add(self.aba_dispositivos, text="💻  Dispositivos")
        self.abas.add(self.aba_sessoes,      text="🔑  Sessões Ativas")
        self.abas.add(self.aba_falhas,       text="⚠️  IPs Suspeitos")

        self._construir_aba_dispositivos()
        self._construir_aba_sessoes()
        self._construir_aba_falhas()

    def _stat_card(self, parent, titulo, valor, cor):
        card = tk.Frame(parent, bg=CORES["card"], padx=20, pady=12)
        card.pack(side="left", padx=(0, 12))
        tk.Label(card, text=valor, font=("Segoe UI", 22, "bold"),
                 bg=CORES["card"], fg=cor).pack()
        tk.Label(card, text=titulo, font=("Segoe UI", 9),
                 bg=CORES["card"], fg=CORES["sub"]).pack()

    # ── Aba: Dispositivos ─────────────────────
    def _construir_aba_dispositivos(self):
        frame = self.aba_dispositivos

        # Barra de ações
        barra = tk.Frame(frame, bg=CORES["fundo"])
        barra.pack(fill="x", pady=(10, 6))

        tk.Label(barra, text="Pesquisar:",
                 font=("Segoe UI", 10), bg=CORES["fundo"],
                 fg=CORES["sub"]).pack(side="left")

        self.pesq_var = tk.StringVar()
        self.pesq_var.trace("w", lambda *a: self._filtrar_dispositivos())
        tk.Entry(barra, textvariable=self.pesq_var,
                 font=("Segoe UI", 10),
                 bg=CORES["card"], fg=CORES["texto"],
                 insertbackground=CORES["texto"],
                 relief="flat", bd=8, width=30).pack(side="left", padx=8)

        tk.Button(barra, text="🔓  Desvincular PC",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["laranja"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  command=self.desvincular_dispositivo).pack(side="right", padx=(8, 0))

        tk.Button(barra, text="🚪  Forçar Logout",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["vermelho"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  command=self.forcar_logout).pack(side="right", padx=(8, 0))

        # Tabela
        colunas = ("email", "device_id", "mac", "ip", "hostname",
                   "sistema", "visto_em")
        self.tree_disp = self._criar_tabela(frame, colunas, {
            "email":     ("Email",            200),
            "device_id": ("ID Dispositivo",   120),
            "mac":       ("MAC Address",      140),
            "ip":        ("IP Público",       120),
            "hostname":  ("Hostname",         130),
            "sistema":   ("Sistema",          120),
            "visto_em":  ("Última Atividade", 140),
        })
        self._dados_dispositivos = []

    # ── Aba: Sessões ──────────────────────────
    def _construir_aba_sessoes(self):
        frame = self.aba_sessoes

        barra = tk.Frame(frame, bg=CORES["fundo"])
        barra.pack(fill="x", pady=(10, 6))

        tk.Button(barra, text="🔒  Invalidar Sessão Selecionada",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["vermelho"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  command=self.invalidar_sessao).pack(side="right")

        colunas = ("email", "device_id", "ip", "criado_em")
        self.tree_sess = self._criar_tabela(frame, colunas, {
            "email":     ("Email",         250),
            "device_id": ("ID Dispositivo",160),
            "ip":        ("IP da Sessão",  140),
            "criado_em": ("Início Sessão", 160),
        })

    # ── Aba: Falhas / IPs suspeitos ───────────
    def _construir_aba_falhas(self):
        frame = self.aba_falhas

        barra = tk.Frame(frame, bg=CORES["fundo"])
        barra.pack(fill="x", pady=(10, 6))

        tk.Button(barra, text="🧹  Limpar IP Selecionado",
                  font=("Segoe UI", 10, "bold"),
                  bg=CORES["verde"], fg=CORES["branco"],
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  command=self.limpar_ip).pack(side="right")

        colunas = ("ip", "email", "tentativas", "ultima")
        self.tree_falhas = self._criar_tabela(frame, colunas, {
            "ip":         ("IP Bloqueado",    160),
            "email":      ("Email Tentado",   220),
            "tentativas": ("Nº Tentativas",   120),
            "ultima":     ("Última Tentativa",160),
        })

    def _criar_tabela(self, parent, colunas, config):
        frame = tk.Frame(parent, bg=CORES["fundo"])
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Custom.Treeview",
                        background=CORES["card"],
                        foreground=CORES["texto"],
                        fieldbackground=CORES["card"],
                        rowheight=32,
                        font=("Segoe UI", 10))
        style.configure("Custom.Treeview.Heading",
                        background=CORES["painel"],
                        foreground=CORES["sub"],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("Custom.Treeview",
                  background=[("selected", CORES["azul"])],
                  foreground=[("selected", CORES["branco"])])

        tree = ttk.Treeview(frame, columns=colunas, show="headings",
                            style="Custom.Treeview")

        for col in colunas:
            nome, larg = config[col]
            tree.heading(col, text=nome,
                         command=lambda c=col, t=tree: self._ordenar(t, c))
            tree.column(col, width=larg, minwidth=60)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        # Copiar ao clicar com botão direito
        menu = tk.Menu(self, tearoff=0, bg=CORES["card"],
                       fg=CORES["texto"], font=("Segoe UI", 10))
        menu.add_command(label="📋 Copiar valor",
                         command=lambda: self._copiar_celula(tree))

        tree.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))
        return tree

    def _ordenar(self, tree, col):
        dados = [(tree.set(k, col), k) for k in tree.get_children("")]
        dados.sort(reverse=getattr(self, f"_ord_{col}", False))
        for i, (_, k) in enumerate(dados):
            tree.move(k, "", i)
        setattr(self, f"_ord_{col}", not getattr(self, f"_ord_{col}", False))

    def _copiar_celula(self, tree):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if vals:
            self.clipboard_clear()
            self.clipboard_append(" | ".join(str(v) for v in vals))

    # ── Carregar dados ────────────────────────
    def atualizar_tudo(self):
        self.lbl_status.config(text="A carregar...")
        self.after(50, self._carregar_dados)

    def _carregar_dados(self):
        try:
            self._carregar_dispositivos()
            self._carregar_sessoes()
            self._carregar_falhas()
            self._atualizar_stats()
            agora = datetime.now().strftime("%H:%M:%S")
            self.lbl_status.config(
                text=f"✓ Atualizado às {agora}", fg=CORES["verde"])
        except Exception as e:
            self.lbl_status.config(
                text=f"Erro: {e}", fg=CORES["vermelho"])

    def _carregar_dispositivos(self):
        # Busca dispositivos + emails dos utilizadores
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/dispositivos?select=*",
            headers=headers_admin()
        )
        dispositivos = resp.json() if resp.status_code == 200 else []

        # Busca utilizadores para mapear user_id → email
        resp_u = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers_admin()
        )
        emails = {}
        if resp_u.status_code == 200:
            for u in resp_u.json().get("users", []):
                emails[u["id"]] = u["email"]

        self._dados_dispositivos = []
        for d in dispositivos:
            row = (
                emails.get(d.get("user_id"), d.get("user_id", "?")),
                d.get("device_id", "")[:16] + "…",
                d.get("mac_address", "—"),
                d.get("ip", "—"),
                d.get("hostname", "—"),
                d.get("sistema", "—"),
                formatar_data(d.get("visto_em")),
            )
            self._dados_dispositivos.append((d, row))

        self._preencher_tabela(self.tree_disp,
                               [r for _, r in self._dados_dispositivos])

    def _carregar_sessoes(self):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/sessoes?select=*",
            headers=headers_admin()
        )
        sessoes = resp.json() if resp.status_code == 200 else []

        resp_u = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers_admin()
        )
        emails = {}
        if resp_u.status_code == 200:
            for u in resp_u.json().get("users", []):
                emails[u["id"]] = u["email"]

        self._dados_sessoes = sessoes
        rows = []
        for s in sessoes:
            rows.append((
                emails.get(s.get("user_id"), "?"),
                s.get("device_id", "")[:16] + "…",
                s.get("ip", "—"),
                formatar_data(s.get("criado_em")),
            ))
        self._preencher_tabela(self.tree_sess, rows)

    def _carregar_falhas(self):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/login_falhas?select=*",
            headers=headers_admin()
        )
        falhas = resp.json() if resp.status_code == 200 else []

        # Agrupar por IP
        por_ip = {}
        for f in falhas:
            ip = f.get("ip", "?")
            if ip not in por_ip:
                por_ip[ip] = {"emails": set(), "ultima": f.get("criado_em")}
            por_ip[ip]["emails"].add(f.get("email", ""))
            if f.get("criado_em", "") > por_ip[ip]["ultima"]:
                por_ip[ip]["ultima"] = f.get("criado_em")

        self._dados_falhas = por_ip
        rows = []
        for ip, info in por_ip.items():
            rows.append((
                ip,
                ", ".join(filter(None, info["emails"])) or "—",
                len(falhas),
                formatar_data(info["ultima"]),
            ))
        self._preencher_tabela(self.tree_falhas, rows)

    def _atualizar_stats(self):
        for w in self.frame_stats.winfo_children():
            w.destroy()
        n_disp  = len(self._dados_dispositivos)
        n_sess  = len(self._dados_sessoes) if hasattr(self, "_dados_sessoes") else 0
        n_blq   = len(self._dados_falhas)  if hasattr(self, "_dados_falhas")  else 0

        self._stat_card(self.frame_stats, "Dispositivos",   str(n_disp), CORES["azul"])
        self._stat_card(self.frame_stats, "Sessões Ativas", str(n_sess), CORES["verde"])
        self._stat_card(self.frame_stats, "IPs Suspeitos",  str(n_blq),  CORES["vermelho"])

    def _preencher_tabela(self, tree, rows):
        tree.delete(*tree.get_children())
        for i, row in enumerate(rows):
            tag = "par" if i % 2 == 0 else "impar"
            tree.insert("", "end", values=row, tags=(tag,))
        tree.tag_configure("par",   background=CORES["card"])
        tree.tag_configure("impar", background=CORES["painel"])

    def _filtrar_dispositivos(self):
        termo = self.pesq_var.get().lower()
        filtrado = [r for _, r in self._dados_dispositivos
                    if termo in " ".join(str(v) for v in r).lower()]
        self._preencher_tabela(self.tree_disp, filtrado)

    # ── Ações ─────────────────────────────────
    def desvincular_dispositivo(self):
        sel = self.tree_disp.selection()
        if not sel:
            messagebox.showwarning("Nenhuma seleção",
                                   "Seleciona um utilizador na tabela.")
            return
        vals = self.tree_disp.item(sel[0], "values")
        email = vals[0]

        if not messagebox.askyesno(
            "Confirmar Desvinculação",
            f"Vais desvincular o PC da conta:\n\n"
            f"📧 {email}\n"
            f"🖥️ MAC: {vals[2]}\n"
            f"🌍 IP: {vals[3]}\n\n"
            f"O utilizador poderá fazer login noutro dispositivo.\n"
            f"Tens a certeza?",
        ):
            return

        # Encontrar user_id correspondente
        dado_real = next(
            (d for d, r in self._dados_dispositivos if r[0] == email), None
        )
        if not dado_real:
            messagebox.showerror("Erro", "Não foi possível identificar o utilizador.")
            return

        user_id = dado_real.get("user_id")

        # Apagar dispositivo
        r1 = requests.delete(
            f"{SUPABASE_URL}/rest/v1/dispositivos?user_id=eq.{user_id}",
            headers=headers_admin()
        )
        # Apagar sessão também
        r2 = requests.delete(
            f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{user_id}",
            headers=headers_admin()
        )

        if r1.status_code in (200, 204):
            messagebox.showinfo(
                "✅ Desvinculado",
                f"PC desvinculado com sucesso!\n\n"
                f"{email} pode agora fazer login noutro dispositivo."
            )
            self.atualizar_tudo()
        else:
            messagebox.showerror("Erro", f"Erro ao desvincular: {r1.text}")

    def forcar_logout(self):
        sel = self.tree_disp.selection()
        if not sel:
            messagebox.showwarning("Nenhuma seleção",
                                   "Seleciona um utilizador na tabela.")
            return
        vals = self.tree_disp.item(sel[0], "values")
        email = vals[0]

        dado_real = next(
            (d for d, r in self._dados_dispositivos if r[0] == email), None
        )
        if not dado_real:
            return

        user_id = dado_real.get("user_id")
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{user_id}",
            headers=headers_admin()
        )
        if r.status_code in (200, 204):
            messagebox.showinfo("✅ Logout Forçado",
                                f"{email} será desligado na próxima verificação.")
            self.atualizar_tudo()
        else:
            messagebox.showerror("Erro", f"Erro: {r.text}")

    def invalidar_sessao(self):
        sel = self.tree_sess.selection()
        if not sel:
            messagebox.showwarning("Nenhuma seleção",
                                   "Seleciona uma sessão na tabela.")
            return
        vals = self.tree_sess.item(sel[0], "values")

        dado_real = next(
            (s for s in self._dados_sessoes
             if s.get("ip") == vals[2]), None
        )
        if not dado_real:
            return

        user_id = dado_real.get("user_id")
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/sessoes?user_id=eq.{user_id}",
            headers=headers_admin()
        )
        if r.status_code in (200, 204):
            messagebox.showinfo("✅ Sessão Invalidada",
                                "O utilizador será desligado na próxima verificação.")
            self.atualizar_tudo()
        else:
            messagebox.showerror("Erro", f"Erro: {r.text}")

    def limpar_ip(self):
        sel = self.tree_falhas.selection()
        if not sel:
            messagebox.showwarning("Nenhuma seleção",
                                   "Seleciona um IP na tabela.")
            return
        vals = self.tree_falhas.item(sel[0], "values")
        ip = vals[0]

        if not messagebox.askyesno(
            "Desbloquear IP",
            f"Vais remover o bloqueio do IP:\n\n🌍 {ip}\n\nTens a certeza?"
        ):
            return

        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/login_falhas?ip=eq.{ip}",
            headers=headers_admin()
        )
        if r.status_code in (200, 204):
            messagebox.showinfo("✅ IP Desbloqueado",
                                f"O IP {ip} foi desbloqueado com sucesso.")
            self.atualizar_tudo()
        else:
            messagebox.showerror("Erro", f"Erro: {r.text}")


if __name__ == "__main__":
    PainelAdmin()
