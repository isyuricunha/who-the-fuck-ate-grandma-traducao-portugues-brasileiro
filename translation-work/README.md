# Guia técnico da tradução

## Começo rápido no Ubuntu 24.04 ARM64

Depois do clone/pull normal do Git, execute **um único preflight**, a partir da raiz:

```sh
python3 -B translation-work/toolkit.py doctor
```

Requer Python 3.10 ou posterior e sua biblioteca padrão. Não usa Mono, .NET, DLLs auxiliares, pip, serviços externos ou executáveis Windows. O preflight verifica arquitetura Linux ARM64/aarch64, recibos de integridade encadeados, fonte aceita, lotes e uma fixture nativa válida, incluindo leitura, reconstrução sem perdas e strings Unicode maiores. Ele não traduz, instala, altera os originais nem cria PTBR. Se falhar, pare antes de traduzir e encaminhe o erro exato ao responsável pelo toolkit. Não reinstale pacotes nem regenere hashes para contornar o erro.

**Verificação de plataforma:** desenvolvimento e testes iniciais executados no Windows com Python 3.14. Em 27/10/2026, `doctor`, `check`, `build` e `verify-output` passaram no Ubuntu ARM64/aarch64 real, com Python 3.12.3. O teste de execução do jogo no Windows permanece pendente. Para repetir o preflight no Windows: `python -B translation-work/toolkit.py doctor --target host`.

Leia o [briefing já pesquisado e escrito durante a engenharia](docs/briefing-do-jogo.md), o [fluxo de tradução](docs/fluxo-de-traducao.md) e a [descrição do formato](docs/formato-localizacao.md). O tradutor mantém o glossário e as diretrizes; a pesquisa inicial não ficou delegada à tradução.

## Estado da preparação

O catálogo contém **3.770 registros**, organizados em **16 lotes: 15 × 250 + 20**, conforme a solicitação de tradução manual de 27/10/2026: 3.686 entradas do SpeechManager e **84 falas não vazias sem ID de tradução** nas cenas. Outra ação sem ID tem mensagem vazia e não é unidade linguística. Os lotes começaram com PTBR vazio e a reorganização preservou todos os campos e IDs. A auditoria não usou deduplicação por frase. Há cenas antigas e textos potencialmente não usados em execução: a presença no arquivo não prova visibilidade atual. Consulte `status` e o [registro de revisão textual](reports/translation-review.md) para acompanhar o trabalho.

| Tipo nativo | Entradas |
| --- | ---: |
| Speech | 3.037 |
| Hotspot | 223 |
| DialogueOption | 201 |
| MenuElement | 97 |
| Character | 49 |
| InventoryItem | 44 |
| Variable | 15 |
| JournalEntry | 11 |
| HotspotPrefix | 5 |
| CursorIcon | 4 |

A tabela acima discrimina as 3.686 entradas centrais. As 84 falas adicionais também são `Speech` e têm identidades por arquivo/PathID/campo. Fontes gerenciadas: `resources.assets` e `level0` até `level15`, preservados em EN. O build publica somente os 12 arquivos efetivamente necessários: `resources.assets`, `level2` e `level4` até `level13`.

**Estado em 27/10/2026:** todos os **3.770 registros estão traduzidos**, sem pendências, e o build completo criou `PTBR/` com os 12 recursos nativos esperados. `verify-output` aprovou o pacote; ele ainda não foi instalado nem testado no jogo. Não há pacote parcial e não foi usado preenchimento automático de textos. Saídas sintéticas dos testes ficam em diretórios temporários, fora dos lotes reais.

## Organização e propriedade

- `EN/Who the fuck ate grandma_Data/`: cópias originais aceitas de `resources.assets` e das 16 cenas, binárias e somente leitura para o fluxo de tradução.
- `translation-work/translations/`: fonte catalogada, manifesto e JSONL canônicos. Somente `PTBR` é editável nos registros.
- `translation-work/docs/`: pesquisa, regras técnicas e decisões linguísticas do tradutor.
- `translation-work/history/`: diffs duráveis das atualizações de fonte, incluindo valores anteriores removidos/alterados. Devem acompanhar os commits de sincronização.
- `translation-work/reports/`: relatório da última sincronização. Compare sua geração com `status`; ele não representa necessariamente a última tentativa fracassada.
- `translation-work/.state/`: recibos e cópias locais de recuperação, ignorados pelo Git.
- `PTBR/Who the fuck ate grandma_Data/`: saída nativa completa. O PT-BR substitui o inglês no seletor e o francês é preservado. O build registra as falas sem ID no sistema nativo e altera apenas os vínculos de localização nas respectivas cenas.
- `translation-work/build-manifest.json`: recibo de build, fora da instalação, que acompanha o commit de PTBR.

