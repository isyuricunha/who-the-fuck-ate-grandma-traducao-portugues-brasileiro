# Formato e reconstrução

## Perfil aceito

Unity SerializedFile **v22**, little endian, player Windows (plataforma 19), engine **6000.2.9f1**, com type trees removidas. O adaptador não tenta interpretar qualquer jogo Unity: exige este perfil e rejeita layouts desconhecidos. `engine-shapes.json` guarda os envelopes verificados do SpeechManager e os IDs dos dois objetos de seletor de idioma.

O cabeçalho de 48 bytes contém tamanho estendido, tamanho dos metadados e início dos dados. A tabela de objetos fornece PathID, offset relativo, tamanho e tipo. O parser valida limites, sobreposição e unicidade. A reconstrução atualiza somente offsets/tamanhos necessários e o tamanho do arquivo, preserva o resíduo de alinhamento de cada objeto e reabre o resultado. Todos os payloads de objetos não alterados precisam continuar byte-idênticos.

## Tabela nativa

O objeto `SpeechManager` tem 3.686 linhas nesta fonte. O envelope até o contador de linhas é verificado pelo perfil. Cada linha contém flag de jogador alinhada, `lineID`, strings UTF-8 com comprimento de bytes e alinhamento de quatro bytes (`scene`, `owner`, texto original, descrição), tipo de texto, um array de uma tradução francesa e 52 bytes de campos auxiliares. Somente as duas formas auxiliares observadas são aceitas; referências/arrays não previstos bloqueiam importação, em vez de adivinhar tamanho.

O sufixo registra os idiomas inglês/francês e campos auxiliares. O PT-BR substitui **o inglês no seletor**, preservando o francês. Isso usa o recurso nativo `Language.isDisabled`: a língua original inglesa (índice interno 0) é desativada; PT-BR é inserido como primeira tradução (índice 1), e o francês passa ao índice 2 com todas as suas strings originais. Os idiomas ativos ficam **Português (Brasil), Français**, nessa ordem. O original inglês permanece somente como dado de referência/fallback interno, não como opção ativa. Assim não é preciso renomear objetos ou modificar lógica para exibir o PT-BR.

O build expande cada array de traduções de uma para duas strings, inserindo PTBR antes do francês e conservando o texto francês. O registro de idiomas preserva seus campos e só altera a flag inglesa e acrescenta o descritor português. Os dois arrays de opções de MenuCycle são verificados antes da troca de rótulos. Não há busca global por frases nem alteração de `GameAssembly.dll`. O uso de língua original desativada é [comportamento documentado pelo desenvolvedor do Adventure Creator](https://adventurecreator.org/forum/discussion/16040/parser-failure-at-line-2-expected-closing); os [campos de Language](https://adventurecreator.org/scripting-guide/class_a_c_1_1_language.html) definem o layout interpretado.

O no-op de leitura/reconstrução de **todas as traduções originais**, com o idioma inalterado, precisa produzir exatamente os bytes de entrada. O build também reabre a tabela traduzida, verifica contagem, valores e todos os campos imutáveis. Arquivos `.resS`, texturas, áudio, objetos de lógica e referências externas permanecem originais; a instalação já os contém. Isso não prova que todo texto do jogo está na tabela, nem que um atlas estático renderiza todos os acentos.

## Falas sem registro de idioma

A auditoria estrutural das 16 cenas identificou 84 mensagens não vazias em `ActionSpeech` com `lineID=-1`, além de uma mensagem vazia. Há duas serializações observadas do envelope de Action; ambas são reconhecidas somente quando todo o layout derivado é válido, incluindo parâmetros, mensagem, ID, array de IDs, flags de animação, referências, nomes de clipes, camadas e espera. Mensagens dinâmicas sem mapeamento e layouts desconhecidos falham visivelmente. A API [ActionSpeech](https://adventurecreator.org/scripting-guide/class_a_c_1_1_action_speech.html) confirma a função dos campos.

Essas 84 unidades usam identidade real `arquivo#PathID:<id>:ActionSpeech.messageText`. O build acrescenta SpeechLines com IDs de localização novos, sem colisão, e liga cada ação à sua linha. Isso é registro de localização, não identidade inventada para a fonte: o JSONL conserva PathID/campo e o ID original -1. O texto original da ação não é alterado. Os novos registros guardam PTBR e, para o francês, o inglês que já era o fallback original dessas falas. Não se fabrica uma tradução francesa.

PathIDs podem mudar numa reserialização das cenas. Nessa situação, a sincronização usa remoção/adição e histórico; não reutiliza tradução por frase parecida. Mudanças de EN, referência de falante, tipo de campo ou contexto invalidam somente as unidades afetadas. O perfil gerencia todas as cenas para detectar novas falas, mas publica apenas as cenas que precisam de vínculos novos. Cenas não alteradas não entram no ZIP.

A identidade do falante adicional é cruzada com ações registradas da mesma cena que tenham exatamente as mesmas referências nativas de personagem/jogador, constant ID e parâmetros. Só uma correspondência única e não dinâmica é aproveitada, com o ID de uma fala testemunha exposto no contexto. O nome não vira evidência de gênero: apenas evidências explícitas do catálogo podem ser herdadas. Referências ambíguas ou variáveis permanecem desconhecidas.

## Identidade e contrato JSONL

Para a tabela central, ID: `Who the fuck ate grandma_Data/resources.assets#SpeechLine:<lineID>`. A identidade vem do inteiro nativo, não da frase, da ordem ou do número de linha JSONL. Para mensagens sem ID, aplica-se a identidade de PathID/campo descrita acima. Valores ingleses iguais com IDs diferentes continuam registros diferentes. `row` é o localizador atual; reordenação sem mudança de significado preserva a tradução e a atribuição ao lote.

Campos imutáveis: `id`, `key`, `row`, `source_file`, `EN`, `FR`, `context`. Único campo editável: `PTBR`. String vazia significa pendente; se um nome deve permanecer em inglês, o tradutor escreve essa decisão explicitamente em PTBR. Não existem preenchimentos automáticos.

Contexto distingue fala, proprietário, evidência de gênero, destinatário e referente. Somente evidência explícita documentada é propagada. A fonte inglesa/francesa e o contexto compõem a comparação de sync, de forma que uma mudança de evidência pode exigir revisão mesmo que a frase inglesa seja igual. A fonte anterior permanece no catálogo versionado e nos registros de histórico.

UTF-8 aceita acentos e frases maiores sem limitar pela quantidade de bytes do inglês. O limite de segurança de uma string é 4 MiB, não uma alegação de limite visual do jogo. Tokens, multiplicidade de parâmetros e tags devem permanecer estruturalmente válidos; não há prova automática de correção gramatical. As decisões linguísticas pertencem ao tradutor.

## Limites de atualização

O perfil é deliberadamente estrito. Uma nova compilação do Unity, outro layout de SpeechManager, mais idiomas, referências auxiliares diferentes ou objetos de menu renumerados exigem revisão e novas fixtures pelo desenvolvedor. Não regenere envelopes a partir de um arquivo desconhecido só para fazê-lo passar. Não há suporte a variantes de mods ou community patches neste projeto.
