# Validação da preparação

## Evidências nativas

- Instalação inspecionada somente para leitura: `D:/Games/Who The Fuck Ate Grandma`.
- Engine: Unity `6000.2.9f1`, arquivo serializado v22, player Windows IL2CPP, Adventure Creator.
- `resources.assets` original: 43.959.176 bytes; SHA-256 `17599bf6650a62f79a120424ef5c0933cfdf05107c3b32e6946dd007377347d1`.
- 3.686 IDs únicos no SpeechManager; a revisão estrutural das cenas acrescentou 84 mensagens não vazias sem ID de localização. Uma ação com mensagem vazia não foi transformada em tarefa linguística.
- Catálogo final de preparação: **3.770 unidades, oito lotes (7 × 500 + 270), todas pendentes**. O estado corrente está no manifesto/status.
- Fontes: 17 arquivos nativos preservados em EN, com caminhos originais. A reconstrução sem alterações retorna os bytes de cada fonte. Uma versão completa do pacote precisa de 12 arquivos: recurso central e 11 cenas com registros de fala adicionados.
- `scene-audit.json` guarda a varredura heurística inicial e seus candidatos; não deve ser usado como contagem final. A contagem e os vínculos finais vêm do parser de ActionSpeech.

## Política de idioma solicitada

**PT-BR substitui o inglês no seletor; francês preservado.** O teste verifica a lista nativa: inglês original desativado, PT-BR como primeira tradução e francês como segunda. Também verifica que as strings francesas originais continuam iguais, os textos ingleses de origem são preservados internamente e os objetos/lógica não são renomeados.

O registro das falas sem ID altera somente o inteiro de localização de cada ação. O texto original e a referência de falante permanecem iguais; o ID novo é conferido com a SpeechLine acrescentada. Em francês, essas falas conservam o inglês que já era seu fallback, sem tradução francesa inventada.

