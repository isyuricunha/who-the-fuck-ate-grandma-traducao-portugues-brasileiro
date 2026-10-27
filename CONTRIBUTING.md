# Contribuições e permissão voluntária

Relatos de erro, sugestões e revisões são bem-vindos. Não envie arquivos proprietários do jogo nem traduções de terceiros sem autorização.

Uma contribuição de texto original só será incorporada após aceite afirmativo registrado. Você mantém a autoria e concede, sobre os direitos que efetivamente controla, uma licença **não exclusiva, mundial e gratuita** que permite ao mantenedor usar, editar e distribuir a contribuição sob a CC BY-NC-SA 4.0 e transmitir/sublicenciar a autorização adicional de integração oficial descrita em [GAME-DEVELOPER-PERMISSION.md](./GAME-DEVELOPER-PERMISSION.md). Isso inclui distribuição comercial do jogo oficial, com crédito e sem novo pedido de autorização ou pagamento. Não se exige transferência de propriedade nem renúncia a direitos morais inalienáveis.

## Como registrar o aceite

1. Leia [LICENSE](./LICENSE) e [GAME-DEVELOPER-PERMISSION.md](./GAME-DEVELOPER-PERMISSION.md).
2. Abra um pull request com o conteúdo de sua autoria, identificando os commits e o crédito desejado.
3. Marque voluntariamente a declaração do modelo de PR. A caixa começa desmarcada. Abrir um PR, oferecer ajuda ou enviar um texto não equivale a consentir.
4. A verificação **Permissão de contribuição** confere o aceite e os autores dos commits. Cada coautor precisa de autorização própria. A declaração do proponente não autoriza o trabalho de outra pessoa.
5. Antes do merge, o mantenedor registra em `.github/contributor-consents.json` o identificador do autor, os hashes dos commits abrangidos, `affirmative: true` e `evidence_url` com o link permanente do aceite. O PR e os commits preservam a evidência e o crédito. Configure essa verificação como obrigatória na proteção da branch, quando o repositório for publicado; essa configuração remota não é feita pelo toolkit.

Exemplo de registro, somente após um aceite real: campos `login`, `commits`, `affirmative` e `evidence_url`. Não preencha registros fictícios. Para material recebido fora do GitHub, registre uma autorização expressa de escopo equivalente, com identidade, conteúdo/commit abrangido, data e referência durável consultável pelo mantenedor.

Se não puder autorizar a integração oficial comercial, informe antes de enviar texto autoral. Ele não será tratado como coberto pela autorização adicional. Contribuições antigas sem consentimento também precisam de revisão; nenhuma licença retroativa é presumida.

O código do toolkit e contribuições de software exigem avaliação de licença própria; a CC não é recomendada para software. Não substitua licenças legítimas de dependências ou de trabalhos alheios. Nesta preparação não foi escolhida uma licença adicional de software.

O projeto não presume autoria protegida sobre todo relato de bug ou sugestão pontual; em caso de texto substancial, o mantenedor avalia o escopo e pede o aceite antes de incorporar.