Não existe segundo repositório. O caminho da instalação fornecida serve só para leitura. O toolkit não escreve no jogo; nenhuma opção instala arquivos.

## Comandos

Todos resolvem a raiz pelo próprio arquivo, inclusive quando chamados de outro diretório. As respostas são JSON; erros retornam código 1 e `apply` com rejeições retorna 2.

```sh
python translation-work/toolkit.py status
python translation-work/toolkit.py resume
python translation-work/toolkit.py check
python translation-work/toolkit.py diff
python translation-work/toolkit.py apply /caminho/payload.json
python translation-work/toolkit.py apply /caminho/revisao.json --replace
python translation-work/toolkit.py build
python translation-work/toolkit.py verify-output
python translation-work/toolkit.py gc --dry-run
python translation-work/toolkit.py gc
python translation-work/toolkit.py recover
python translation-work/toolkit.py recover --rollback ID_DA_TRANSACAO
```

`status` e `resume` não carregam o parser nativo nem reconstroem arquivos. `check` verifica estrutura e fonte, permitindo tradução incompleta. `build` exige todos os PTBR preenchidos e validados; valida o binário reaberto e promove saída e recibo na mesma transação recuperável. `verify-output` confere o catálogo, a geração, os lotes, a conclusão, os hashes e o inventário, sem reconstruir o nativo. Progresso nunca chama build implicitamente.

Exemplo de payload (substitua geração e ID pelos valores reais do lote; o texto ilustrativo não é tradução de uma entrada real):

```json
{
  "generation": "copie o valor generation do manifesto",
  "entries": [
    {"id": "copie o id completo da entrada", "PTBR": "texto revisado pelo tradutor"}
  ]
}
```

IDs desconhecidos, duplicados e geração incorreta rejeitam o payload antes de gravar. Entradas com erro de texto são relatadas individualmente; as válidas podem ser aceitas. Valores existentes ficam protegidos, salvo `--replace` explícito. Repetir um valor já aceito não gera nova transação. Edição direta dos JSONL é possível, preservando os outros campos; o próximo `check` fiscaliza isso, mas edições manuais precisam do Git para recuperação anterior ao toolkit.

## Importar e atualizar fontes

`extract` é apenas para a primeira preparação e recusa sobrescrever progresso existente. Já foi executado neste repositório.

```sh
python translation-work/toolkit.py update-sources --dry-run
python translation-work/toolkit.py update-sources --game-root "D:/Games/Who The Fuck Ate Grandma" --dry-run
python translation-work/toolkit.py update-sources --game-root "D:/Games/Who The Fuck Ate Grandma"
python translation-work/toolkit.py sync
python translation-work/toolkit.py sync --source-root "/caminho/raiz-com-layout-original"
python translation-work/toolkit.py diff --source-root "/caminho/raiz-com-layout-original"
```

A descoberta lê bibliotecas Steam e o candidato local explicitamente configurado. Somente um candidato verificado pode ser aceito; nenhum ou vários resulta em erro com `--game-root`. O servidor não consegue descobrir um jogo instalado em outro computador. Para importação pelo jogo, exige `app.info` da identidade correta e a árvore gerenciada completa. A árvore passa pelo parser restrito e pela reconstrução sem perdas. Não se copiam executáveis, a instalação inteira, áudio nem arquivos estranhos ao escopo.

Este perfil exige uma árvore completa dos 17 recursos: `--source-file` isolado falha com orientação para `--source-root` ou `--game-root`. Não se mistura silenciosamente um arquivo novo com cenas de outra versão. Cenas extras ou ausentes também bloqueiam o import, exigindo revisão do perfil. `source-catalog.json` preserva a fonte aceita mesmo quando EN foi trocado manualmente.

`sync` e `update-sources` usam o mesmo reconciliador. Se EN foi substituído manualmente, o catálogo aceito persistido nos JSONL/manifesto continua disponível para o diff. Fonte/contexto idênticos preservam PTBR e lote; mudança de posição só atualiza o localizador; fonte, francês ou contexto relevante alterados esvaziam somente as entradas afetadas e guardam os valores antigos no histórico. Remoções são registradas; novos IDs entram pendentes. Não há reaproveitamento por semelhança textual. Um arquivo grande alterado não invalida tudo.

Lotes existentes não são reempacotados para tapar buracos. Novas entradas usam a capacidade final disponível e depois lotes novos. Ordem de reconstrução vem da tabela nativa, não da ordem física do lote. Ausência de arquivo, formato diferente, IDs repetidos, metadados de idioma desconhecidos ou edição concorrente causam erro. Uma atualização pode tornar o último PTBR obsoleto, mas não o substitui.

