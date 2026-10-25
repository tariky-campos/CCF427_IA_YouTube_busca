# Proposta de projeto para a Parte 1 - CCF427

**Tema:** Opinioes sobre inteligencia artificial na programacao no YouTube.

**Autor:** [NOME COMPLETO]

**Status em 25/10/2026:** plano e codigo elaborados; **dados ainda nao
coletados**. Este arquivo e um roteiro de apresentacao, nao um relatorio de
resultados. Apos executar o coletor, use `dados/relatorio_parte1.md`, com
quantidades e videos reais, para a entrega definitiva.

## Pergunta de pesquisa

Quais sentimentos e opinioes sobre IA na programacao aparecem nos comentarios
publicos do YouTube? Existem diferencas entre videos sobre substituicao de
programadores, produtividade e aprendizado?

## Objetivo da primeira etapa

Programar um coletor em Python com a YouTube Data API v3, organizar os videos
e comentarios coletados em CSV e registrar o volume, o procedimento e as
limitacoes da amostra.

## Estrategia de coleta planejada

- Fonte: videos publicos do YouTube localizados por tres consultas em portugues.
- Selecao: ate quatro videos por consulta, publicados desde 2024, com pelo
  menos quatro minutos e 50 comentarios; no maximo dois videos por canal.
- Coleta: ate 100 comentarios principais mais recentes por video.
- Meta maxima: 12 videos e 1.200 comentarios, **nao resultado observado**.
- Arquivos finais: `videos.csv`, `comentarios.csv`, `resumo_coleta.json`.
- Chamadas: `search.list`, `videos.list`, `commentThreads.list`.

## Limitacoes previstas

A amostra nao sera probabilistica; buscas e ranking criam vies, comentarios
recentes nao representam todos os comentarios, e a amostra sera restrita
a videos elegiveis em portugues. Respostas e comentarios indisponiveis
nao serao coletados. A quantidade final pode ser inferior a meta.

## Etapas seguintes

Caracterizar os dados com graficos de distribuicao, frequencia de palavras e
comparacoes por tema. Posteriormente, classificar sentimentos com validacao
de uma amostra manual e escrever o artigo cientifico.

## O que falar ao professor

"Minha proposta e analisar opinioes sobre inteligencia artificial na
programacao em comentarios do YouTube. Criei um coletor Python que busca
videos sobre substituicao de programadores, produtividade e aprendizado,
e organiza comentarios publicos em tabelas. Apos executar a coleta, vou
apresentar a quantidade de comentarios obtidos e as limitacoes da amostra.
Nas etapas seguintes, vou explorar sentimentos e comparar os tres grupos."

