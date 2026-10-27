# Correção visual: acentos e menu inicial

Correção solicitada após as capturas em execução mostrarem botões franceses e acentos com outro desenho. A instalação é somente leitura; os arquivos corrigidos são gerados no repositório.

## Fontes

A fonte `lucasarts-scumm-solid`, PathID 427 em `resources.assets`, continha 101 caracteres Unicode. Faltavam, entre outros, á, ã, ç e í. As entradas `SubsLineLabel` e `Journal` referenciam essa fonte diretamente.

A variante amplia a fonte para 125 caracteres. Os novos glifos seguem a grade vetorial de 250 unidades e preservam integralmente o corpo da letra-base, inclusive nas maiúsculas. O í reutiliza o contorno contínuo da haste do i original, retirando apenas o ponto. Todos os contornos, avanços e espaçamentos laterais dos caracteres preexistentes foram comparados após recompilação e permanecem iguais. As métricas verticais da fonte e os três campos correspondentes no objeto Unity foram ampliados para acomodar acentos e cedilha sem reduzir as letras; os demais campos permanecem iguais. A ChunkFive, PathID 428, recebe õ, Õ e o mapeamento de °, passando de 167 para 170 caracteres. Nenhuma das duas fontes tem caractere ausente no conjunto dos 3.770 textos traduzidos.

`fonts/coverage.json` registra os resultados da autoria. `reports/visual-verification.json` verifica as fontes efetivamente embutidas no build, sem dependências externas.

## Menu

As artes do menu são texturas, independentes das traduções da tabela central. Os estados normal e destacado dos botões ingleses passam a JOGAR, CARREGAR e SAIR. As seis texturas francesas originais permanecem byte a byte iguais.

O componente próprio `ACLanguageButtonStyler` selecionava imagens inglesas para idioma 0 e francesas para qualquer outro índice. Como o PT-BR usa índice 1 e o francês foi preservado no 2, era necessário corrigir o seletor visual. Dois trechos do método `UpdateButton` foram ajustados para escolher francês somente quando o idioma é 2; os demais usam o conjunto inglês agora localizado. A DLL tem o mesmo tamanho: 44 bytes mudam dentro de duas regiões de 19 e 26 bytes, respectivamente. O SHA-256 original e as assinaturas completas das duas regiões são obrigatórios. Qualquer versão diferente falha antes da reconstrução.

`visuals/selector-proof.json` registra a identificação do método, a desmontagem dos trechos resultantes e a execução isolada das instruções x64 para os idiomas -1, 0, 1, 2, 3 e 99, nos dois estados. Isso prova a seleção dos ponteiros e a preservação dos registradores relevantes nesse trecho, não a execução do jogo inteiro.

OPÇÕES usa uma segunda instância do mesmo componente já presente no jogo, ligada apenas ao botão Options. Quatro texturas são acrescentadas a `sharedassets0.assets`: normal/destaque PT-BR e cópias intactas normal/destaque francesas. Uma instância é acrescentada a `level0`, e a lista de componentes de seu GameObject passa de sete para oito. Nenhuma classe nova ou DLL gerenciada é introduzida.

## Build e validação

O build textual permanece independente. Depois dele, `visuals.py` aplica somente o perfil `visuals/profile.json`, com fontes e objetos hash-bound. Há quatro alvos visuais: `resources.assets`, `sharedassets0.assets`, `level0` e `GameAssembly.dll`. Os três últimos aumentam o inventário do pacote de 12 para 15 arquivos.

O build normal e a verificação usam Python padrão e não executam o DLL Windows. A camada visual foi validada no host Windows; a confirmação deste build no Ubuntu ARM64 permanece pendente. A autoria opcional dos recursos usa as versões registradas em `visuals/requirements-authoring.txt`. Os originais adicionais ficam em `visuals/original/`, separados do inventário textual imutável de EN.

```sh
python translation-work/toolkit.py doctor --target host
python translation-work/toolkit.py build
python translation-work/toolkit.py verify-output
python translation-work/verify_visuals.py
```

Para regenerar a autoria em ambiente de desenvolvimento, instale as dependências opcionais em ambiente isolado e execute `author_visuals.py`. Na primeira importação, forneça `--game-root`; depois, o comando usa os originais preservados e as artes de dois estados já salvas. O comando não instala nem modifica o jogo. Uma atualização dos originais exige nova análise do perfil, nunca troca cega de hashes.

Os testes incluem anexação de objetos sem modificar os existentes, rejeição de IDs duplicados, assinaturas nativas incorretas, versões de fonte diferentes, caminhos inseguros e inventário antigo do pacote. Também foram reexecutadas as suítes de fontes, Release simulada e documentação, além dos testes pontuais de build e doctor.

As prévias e a inspeção do pacote não equivalem a uma captura do jogo corrigido em execução. Conferir no jogo: menu PT-BR e francês, estados destacados, acentos em legendas e diário e navegação entre cenas. A nova versão não foi instalada automaticamente.

## Resultado da rodada final

