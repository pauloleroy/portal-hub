-- Deletar tabela
DROP TABLE IF EXISTS notas CASCADE;

-- Deletar linhas notas
TRUNCATE TABLE notas RESTART IDENTITY CASCADE;

-- Soma notas mes empresas
SELECT SUM(valor_total)
FROM notas
WHERE empresa_id = 1
AND data_emissao BETWEEN '2025-07-01' AND '2025-07-31'
AND e_cancelada = false;

-- Selecionar nota especifica
SELECT * FROM notas WHERE numero = '202500000000384'

-- Descancelar nota
UPDATE notas
SET e_cancelada = false
WHERE numero = '202500000000247';

-- Soma ISS MES
SELECT SUM(valor_iss)
FROM notas
WHERE empresa_id = 1
AND data_emissao BETWEEN '2025-07-01' AND '2025-07-31'
AND e_cancelada = FALSE;