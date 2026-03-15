-- ============================================================
-- BASE DE DADOS — Sistema Anti-Pirataria v2
-- Corre no Supabase → SQL Editor
-- ============================================================

-- Tabela: dispositivos (com informação completa de hardware)
CREATE TABLE IF NOT EXISTS dispositivos (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    device_id   TEXT NOT NULL,          -- Fingerprint SHA256 do hardware
    mac_address TEXT,                   -- MAC Address (ex: A1:B2:C3:D4:E5:F6)
    hostname    TEXT,                   -- Nome do PC na rede
    sistema     TEXT,                   -- OS + versão (ex: Windows 11 22H2)
    ip          TEXT,                   -- Último IP público registado
    visto_em    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)                     -- 1 dispositivo por conta
);

-- Tabela: sessões ativas
CREATE TABLE IF NOT EXISTS sessoes (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL,
    device_id     TEXT,
    ip            TEXT,
    criado_em     TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

-- Tabela: tentativas falhadas (anti-brute-force)
CREATE TABLE IF NOT EXISTS login_falhas (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ip         TEXT NOT NULL,
    email      TEXT,
    criado_em  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_falhas_ip ON login_falhas(ip);
CREATE INDEX IF NOT EXISTS idx_dispositivos_user ON dispositivos(user_id);
CREATE INDEX IF NOT EXISTS idx_sessoes_user ON sessoes(user_id);


-- ============================================================
-- SEGURANÇA (Row Level Security)
-- ============================================================
ALTER TABLE dispositivos  ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessoes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_falhas   ENABLE ROW LEVEL SECURITY;

-- Dispositivos
CREATE POLICY "disp_select" ON dispositivos FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "disp_insert" ON dispositivos FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "disp_update" ON dispositivos FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "disp_delete" ON dispositivos FOR DELETE USING (auth.uid() = user_id);

-- Sessões
CREATE POLICY "sess_select" ON sessoes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "sess_insert" ON sessoes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "sess_update" ON sessoes FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "sess_delete" ON sessoes FOR DELETE USING (auth.uid() = user_id);

-- Falhas (acesso público para registar antes do login)
CREATE POLICY "falhas_insert" ON login_falhas FOR INSERT WITH CHECK (true);
CREATE POLICY "falhas_select" ON login_falhas FOR SELECT USING (true);
-- O administrador usa a service_role key que ignora o RLS automaticamente


-- ============================================================
-- VISTA útil para o administrador (opcional)
-- Mostra um resumo de todos os utilizadores com dispositivos
-- ============================================================
CREATE OR REPLACE VIEW vista_admin AS
SELECT
    u.email,
    d.mac_address,
    d.hostname,
    d.sistema,
    d.ip          AS ultimo_ip,
    d.visto_em    AS ultima_atividade,
    d.device_id,
    d.user_id,
    CASE WHEN s.user_id IS NOT NULL THEN 'Ativa' ELSE 'Inativa' END AS sessao
FROM auth.users u
LEFT JOIN dispositivos d ON d.user_id = u.id
LEFT JOIN sessoes      s ON s.user_id = u.id
ORDER BY d.visto_em DESC;


-- ============================================================
-- LIMPEZA AUTOMÁTICA DE FALHAS ANTIGAS (+24h)
-- Descomenta se tiveres pg_cron ativo no Supabase Pro
-- ============================================================
-- SELECT cron.schedule(
--   'limpar-falhas-antigas',
--   '0 * * * *',
--   $$DELETE FROM login_falhas WHERE criado_em < now() - interval '24 hours'$$
-- );
