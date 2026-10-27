# Registro da revisão textual

Tradução manual iniciada em 27/10/2026 a pedido do mantenedor, com lotes de 250 e meta de acabamento profissional. Este registro descreve revisão linguística, não execução do jogo, certificação externa ou teste visual de fontes.

## Lotes 0001 e 0002

- 500 entradas traduzidas, em dois lotes completos de 250, com comparação de EN, FR e contexto. Os demais lotes continuam pendentes; `status` é a autoridade de contagem corrente.
- Foram escritas diretrizes de voz, agressividade, concordância e ritmo, e um glossário contextual. Não houve tradução por API, preenchimento provisório ou substituição automática de palavras.
- A reorganização em 16 lotes preservou exatamente os registros anteriores, a geração aceita das fontes e todos os IDs. O recibo está em `rebatch-250.json`.
- Após a primeira redação, houve revisão das falas em conjunto. Entre os ajustes do lote 0001: explicitar que se trata de roubar brinquedo de uma criança, em vez de uma formulação ambígua que poderia sugerir sequestro; preservar a progressão de muito realista para realista demais; e esclarecer que o aparelho auditivo ficava desligado durante todo o intervalo da piada.

## Decisões de maior risco conferidas

| Entradas | Decisão e motivo |
| --- | --- |
| 28/60/254–258/458 | A pergunta recorrente mantém o palavrão. Os cinco fragmentos dramáticos viram QUEM / FOI QUE / COMEU / A VOVÓ, / PORRA?, mantendo as cinco entradas e a ordem natural brasileira. Conferir o ritmo visual quando houver teste autorizado. |
| 364–371 | Mantidas as interrupções do diálogo com Gustave: frase cortada, POR FAVOR, nova interrupção, CALA / A BOCA. Não juntar nem eliminar unidades. |
| 44–45 | Mantido o jogo entre a harmonia familiar que sai voando e os balões de hélio. O caractere invisível inicial herdado do EN não foi reproduzido no texto visível PT-BR. |
| 55 | 350 milhas foram localizadas para aproximadamente 560 quilômetros. Não se adotaram os 500 quilômetros divergentes do francês. |
| 326–333 | Mantida a repetição exaustiva de salsicha; não encurtar a discussão a ponto de eliminar a piada. |
| 215–216/229/303–306 | Concordância baseada em parentesco e pronomes explícitos: protagonista masculino, Josiane feminina; as pessoas mencionadas recebem a própria concordância. |
| 137/219 | Mantidas as duas medidas da fonte inglesa: 18h47 e 18h. A referência francesa repete 18h47, mas não foi usada para uniformizar a diferença. |
| 142–145 | Conservadas as duas pernas amputadas do instrutor na fonte inglesa, em vez da variante francesa de uma perna. Humor mórbido não foi censurado. |
| 287–289 | Fórmula e resposta original de 48,4 anos preservadas. A resposta matematicamente errada faz parte do diálogo; não consertar por cálculo automático. |
| 308–309 | José é o nome errado proposital, seguido da correção de Henri; não normalizar os dois nomes para o mesmo. |
| 318/442/489 | Bell é a tampa da refeição, confirmada por Couvercle; não traduzir como sino. |
| 517–519 | A exclamação em três segmentos foi adaptada para Meu / Deus / do céu., mantendo as três entradas. Conferir a apresentação em jogo quando autorizada. |

## Limites e próximos passos

A revisão textual não demonstra encaixe em tela, acentos renderizados ou temporização dos fragmentos. Nenhum arquivo da instalação foi alterado. PTBR nativo só pode ser gerado pelo build completo, após terminar e revisar todas as entradas. O próximo lote é `batch-0003.jsonl`; não recomeçar nem sobrescrever os lotes concluídos.
