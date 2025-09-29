CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) UNIQUE NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    regime_tributario VARCHAR(20) NOT NULL, -- 'simples', 'presumido', 'real'
    detalhes_tributarios VARCHAR(100),      -- 'Anexo III', 'Anexo III, V', '32%', etc.
    ativo BOOLEAN DEFAULT true,
    data_abertura DATE,
    data_encerramento DATE,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE socios (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(20) NOT NULL,
    identificador_prof VARCHAR(50),  -- ex: CRM, CRO, OAB, etc.
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id),
    socio_id INT REFERENCES socios(id), -- opcional, se quiser vincular a um sócio específico
    tipo VARCHAR(50) NOT NULL, -- "nfse_pbh", "nfe", "danfe", etc.
    numero VARCHAR(50) NOT NULL,
    chave VARCHAR(255) NOT NULL, -- chave de acesso ou identificador único
    data_emissao DATE NOT NULL,
    data_competencia DATE, -- mês/ano da competência
    prestador_nome VARCHAR(255),
    prestador_doc VARCHAR(20),
    tomador_nome VARCHAR(255),
    tomador_doc VARCHAR(20),
    valor_total NUMERIC(12,2),
    valor_iss NUMERIC(12,2),
    retencoes_json JSONB, -- ex: IR, INSS, PIS/COFINS/CSLL
    xml_text TEXT, -- XML bruto para consultas futuras
    e_cancelada BOOLEAN DEFAULT FALSE, -- flag de cancelamento
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