Fontes técnicas primárias: [Language](https://adventurecreator.org/scripting-guide/class_a_c_1_1_language.html), [SpeechLine](https://adventurecreator.org/scripting-guide/class_a_c_1_1_speech_line.html), [ActionSpeech](https://adventurecreator.org/scripting-guide/class_a_c_1_1_action_speech.html) e [explicação do desenvolvedor sobre desativar o idioma original](https://adventurecreator.org/forum/discussion/16040/parser-failure-at-line-2-expected-closing). A funcionalidade em jogo continua pendente; conferir a estrutura não equivale a afirmar que o jogo foi executado.

## Comandos e testes

```sh
python -B -m unittest discover -s translation-work/tests -v
python -B translation-work/toolkit.py check
python -B translation-work/toolkit.py doctor --target host
python -B translation-work/toolkit.py update-sources --game-root "D:/Games/Who The Fuck Ate Grandma" --dry-run
python -B translation-work/toolkit.py gc --dry-run
python -B translation-work/toolkit.py build
```

`build` no projeto real deve falhar enquanto houver entradas pendentes, sem criar PTBR. Os builds completos e publicações HTTP dos testes usam **fixtures sintéticas** em diretórios temporários e um servidor mock local, nunca os lotes reais ou a API pública de publicação.

**Resultados executados no Windows:** rodada completa com **49 testes em 529,139 s**, sem falhas e com **um skip** de criação de symlink por restrição do sistema. Após o refinamento da associação de falantes, foram reexecutados **seis testes de fontes/registro de idiomas**, **oito de Release** e **seis de documentação**, todos aprovados. O teste adicional de associação por referência nativa integra agora a suíte. O cenário de 500 aplicações foi executado na rodada completa; não foi repetido por uma alteração que afetou apenas metadados de falante no build.

No projeto real: `check` aprovado com 3.770 pendências; `doctor --target host` aprovado; `update-sources --dry-run` retornou `unchanged`; `gc --dry-run` não identificou poda necessária; `build` retornou código 1 e preservou a ausência de PTBR. Os hashes dos 17 originais instalados coincidem com EN. O relatório `native-proof.json` registra ainda uma reconstrução dos 12 arquivos em memória, usando valores de referência originais, para validar todos os vínculos e a conservação do francês. Essa prova não constitui tradução nem grava saída PTBR.

A suíte cobre extração, lotes, campos imutáveis, aplicação parcial, substituição explícita, geração incorreta, fontes/contextos alterados, adição/remoção/reordenação, EN substituído manualmente, fontes desconhecidas, no-op, fingerprints LF/Git, corrupção binária, controle de disco, travas, staging interrompido, recuperação/rollback, caminhos inseguros, receipts corrompidos e retenção. O cenário de **500 aplicações pequenas em 101 lotes** verifica que os outros lotes mantêm bytes/mtime, no máximo dez snapshots são retidos e o histórico desse cenário permanece abaixo de 100 KiB.

Os testes de Release executam o cliente HTTP: raiz correta da API, tags, rascunho, upload, confirmação de digest/tamanho, publicação, primeira versão, patch seguinte, repetição idempotente, draft interrompido, asset inesperado, erro 403/404, retry de GET, tag órfã/não ancestral e avanço concorrente da branch. São testes locais; nenhuma Release foi publicada.

O teste que cria um symlink real pode ser ignorado pelo Windows quando a conta não tem privilégio de criação. A validação de escape de caminhos continua coberta; não se afirma que a criação de symlink foi autorizada ou testada nesse ambiente.

## Pesquisa, links e documentos

A autoria, sinopse e idiomas foram pesquisados na [página oficial da Steam](https://store.steampowered.com/app/1756100/); o briefing também usa IDs e textos do próprio jogo. Banner oficial, três badges, portal de traduções, Discord Vai Brasil e páginas de Releases/issues retornaram HTTP 200 na verificação de 26/10/2026. Isso confirma acesso aos destinos naquela consulta, não disponibilidade futura ou existência de um pacote publicado.

O `LICENSE` foi obtido do [legal code oficial completo em texto](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt), sem edição: 20.850 bytes, SHA-256 `e66c269d4819aaab34b49ef5220c4ddab6756f21bb5180761a4eb8561f2b7bbd`. A permissão adicional em inglês foi adaptada do documento existente em `D:/Users/ysi/Documents/Git/star-dynasties-gold-traducao-portugues-brasileiro/GAME-DEVELOPER-PERMISSION.md`, referência indicada pelo mantenedor. Consentimento de terceiros não foi presumido.

O Markdown, a hierarquia, os textos alternativos, os links e os badges foram revisados e têm regressões automatizadas. A prévia HTML foi gerada com um renderer disponível no ambiente de desenvolvimento, mas **a inspeção visual não foi concluída**: o ambiente não tinha um navegador headless instalado e a política do navegador disponível bloqueou `file://`. Não houve tentativa de contornar essa política. O script de preview é opcional de desenvolvimento e não faz parte das dependências do toolkit.

## Limitações que permanecem

- **Ubuntu 24.04 ARM64:** execução real pendente. Após clone/pull, o tradutor executa uma única vez `python3 -B translation-work/toolkit.py doctor`; se falhar, encaminha o erro e não inicia tradução.
- **Jogo:** nenhuma execução, instalação, validação visual de acentos, verificação de saves ou teste de jogabilidade foi realizado. O suporte a Unicode no arquivo não prova glifos no atlas.
- **GitHub:** workflows preparados e cliente testado por mock; execução real remota e publicação não realizadas. A proteção de branch para exigir aceite de contribuição depende de configuração do mantenedor.
- **Redistribuição:** autorização para recursos proprietários não fornecida. O publisher falha antes de chamadas de publicação enquanto `redistribution.authorized` estiver falso ou faltar a evidência. Verifique também o direito de publicar as cópias originais em EN antes de tornar este conteúdo público.
- **Formato:** o adaptador é específico ao perfil analisado; novas cenas, layouts, mensagens dinâmicas sem vínculo ou compilação incompatível exigem revisão. Não há suporte declarado a outros mods/plataformas.
- **Entrega Git:** arquivos preparados localmente; sem commit ou push automático.