- 54 testes executados: 53 aprovados e um ignorado pelo ambiente. O benchmark prolongado de 500 transações, executado anteriormente, foi excluído desta rodada.
- Verificação independente dos objetos do build: 3.770 textos, 15 arquivos, nenhuma ausência de glifo nas duas fontes; imagens francesas preservadas e ligação do botão Options conferida.
- Os oito estados de botão foram extraídos dos arquivos Unity finais e comparados pixel a pixel com as artes importadas. O relatório está em `reports/visual-image-verification.json`. Essa verificação detecta inclusive uma serialização que tenha mantido a imagem antiga por engano.
- O ZIP contém exatamente os 15 arquivos do recibo, com CRC e SHA-256 de cada arquivo conferidos após descompressão. Tamanho e hash do ZIP ficam em `reports/visual-package.json`.

## Revisão v2: tamanho dos acentos

O usuário confirmou o menu em execução e relatou letras acentuadas pequenas. A revisão preserva os contornos completos e ajusta ascendente, descendente e entrelinha. Quatro testes de geometria verificam os contornos originais, a haste contínua de í, os limites verticais e a igualdade pixel a pixel do corpo de cada letra nova com sua base em cinco tamanhos. A ChunkFive permanece idêntica à primeira revisão.

O pacote `PTBR-menu-e-fontes-v2.zip` muda somente `resources.assets` em relação ao primeiro ZIP; menu, seletor e textos permanecem iguais. CRC, inventário e hashes foram conferidos após descompressão, conforme `reports/visual-package-v2.json`. O teste posterior do usuário confirmou que a v2 ainda apresentava acentos pequenos. A instalação não foi modificada pela ferramenta.

## Revisão v3: atlas efetivamente usado pelas legendas

A inspeção dos componentes `TextMeshProUGUI` mostrou que o campo de fonte legado dos `MenuLabel` não era o recurso usado pela malha das legendas. A fonte visível é o `TMP_FontAsset` PathID 458 de `sharedassets0.assets`, com 86 entradas básicas, atlas Alpha8 PathID 201 e material PathID 2. A reserva FRENCH (457) cobre alguns acentos franceses; í, ã e ó caíam em LiberationSans SDF.

A prova foi feita com o motor Unity 6000.2.9f1 do próprio jogo, em uma cópia privada com `-batchmode -nographics`. `ForceMeshUpdate` no componente TMP, com “familia família irmao irmão vovo vovó difícil À Á É Ç Õ”, registrou LiberationSans SDF e escala 0,41860464 para os caracteres portugueses na v2. No build corrigido, todos usam lucasarts-scumm-solid e escala 0,52941179. Os relatórios estão em `reports/subtitle-mesh-before.json` e `reports/subtitle-mesh-after.json`. Esse é um teste do motor e da malha textual; não é uma captura de tela nem uma campanha completa.

O atlas principal agora contém 112 glifos e 113 mapeamentos, cobrindo todos os caracteres dos 3.770 textos. O rasterizador nativo `TMP_FontAsset.TryAddCharacters` gerou os SDFs em 68 pontos, padding 27, modo 4134 (SDFAA). O atlas foi ampliado de 1024×1024 para 2048×1024: a metade esquerda mantém exatamente os pixels originais, e a direita recebe os glifos adicionais. Todos os registros originais de glifo, coordenadas e avanços foram preservados. O material só muda `_TextureWidth`. A face recebe espaço vertical para os acentos completos. O recurso final continua estático e não requer scripts, Frida ou geração em tempo de execução.

Os quatro testes em `tests/test_tmp_atlas.py` verificam cobertura real do TMP, preservação de registros/pixels, igualdade do corpo dos acentos nos SDFs e rejeição de um bake incompleto ou que altere caracteres originais. A cobertura da fonte OTF isolada deixou de ser aceita como prova suficiente das legendas.

Os originais franceses 193, 200 e 457 permanecem byte a byte iguais. Menu, seletor de idioma, traduções e demais arquivos permanecem iguais à v2. Apenas `sharedassets0.assets` muda no novo ZIP. A instalação original permanece somente leitura.

### Reproduzir a autoria nativa (opcional, Windows)

Instale as dependências de `visuals/requirements-engine-bake.txt` em um ambiente isolado e execute:

```sh
python translation-work/author_tmp_atlas.py --game-root "D:/Games/Who The Fuck Ate Grandma"
```

O comando verifica o build e trabalha exclusivamente numa cópia em `.state/tmp-bake/game`, restaurando nela os três objetos TMP originais antes da autoria. Produz `bake.json` e `atlas-alpha8.bin` em `.state` para revisão e comparação com `visuals/tmp/`. O processo criado para a autoria é encerrado ao final. Nenhuma instrumentação integra o pacote do jogo. O build normal e a verificação estrutural continuam usando somente a biblioteca padrão do Python.

Validação final da v3: 62 testes executados, 61 aprovados e um ignorado pelo ambiente; apenas o benchmark prolongado de armazenamento foi excluído. O bake nativo foi repetido pelo comando documentado, produzindo registros e pixels idênticos ao snapshot revisado. O ZIP de 15 arquivos foi descomprimido e conferido por CRC e SHA-256; o recibo está em `reports/visual-package-v3.json`.

## Confirmação do mantenedor — 27/10/2026

Após instalar o pacote v3, o mantenedor confirmou: “Agora deu certo.” O menu já havia sido confirmado e os acentos das legendas passaram a ter o desenho e o tamanho corretos. O registro vincula essa confirmação ao SHA-256 do ZIP em `reports/subtitle-atlas-validation.json`. Os 15 arquivos desse pacote integram `PTBR/`, de onde o workflow de release gera `PTBR.zip`. A confirmação é visual e pontual; não amplia a validação para campanha completa, saves ou todas as telas.
