📊 PortalHub: Gestão Fiscal e Contábil

O PortalHub é um sistema interno e futuro portal do cliente desenvolvido para centralizar a gestão de dados fiscais (NFes, apuração do Simples Nacional) e otimizar a comunicação de obrigações contábeis.

Este projeto visa unificar a base de notas, automatizar o cálculo de impostos para conferência e, futuramente, prover uma experiência de transparência e checklist de documentos para os clientes.

🎯 Status Atual do Projeto: MVP Interno Concluído

A primeira fase, focada no Hub Interno para a equipe, foi concluída. O foco está agora na criação do Back-end com FastAPI e o Portal do Cliente.

⚙️ Funcionalidades Atuais (Hub Interno - Streamlit)

O módulo atual permite a gestão de notas fiscais e a apuração fiscal básica:

Busca e Visualização: Tela para buscar, filtrar e visualizar notas fiscais.

Edição de Notas: Formulário para editar dados de notas fiscais existentes.

Apuração Simples Nacional: Módulo dedicado para:

Cálculo e registro do RBT12.

Cálculo e registro da Alíquota Efetiva.

Cálculo da Guia (DAS/ISS) do Simples Nacional.

Conferência de Sequência: Ferramenta para verificar números de notas fiscais faltantes em uma sequência emitida (essencial para evitar omissão de receita).

Base de Dados: Utilização de PostgreSQL para persistência de todos os dados fiscais.

🗺️ Próximas Funcionalidades (Pós-MVP)

[ ] Incluir importação de NFSe padrão nacional (gov.br).

[ ] Implementar formulários de edição para Empresas e Sócios (atualmente via PgAdmin).

[ ] Melhorias de User Experience (UX) no cadastro (ex: limpar widgets após submissão).