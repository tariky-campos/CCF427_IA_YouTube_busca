# CCF427 - Analise de opinioes sobre IA na programacao no YouTube

Projeto de coleta da Parte 1 de **Tecnicas para Analise de Midias Sociais**.
O script coleta **dados reais** somente depois de configurada uma chave pessoal
da **YouTube Data API v3**. Nao ha comentarios ficticios neste projeto.


## 1. O que acontece ao executar?

O programa procura ate **4 videos para cada uma de 3 consultas** (maximo de 12),
publicados a partir de 2024, com duracao de pelo menos 4 minutos e ao menos
50 comentarios segundo os metadados da API. Limita a dois videos por canal
e coleta **ate 100 comentarios principais por video** (maximo teorico de 1.200).
Numeros efetivos dependem dos resultados e disponibilidade no momento da busca.

Consultas: (1) se IA substituira programadores, (2) uso de IA para produtividade,
(3) uso de IA para aprender programacao. Sao **temas de busca**, nao uma
classificacao automatica dos sentimentos.

Depois da coleta, a pasta `dados/` tera:

| Arquivo | Conteudo |
|---|---|
| `comentarios.csv` | Uma linha para cada comentario real, com ID, texto, data, curtidas e video de origem |
| `videos.csv` | Identificadores/URLs, titulo, canal, publicacao, duracao e volume coletado |
| `resumo_coleta.json` | Total real de videos/comentarios, parametros e avisos |
| `relatorio_parte1.md` | Documentacao da Parte 1 **preenchida automaticamente com resultados reais** |

O CSV usa UTF-8 com BOM para facilitar a abertura no Excel. Novas linhas em
comentarios sao citadas corretamente pelo formato CSV. Nomes e IDs de autores
dos comentarios nao sao armazenados. IDs de **comentarios e videos** sao
mantidos para rastreabilidade. Um apostrofo e acrescentado aos textos que
comecam com caracteres perigosos para planilhas (=, +, - ou @).

## 2. Se a coleta falhar

- **Falta YOUTUBE_API_KEY**: volte ao passo 1.
- **API key not valid / accessNotConfigured**: confira a chave e se ativou a API.
- **quotaExceeded**: a cota da API foi atingida; consulte o Console Google.
- **Nenhum video elegivel**: tente reduzir filtros, por exemplo:

```bash
python3 coletar_youtube.py --comentarios-minimos 10 --duracao-minima 120
```

- **Video com comentarios desativados**: pode ser ignorado e fica registrado
  no resumo da coleta; nenhum comentario inexistente sera preenchido.

O comando `python3 coletar_youtube.py --help` mostra todos os parametros.
Para um teste pequeno que consuma menos quota:

```bash
python3 coletar_youtube.py --videos-por-tema 1 --comentarios-por-video 10 --output dados_teste
```

## 3. Validacao dos dados

Confira o numero real mostrado no terminal e no `resumo_coleta.json`. Abra
`videos.csv` e teste alguns URLs. Verifique que `comentarios.csv` possui os
mesmos IDs e contagens do relatorio. **Nao informe 1.200 comentarios se a
coleta retornar menos**.

Para conferir que o projeto funciona sem usar credito da API:

```bash
python3 -m unittest discover -s tests -v
```


## 4. Metodo e cuidados cientificos

- A unidade de analise e o **comentario principal**, nao o usuario nem a resposta.
- Busca de videos por relevancia; amostra dos **100 comentarios mais recentes**
  de cada video (quando disponiveis). Isso gera vies de selecao e temporal.
- As consultas e os filtros foram escolhidos para diversificar perspectivas,
  mas nao garantem representatividade.
- Os comentarios sao opinioes publicas, nao dados de uma pesquisa amostral;
  um mesmo individuo pode comentar mais de uma vez.
- Nao publique a chave da API, dados pessoais ou identificadores de autores.
- Respeite os termos e as politicas aplicaveis a dados da API do YouTube,
  inclusive atualizacao/remocao quando exigidas:
  https://developers.google.com/youtube/terms/developer-policies

Documentacao oficial:

- https://developers.google.com/youtube/data/getting-started
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/v3/docs/videos/list
- https://developers.google.com/youtube/v3/docs/commentThreads/list
- https://developers.google.com/youtube/v3/determine_quota_cost

