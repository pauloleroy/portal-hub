CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) UNIQUE NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    regime_tributario VARCHAR(20) NOT NULL, -- 'simples', 'presumido', 'real'
    detalhes_tributarios VARCHAR(100),      -- 'Anexo III', 'Anexo III, V', '32%', etc.
    data_abertura DATE,
    email TEXT,
    telefone VARCHAR(20),
    situacao_cadastral VARCHAR(50),
    notificacao_ativa BOOLEAN DEFAULT TRUE,
    is_matriz BOOLEAN DEFAULT TRUE,
    matriz_id INT REFERENCES empresas(id),
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE socios (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(20),
    identificador_prof VARCHAR(50),  -- ex: CRM, CRO, OAB, etc.
    email VARCHAR(255),
    telefone VARCHAR(20),
    percentual_participacao NUMERIC(5,2),
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE notas (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id),
    socio_id INT REFERENCES socios(id), -- opcional, se quiser vincular a um sócio específico
    tipo VARCHAR(50) NOT NULL, -- "nfse_pbh", "nfe", "danfe", etc.
    numero VARCHAR(50) NOT NULL,
    chave VARCHAR(255) NOT NULL UNIQUE, -- chave de acesso ou identificador único
    data_emissao DATE NOT NULL,
    data_competencia DATE, -- mês/ano da competência
    mes_ref DATE NOT NULL,
    prestador_nome VARCHAR(255),
    prestador_doc VARCHAR(20),
    tomador_nome VARCHAR(255),
    tomador_doc VARCHAR(20),
    valor_total NUMERIC(12,2),
    valor_iss NUMERIC(12,2),
    retencoes_json JSONB, -- ex: IR, INSS, PIS/COFINS/CSLL
    cfop VARCHAR(10),
    xml_text TEXT, -- XML bruto para consultas futuras
    link_download TEXT,
    e_cancelada BOOLEAN DEFAULT FALSE, -- flag de cancelamento
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE simples_apuracoes (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    competencia DATE NOT NULL,  -- dia 1 do mês ref (ex: 2025-09-01)
    faturamento_mensal NUMERIC(14,2),
    anexo VARCHAR(20) NOT NULL,  -- "Anexo III", "Anexo V", etc.
    rbt12 NUMERIC(14,2),
    aliquota_efetiva NUMERIC(12,8), 
    impostos JSONB,
    retencoes NUMERIC(12,2),
    valor_estimado_guia NUMERIC(12,2),
    valor_guia_oficial NUMERIC(12,2),
    diferenca NUMERIC(10,2),
    data_calculo TIMESTAMP DEFAULT now(),
    UNIQUE (empresa_id, competencia)
);
