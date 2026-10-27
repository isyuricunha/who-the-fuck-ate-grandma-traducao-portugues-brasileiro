# Fluxo manual e retomada

1. Faça clone/pull e execute `python3 -B translation-work/toolkit.py doctor` no Ubuntu 24.04 ARM64. Se falhar, encaminhe o erro e pare; nenhuma tradução ou instalação é feita por esse comando.
2. Leia o briefing já pesquisado e escrito durante a engenharia, o README técnico e o formato. Não é necessário produzir a pesquisa inicial do zero.
3. Registre decisões próprias em `glossario-ptbr.md` e `diretrizes-de-traducao.md`.
4. Execute `status`, `resume` e `diff`. Localize a próxima entrada pendente; cada lote completo guarda 500 registros, mas você pode trabalhar em grupos menores.
5. Traduza apenas PTBR, consultando EN, FR e contexto. Compare falas próximas pelo `row`, os grupos de `owner` e a `description`; não renomeie IDs, objetos, cenas ou lógica.
6. Antes de flexionar gênero, distinga quem fala, quem ouve e quem está sendo descrito. `unknown` pede pesquisa contextual, não concordância masculina automática. Use as evidências citadas por ID e não apenas o nome do personagem.
7. Aplique um payload com a geração atual, confira o resultado e execute `check`. Rejeições parciais retornam código 2 e motivos por ID. Retome apenas o que ficou pendente; `--replace` é reservado à revisão intencional de valores já aceitos.
8. Faça commits normais de progresso sem tocar PTBR. A publicação não é acionada por esses commits.
9. Após uma atualização de fontes, leia os diffs completos: entradas alteradas têm o inglês/francês/contexto anterior e a tradução histórica. Resolva as pendências e revise os nomes/vozes afetados.
10. Quando todo o escopo estiver traduzido e revisado, execute `check`, **`build` explicitamente** e `verify-output`. O build cria o recurso nativo completo e seu recibo; não instala no jogo.
11. Faça teste em jogo somente em ambiente autorizado. Registre versão, acentuação, menus e cenas efetivamente verificadas; não generalize para plataformas não testadas.
12. Ao preparar um commit de publicação, inclua PTBR e `translation-work/build-manifest.json` coerentes. O workflow empacota e publica automaticamente se todos os gates, inclusive a autorização de redistribuição dos recursos, estiverem satisfeitos. Não há upload manual adicional.

Para uma interrupção, primeiro `status`; se houver diário pendente, `recover`. Nunca apague backups ou lock para contornar um erro sem verificar se a operação ainda está viva. `gc --dry-run` mostra apenas snapshots concluídos que excedem a política; não é um comando para apagar histórico de tradução.