## Integridade e portabilidade

`.gitattributes` é estabelecido antes dos hashes: scripts e metadados próprios usam UTF-8/LF; EN, PTBR e fixtures binárias usam `-text`. Os hashes de metadados usam a representação LF equivalente ao blob do Git; hashes binários usam os bytes exatos. A cadeia `engine-shapes.json → toolchain.json → runtime-support.json` também cobre o adaptador, suas dependências locais e a política do projeto. Mudanças legítimas de código/perfil precisam de revisão e novo recibo pelo desenvolvedor, nunca revalidação cega pelo tradutor.

O catálogo aceito e o manifesto impedem modificar EN/contexto silenciosamente. Isso detecta inconsistências e adulterações acidentais; não é assinatura criptográfica contra um autor que reescreva todos os recibos. O recibo de build é um contrato de proveniência com o processo testado, não um certificado independente de jogabilidade.

## Recuperação, disco e limpeza

Operações de escrita usam trava exclusiva. Uma edição em um lote grava e copia para rollback **somente esse lote**, sem copiar os demais ou atualizar o manifesto sem necessidade. O diário registra hashes anteriores/posteriores, staging e status; uma operação interrompida bloqueia novas escritas. `recover` restaura a geração anterior quando os arquivos ainda correspondem aos estados previstos; conflito com edição externa exige inspeção, sem sobrescrita automática. Travas de processo vivo não são quebradas.

Retenção padrão: **10 transações concluídas e 512 MiB**, configuráveis em `project.json` mediante revisão dos recibos. A transação mais recente é preservada. Não se podam transações pendentes, recibos corrompidos, caminhos inseguros ou backups adulterados. `gc --dry-run` só lê; `gc` aplica a política sob a mesma trava. Antes de escrever, são estimados staging/rollback e margem de disco. Uma transação individual acima do orçamento falha com diagnóstico. `status` mostra contagem, bytes e limites.

O histórico local é recuperação curta, não substituto do Git. Faça commits de progresso por lotes e inclua históricos de sync. Não há commit nem push automático. Transações concluídas antigas são limitadas; edições manuais não executadas pelo toolkit não ganham backup retroativo.

## Releases automáticas

`.github/workflows/release.yml` responde a mudanças de `PTBR/**` na branch principal e a disparo manual explícito. Commits de JSONL/EN/README não publicam. O primeiro build completo autorizado produz **v1.0.0**; o próximo conteúdo diferente incrementa patch (**v1.0.1**). Reexecuções iguais não criam versões. A trava de concorrência, verificação do HEAD atual, ancestralidade das tags e rascunhos retomáveis evitam colisões; conflitos falham visivelmente.

O cliente HTTP é exercitado por mock local, inclusive criação de draft, upload, confirmação do SHA-256 e publicação. O changelog compara registros e recursos com a versão anterior, com categorias reais, links de download e comunidade. O único anexo é `PTBR.zip`: arquivos nativos na raiz do ZIP, sem `PTBR/` e sem documentos/recibos anexados. Não há segundo build ou upload manual.

**Publicação:** o workflow do GitHub empacota somente uma saída nativa já construída e validada; não reconstrói nem traduz na CI. A configuração `redistribution.authorized` deve estar ativada pelo mantenedor. Não é exigido campo documental adicional na configuração, mas isso não substitui a necessidade de ter direitos para redistribuir arquivos proprietários do jogo. A licença da tradução não concede direitos sobre os recursos originais. A publicação remota deve ser confirmada na página de Releases.

LICENSE contém o legal code oficial completo CC BY-NC-SA 4.0. GAME-DEVELOPER-PERMISSION.md é uma concessão adicional, em inglês, sobre direitos efetivamente autorizados; CONTRIBUTING.md e o template/check de PR exigem aceite afirmativo. Configure a proteção remota da branch para exigir o check de consentimento. Não foi aplicada uma licença nova a software de terceiros nem escolhida uma licença adicional para o código novo.

## Política do README público

O README da raiz é voltado ao jogador, com arte oficial e links estáveis. Contagens, diagnósticos, versões correntes e pendências ficam aqui, nos manifestos e nas notas de Release. A primeira publicação não exige editar marcador ou disponibilidade no README; CI não o reescreve. Só fatos novos relevantes ao jogador justificam alteração. Preparação, tradução completa, build validado, publicação e teste em jogo são estados distintos.

## Testes e limites

```sh
python -B -m unittest discover -s translation-work/tests -v
```

Consulte [validacao.md](docs/validacao.md) para resultados e limitações verificadas. A toolkit e o build foram validados no servidor ARM64, mas não houve instalação, teste em jogo, commit, push ou Release nesta conclusão da tradução.
