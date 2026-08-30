# Fecho de Caixa V2

A V1 permanece em `caixa/index.html` e não deve ser alterada por este projeto.

## Objetivo

Criar uma V2 do fecho de caixa com separação clara entre:

1. dados automáticos (Sifarma, Cashlogy, logs dos TPAs);
2. dados manuais (TPAs sem fio, Finanfarma, transferências, apuro contado, responsáveis e comentários);
3. reconciliação e validações;
4. análise de taxas e histórico.

## Princípio de compatibilidade

- A V1 continua publicada e operacional.
- A V2 vive numa rota/pasta separada (`caixa-v2/`).
- A V2 pode ler os mesmos JSON já publicados pela V1 durante a transição.
- Nenhuma alteração à V1 é necessária para desenvolver e testar a V2.

## Estado atual identificado na V1

A V1 já contém:

- leitura dos ficheiros `data/fecho/hoje_<farmacia>.json` e `serie_<farmacia>.json`;
- detalhe histórico por dia;
- conciliação entre Sifarma e Cashlogy;
- configuração de TPAs em `data/config/tpas.json`;
- introdução e edição manual de TPAs;
- OCR de talões via Cloudflare Worker;
- cálculo de bruto, líquido e taxa por TPA;
- TPA Finanfarma físico com lógica de custo mensal;
- responsáveis e comentário;
- validação de desvios fora da tolerância;
- análise de vendas e taxas.

## Problema técnico principal da V1

A interface, regras de negócio, acesso a dados, OCR e persistência estão concentrados num único `caixa/index.html`. Isso aumenta o risco de regressões e torna difícil acrescentar uma fonte local de dados dos TPAs.

## Arquitetura V2 proposta

```text
caixa-v2/
  index.html
  css/
    app.css
  js/
    app.js
    api.js
    state.js
    reconciliation.js
    tpa.js
    validation.js
    ui.js
  docs/
    local-tpa-agent.md
```

### Fluxo de dados

```text
Sifarma ---------\
Cashlogy ----------> dados automáticos ----\
Logs TPA (PC) ----/                       \
                                           > motor de reconciliação -> UI V2
TPA wireless ----\                       /
Finanfarma ------- > dados manuais -------/
Transferências ---/
```

## V2 — ecrã de fecho recomendado

### 1. Cabeçalho

- Farmácia
- Dia do fecho
- Estado: `Em curso`, `Conciliado`, `Desvio`, `Incompleto`

### 2. Resumo principal

Mostrar imediatamente:

- Total Sifarma
- Numerário real
- Cartões / TPA
- Outras formas de pagamento
- Diferença de caixa

### 3. Cartões / TPAs

Cada terminal deve mostrar:

- identificador do TPA;
- posto associado;
- origem: `LOG`, `TALÃO/OCR` ou `MANUAL`;
- bruto;
- líquido;
- nº de operações;
- comissão €;
- taxa efetiva %;
- estado de validação.

Prioridade das fontes:

1. log automático do posto;
2. talão/OCR;
3. introdução manual.

Nunca sobrescrever silenciosamente um valor manual. Se existirem duas fontes, comparar e pedir validação quando não coincidirem.

### 4. Reconciliação

Separar duas reconciliações:

**Caixa operacional**

`numerário + cartões + outras formas - total Sifarma`

**TPA / acquiring**

`bruto - líquido = custo do TPA`

Isto evita misturar uma diferença de caixa com uma diferença de liquidação/comissão.

### 5. Validações

- líquido não pode ser superior ao bruto;
- duplicados por terminal/data/identificador da operação;
- diferença OCR vs log;
- terminal não configurado;
- TPA configurado mas sem dados nesse dia;
- comentário obrigatório acima da tolerância;
- indicação explícita quando existem valores estimados.

## Agente local para os logs dos TPAs

O acesso aos logs não deve ser feito diretamente pelo site/browser. Deve existir um pequeno agente no PC da farmácia.

Responsabilidades:

1. vigiar as pastas de log dos postos;
2. ler apenas novos registos;
3. normalizar os movimentos;
4. excluir dados de cartão desnecessários;
5. gerar um resumo diário por TPA;
6. enviar/publicar apenas os campos necessários à aplicação.

Formato normalizado sugerido:

```json
{
  "farmacia": "Aroeira",
  "data": "2026-08-30",
  "terminal": "01123224",
  "posto": "002",
  "origem": "log",
  "bruto": 1234.56,
  "liquido": 1229.40,
  "operacoes": 71,
  "taxa": 5.16
}
```

Não guardar PAN/número de cartão, CVV, track data ou outros dados de pagamento sensíveis.

## Trabalho a executar no PC via Codex

Para construir o parser real, o Codex no PC deve receber acesso a uma pasta de logs e executar:

1. inventário das pastas/ficheiros relevantes;
2. recolha de 2–3 exemplos de dias diferentes;
3. identificação de formato, encoding e rotação dos logs;
4. identificação dos campos úteis;
5. desenvolvimento de parser somente leitura;
6. testes contra totais conhecidos dos talões;
7. geração de JSON normalizado;
8. só depois, automatização da recolha.

## Critério para considerar a integração de um TPA segura

O total bruto diário calculado pelo parser deve coincidir com o total do talão/fecho do terminal em vários dias consecutivos antes de a V2 passar a tratar essa fonte como automática.

## Próximos incrementos

1. criar shell visual da V2;
2. extrair o motor de cálculo/reconciliação da V1 para módulos independentes;
3. manter compatibilidade de leitura dos JSON atuais;
4. adicionar modelo de fonte dos TPAs (`log`, `ocr`, `manual`);
5. ligar o primeiro posto real via agente local;
6. repetir para os restantes postos;
7. adicionar dashboard consolidado das farmácias e custo blended dos TPAs.
