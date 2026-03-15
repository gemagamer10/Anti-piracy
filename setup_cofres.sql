-- ============================================================
-- Adicionar ao setup_supabase_v2.sql — Tabela de Cofres
-- Corre no Supabase → SQL Editor
-- ============================================================

-- Tabela: cofres — guarda as chaves de encriptação dos vaults
CREATE TABLE IF NOT EXISTS cofres (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vault_id   TEXT NOT NULL UNIQUE,   -- nome do ficheiro .vault (ex: "Conteudo.vault")
    chave_enc  TEXT NOT NULL,          -- chave AES-256 em base64 (só o servidor tem)
    nome       TEXT,                   -- nome amigável
    criado_em  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cofres_vault_id ON cofres(vault_id);

-- Segurança: qualquer utilizador autenticado pode LER a chave do cofre
-- (o login já garante que é um utilizador legítimo)
ALTER TABLE cofres ENABLE ROW LEVEL SECURITY;

CREATE POLICY "cofres_select_auth"
    ON cofres FOR SELECT
    USING (auth.role() = 'authenticated');

-- Apenas o service_role (administrador) pode inserir/alterar/apagar
-- (o RLS não se aplica ao service_role — ele tem acesso total)
