# Briefing de contexto para localização

Pesquisa preparada durante a engenharia em **26/10/2026**, antes do início da tradução. Este documento orienta a leitura do texto original; não fixa equivalentes PT-BR nem substitui as decisões do tradutor. Há spoilers na seção explicitamente marcada.

## Identidade e proposta

**Who The Fuck Ate Grandma ?**, de Benjamin G, é uma aventura point-and-click em pixel art, inspirada nos anos 1990. A Steam identifica lançamento em 23/04/2026 e inglês/francês para interface e legendas. O aniversário de 93 anos da avó dá lugar a um mistério familiar macabro. A exploração da casa, o inventário e as conversas conduzem os enigmas. A ficha oficial apresenta Toby como colecionador de cartas de dinossauros, Bertrand como irmão mais velho de temperamento difícil e Rene ligado às salsichas veganas. [Fonte oficial](https://store.steampowered.com/app/1756100/).

O material local corresponde a um player Windows Unity **6000.2.9f1**, IL2CPP, com Adventure Creator. O `app.info` usa `Grandma Industries` como empresa; esse valor técnico não foi tratado como substituto do crédito público Benjamin G. A versão comercial exata não foi determinada por número de patch: a compatibilidade é amarrada ao SHA-256 da fonte aceita no manifesto. Não se deve inferir que toda versão Steam ou outra plataforma usa o mesmo binário.

## Tom e estrutura narrativa

A tabela original mistura investigação, absurdos familiares, humor negro, palavrões, provocações e comentários metalinguísticos sobre o próprio desenvolvimento. Créditos e narradores também aparecem sob o tipo nativo `Speech`: a categoria não basta para afirmar que alguém está conversando. `My new NPC`, por exemplo, contém créditos; `Phone2` inclui falas ligadas ao desenvolvedor dentro da narrativa. Conserve os créditos existentes, sem tratar nomes e URLs como oportunidades de adaptação livre.

As entradas preservam inglês e francês lado a lado. O francês é referência de contexto, não fonte automaticamente superior ao inglês: há linhas vazias, aspas envolventes e quebras CRLF, além de diferenças de redação. Nos diários, a versão francesa às vezes omite detalhes presentes no inglês. Compare intenção e contexto; não tente corrigir diferenças por substituição mecânica.

Há grupos de cena como `Salon - Début`, `Salon`, `Salon - Fin`, `Vieux jardin`, `Jardin`, `Cuisine`, `Couloir`, `Salle de bain`, `Chambre`, `Abri`, `Grotte`, `Grotte - Fin` e **`Grotte OLD`**. São nomes internos mantidos intactos. Eles ajudam a localizar passagens, mas não provam sozinhos cronologia, presença na versão final ou nome visível do lugar. Cenas antigas e texto retido no SpeechManager podem continuar extraídos sem serem executados.

## Personagens e identidades: o que os dados realmente mostram

| Identificador nativo | Evidência e utilidade | Limites |
| --- | --- | --- |
| `Heros` | Aparece em muitas falas com `isPlayer=true`; é um identificador de proprietário de fala do protagonista. | Não deduzir o nome público nem o gênero só de `Heros`. |
| `Josiane` | A entrada **229** descreve explicitamente Josiane com `She`; a **1346** volta a se referir a ela com `She`. O registro de gênero é associado à personagem descrita e depois ligado ao proprietário `Josiane`. | Isso não torna femininos todos os personagens mencionados nas falas dela. |
| `Bertrand` | Na entrada **95**, o próprio falante se apresenta como irmão do interlocutor. | A identificação do interlocutor depende da conversa, não do gênero de Bertrand. |
| `Gustave` | As entradas **340**, **1247**, **1488**, **2709** e **2753** falam do casamento e da esposa. A **1346**, com descrição `From: Gustave: Look at`, distingue Gustave e Josiane por pronomes. | Não transformar todas as ocorrências de `wife` em nome próprio nem inferir a pessoa referida fora desse contexto. |
| `Henri` | Entradas **161–163** associam o personagem a Pikwik; o proprietário da fala e a entidade mencionada são distintos. | O pronome empregado para Pikwik não é prova isolada do gênero do falante. |
| `Rene` | Conversas sobre salsichas veganas e comentários sobre a família, incluindo **233–234** e **327**. | Preserve o identificador sem acento; uma forma visível adotada em PT-BR é decisão linguística. |
| `Toby`, `Toby Vieux` | Há proprietários distintos. O segundo conduz parte de um relato posterior, como nas entradas **47–50**. | Não unificar os IDs nem presumir que ambas as vozes têm o mesmo registro. |
| `Pepe`, `Papi` | Falas da caverna e referências a parentesco, por exemplo **494–500** e **614–618**. | Não unir as duas identidades automaticamente sem prova da cena em execução. |
| `Jerry the parrot`, `Dog`, `Cage` | Proprietários e descrições indicam interações com animais e objetos. | Um objeto chamado `Cage` pode ter fala associada; proprietário não significa pessoa. |
| `Narrateur`, `Narrator`, `Phone2`, `Grumpy` | Identificadores úteis para agrupar narração, telefone e vozes de apoio. | Correspondências finais, destinatários e identidades permanecem para revisão contextual. |

O catálogo expõe `owner`, `scene`, `description`, `is_player`, tipo e evidências com ID de origem. Só há marcação explícita de gênero onde a ligação foi documentada. Os demais casos ficam `unknown`, sem padrão masculino implícito. Identificadores como `Speaker_*` e nomes de tabelas/cenas são pistas, não prova automática; a fixture de regressão usa `Speaker_Jessica`/`ScriptJessica` justamente para impedir que essas pistas desapareçam sem convertê-las em fatos inventados.

Não foi localizado um seletor de gênero configurável pelo jogador no perfil gerenciado. Isso não autoriza afirmar que toda construção dinâmica do jogo foi auditada. Verifique separadamente falante, destinatário e referente. A frase de uma personagem feminina sobre um homem continua exigindo concordância com o homem descrito. Mudanças na fonte da evidência invalidam o contexto dependente para revisão, sem descartar traduções não relacionadas.

## Vocabulário e desafios recorrentes

- **Will** pode designar documento sucessório neste contexto, não apenas vontade ou verbo auxiliar. Consulte os grupos de objetivo relacionados ao testamento e às informações familiares.
- **Card**, **dinosaur card**, **collection** e referências a raridade fazem parte das interações de Toby. A distinção entre carta/cartão e coleção deve ser decidida de forma consistente no glossário.
- **Vegan sausages**, **dog food**, **cockroach**, **insects**, **barbecue sauce**, **chicken**, **butter** e **yogurt** aparecem como itens ou tópicos de enigmas. Não trate alimentos recorrentes apenas como piadas independentes se a frase aponta uma ação de puzzle.
- **Look**, **Talk**, **Take** e **Use** são ações visíveis de interface; descrições como `From: ...: Use` são contexto técnico e não devem ser traduzidas no JSONL.
- As dicas usam etapas de **Hint**, **Solution**, **Objectives** e variáveis de texto que incluem nomes e assuntos. `Variable` no catálogo significa texto recolhido pelo sistema de localização; o build altera só a string de tradução, sem renomear a variável nem seus vínculos.
- Maiúsculas, hesitações e frases curtas têm função cômica. A tradução precisa avaliar ritmo e voz por conversa, não só equivalência palavra por palavra. A intensidade dos palavrões é decisão do tradutor, documentada nas diretrizes.
- Os diários contêm tabulações e parágrafos, inclusive pistas distribuídas ao longo do texto. O workspace usa escapes JSON; não elimine quebras úteis nem confunda aspas da referência francesa com comandos.

Não foram encontrados placeholders ou tags nas strings inglesas desta extração, mas o validador preserva tokens e estruturas se surgirem em atualização. Ausência atual não significa liberdade para alterar IDs, caminhos, comandos ou referências serializadas. Nomes de desenvolvedores, créditos de música/voz e links devem conservar atribuição verdadeira.

## Spoilers — material para revisão contextual

Os registros da caverna e os diários discutem confinamento prolongado, alimento trazido por um cão mediante um apito e um projeto de restaurante subterrâneo. O diário **2998**, associado a `Livre_D45`, relaciona o apito e as conservas; **3063**, **3116** e **3094** representam outros momentos desse relato. A sequência ajuda a compreender o humor dos alimentos e a diferença entre observação, lembrança e acusação.

O relato de `Toby Vieux` menciona consequências para a família. Essas passagens não devem ser deslocadas para o briefing público nem usadas para revelar o desfecho no README. Também não basta uma acusação dita por um personagem para afirmar como fato quem é culpado: preserve perspectiva, dúvida e eventual contradição narrativa.

## Fontes, escopo e pendências

1. [Steam — ficha oficial, autoria, idiomas e sinopse](https://store.steampowered.com/app/1756100/), consultada em 26/10/2026. Arte do cabeçalho oficial verificada por resposta HTTP válida; não se baixou arte para a instalação.
2. `EN/Who the fuck ate grandma_Data/resources.assets`, objeto `SpeechManager`, IDs citados acima; original aceito e inglês/francês preservados nos lotes. A indicação de caminhos internos aponta evidência do próprio jogo, não instruções externas.
3. `Who the fuck ate grandma_Data/app.info`, `ScriptingAssemblies.json`, `global-metadata.dat` e cabeçalhos de assets da instalação fornecida, lidos para identidade e tecnologia; arquivos que não são necessários ao build não foram copiados.
4. [Adventure Creator — inclusão de traduções](https://adventurecreator.org/tutorials/adding-translations) e [referência SpeechLine](https://adventurecreator.org/scripting-guide/class_a_c_1_1_speech_line.html), usadas para interpretar a tabela e distinguir `owner`, ID, tipo e idioma. [Enumerações de tipos](https://adventurecreator.org/scripting-guide/namespace_a_c.html).

Além da tabela central, o catálogo contém 84 falas sem registro prévio de idioma, encontradas nas cenas por parser de ActionSpeech. Suas referências de falante e identidades por objeto/campo são expostas; francês vazio indica ausência original de tradução francesa, não permissão para inventá-la. O relatório `scene-audit.json` preserva a etapa heurística inicial e seus candidatos; a contagem final vem do parser estrutural.

Permanecem para verificação em jogo: quais entradas antigas ainda aparecem, rótulos em imagens, encaixe das frases, acentos nos atlas de fontes, resolução exata de algumas vozes e comportamento dos menus com **PT-BR substituindo o inglês e francês preservado**. Não foram inventadas facções, expansões, raças, mitologia ou um sistema de classes: não há evidência relevante desses elementos no escopo pesquisado. O tradutor começa com esta pesquisa pronta e a amplia apenas ao encontrar evidência nova.
