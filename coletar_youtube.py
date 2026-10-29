#!/usr/bin/env python3
"""Coletor academico de comentarios publicos pela YouTube Data API v3.

Dependencias: somente biblioteca padrao Python 3.10+.
Configure a variavel YOUTUBE_API_KEY antes de executar.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://www.googleapis.com/youtube/v3"
QUERIES = {
    "substituicao": "inteligencia artificial vai substituir programadores",
    "produtividade": "inteligencia artificial ajuda programadores produtividade",
    "aprendizado": "usar chatgpt inteligencia artificial aprender programacao",
}
VIDEO_FIELDS = ["video_id", "grupo_busca", "consulta", "titulo", "canal", "data_publicacao",
                "duracao_segundos", "visualizacoes_informadas", "comentarios_informados",
                "url_video", "comentarios_coletados"]
COMMENT_FIELDS = ["video_id", "grupo_busca", "comentario_id", "data_comentario",
                  "data_atualizacao", "curtidas_comentario", "texto_comentario",
                  "url_video", "coletado_em_utc"]


class APIError(RuntimeError):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(f"YouTube API HTTP {status}: {reason} - {message}")
        self.status = status
        self.reason = reason


def api_get(endpoint: str, key: str, **params: object) -> dict[str, Any]:
    """Executa GET e evita expor URLs/chaves secretas em erros."""
    query = urlencode({**params, "key": key})
    req = Request(f"{BASE_URL}/{endpoint}?{query}", headers={"User-Agent": "CCF427-Pesquisa/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8")).get("error", {})
            reason = (details.get("errors") or [{}])[0].get("reason", "erro")
            message = details.get("message", "Falha na chamada")
        except (ValueError, UnicodeError, KeyError, TypeError):
            reason, message = "erro", "Falha na chamada"
        raise APIError(exc.code, str(reason), str(message)) from None
    except URLError:
        raise RuntimeError("Falha de rede ao acessar a API do YouTube.") from None


def duration_seconds(iso: str) -> int:
    """Converte duracao ISO 8601 (ex.: PT12M35S) em segundos."""
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", iso)
    if not match:
        return 0
    d, h, m, s = (int(value or 0) for value in match.groups())
    return d * 86400 + h * 3600 + m * 60 + s


def safe_csv_text(value: str) -> str:
    """Evita interpretacao de formulas maliciosas por Excel/planilhas."""
    value = value.replace("\x00", "").strip()
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def video_details(key: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for offset in range(0, len(ids), 50):
        response = api_get("videos", key, part="snippet,statistics,contentDetails",
                           id=",".join(ids[offset:offset + 50]))
        for item in response.get("items", []):
            result[item["id"]] = item
    return result


def select_videos(key: str, per_topic: int, published_after: str,
                  minimum_duration: int, minimum_comments: int,
                  max_per_channel: int) -> list[dict[str, Any]]:
    """Amostragem por tres consultas, limitando videos repetidos e canais."""
    candidates: dict[str, list[str]] = {}
    all_ids: list[str] = []
    for group, query in QUERIES.items():
        response = api_get("search", key, part="snippet", q=query, type="video",
                           maxResults=50, order="relevance", regionCode="BR",
                           relevanceLanguage="pt", publishedAfter=published_after)
        ids = [x.get("id", {}).get("videoId", "") for x in response.get("items", [])]
        candidates[group] = [x for x in ids if x]
        all_ids.extend(candidates[group])
    details = video_details(key, list(dict.fromkeys(all_ids)))
    selected: list[dict[str, Any]] = []
    chosen_ids: set[str] = set()
    channels: dict[str, int] = {}
    for group, ids in candidates.items():
        added = 0
        for video_id in ids:
            item = details.get(video_id)
            if not item or video_id in chosen_ids:
                continue
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            length = duration_seconds(item.get("contentDetails", {}).get("duration", ""))
            number = int(stats.get("commentCount", 0))
            channel_id = snippet.get("channelId", "")
            if (length < minimum_duration or number < minimum_comments
                    or channels.get(channel_id, 0) >= max_per_channel):
                continue
            selected.append({
                "video_id": video_id, "grupo_busca": group, "consulta": QUERIES[group],
                "titulo": snippet.get("title", ""), "canal": snippet.get("channelTitle", ""),
                "data_publicacao": snippet.get("publishedAt", ""),
                "duracao_segundos": length,
                "visualizacoes_informadas": stats.get("viewCount", ""),
                "comentarios_informados": number,
                "url_video": f"https://www.youtube.com/watch?v={video_id}",
                "comentarios_coletados": 0,
            })
            chosen_ids.add(video_id)
            channels[channel_id] = channels.get(channel_id, 0) + 1
            added += 1
            if added >= per_topic:
                break
        print(f"Busca '{group}': {added}/{per_topic} videos elegiveis.")
    return selected


def fetch_comments(key: str, video: dict[str, Any], limit: int,
                   collected_at: str) -> list[dict[str, Any]]:
    """Coleta comentarios principais mais recentes, paginando ate o limite."""
    result_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    token: str | None = None
    while len(result_rows) < limit:
        params: dict[str, Any] = {
            "part": "snippet", "videoId": video["video_id"],
            "maxResults": min(100, limit - len(result_rows)),
            "order": "time", "textFormat": "plainText",
        }
        if token:
            params["pageToken"] = token
        response = api_get("commentThreads", key, **params)
        for thread in response.get("items", []):
            item = thread.get("snippet", {}).get("topLevelComment", {})
            comment_id = item.get("id", "")
            if not comment_id or comment_id in seen:
                continue
            seen.add(comment_id)
            data = item.get("snippet", {})
            result_rows.append({
                "video_id": video["video_id"], "grupo_busca": video["grupo_busca"],
                "comentario_id": comment_id,
                "data_comentario": data.get("publishedAt", ""),
                "data_atualizacao": data.get("updatedAt", ""),
                "curtidas_comentario": data.get("likeCount", 0),
                "texto_comentario": safe_csv_text(data.get("textDisplay", "")),
                "url_video": video["url_video"], "coletado_em_utc": collected_at,
            })
            if len(result_rows) >= limit:
                break
        token = response.get("nextPageToken")
        if not token or not response.get("items"):
            break
    return result_rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(directory: Path, videos: list[dict[str, Any]],
                 comments: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Gera documento com contagens REAIS depois que a coleta terminar."""
    group_rows = "\n".join(
        f"| {group} | {sum(v['grupo_busca'] == group for v in videos)} | "
        f"{sum(c['grupo_busca'] == group for c in comments)} |"
        for group in QUERIES
    )
    video_rows = "\n".join(
        f"| {v['grupo_busca']} | [{v['video_id']}]({v['url_video']}) | "
        f"{v['comentarios_coletados']} |" for v in videos
    )
    messages = "\n".join(f"- {x}" for x in summary["avisos"]) or "Nenhum aviso registrado."
    c = summary["criterios"]
    body = f"""# CCF427 - Parte 1 - Coleta de Dados

**Titulo:** Opinioes sobre inteligencia artificial na programacao em comentarios do YouTube  
**Autor:** Tariky Rodrigues Campos  
**Data da coleta (UTC):** {summary['coleta_utc']}  
**Repositorio do codigo:** https://github.com/tariky-campos/CCF427_IA_YouTube_busca.git

## 1. Objetivo e questao de pesquisa

Investigar opinioes sobre o uso de IA no desenvolvimento de software em comentarios
publicos de videos em portugues. A pergunta de pesquisa e: **quais opinioes e
sentimentos aparecem nos comentarios e como variam entre as perspectivas de
substituicao profissional, produtividade e aprendizado?**

## 2. Fonte, coleta e metodologia

Fonte: YouTube Data API v3. O programa Python `coletar_youtube.py` consulta
`search.list` para localizar videos, `videos.list` para obter metadados e
`commentThreads.list` para recuperar comentarios principais (sem respostas).

As consultas sao: {', '.join(QUERIES.values())}. Os videos foram buscados
por relevancia, com publicacao a partir de {c['published_after']},
duracao minima de {c['min_duration_seconds']} segundos, no minimo
{c['min_comment_count']} comentarios informados e no maximo
{c['max_per_channel']} videos de cada canal. Para cada video, o coletor
recuperou ate {c['comments_per_video']} comentarios principais em ordem
decrescente de publicacao.

## 3. Descricao e volume dos dados

- Videos efetivamente selecionados: **{len(videos)}**.
- Comentarios efetivamente coletados: **{len(comments)}**.
- Meta planejada: ate {c['videos_per_topic'] * len(QUERIES)} videos e
  {c['videos_per_topic'] * len(QUERIES) * c['comments_per_video']} comentarios.

| Perspectiva de busca | Videos | Comentarios |
|---|---:|---:|
{group_rows}

Entidade `video` (uma linha em `videos.csv`): identificador, grupo, consulta,
titulo, canal, data de publicacao, duracao, visualizacoes informadas,
comentarios informados, URL e quantidade coletada. Entidade `comentario`
(uma linha em `comentarios.csv`): identificador, video, grupo, texto, data,
atualizacao, curtidas, URL e instante da coleta. A identidade dos autores
dos comentarios nao e coletada.

| Grupo | Video | Comentarios coletados |
|---|---|---:|
{video_rows}

## 4. Limitacoes dos dados

1. A amostra e de conveniencia, definida por tres buscas e resultados
   ordenados por relevancia; nao e representativa de todos os usuarios do YouTube.
2. Os comentarios foram ordenados por data (mais recentes), o que reduz a
   representacao de opinioes publicadas anteriormente.
3. Respostas a comentarios nao foram coletadas; apenas comentarios principais.
4. Restricao a buscas em portugues e aos criterios de ano, duracao,
   comentarios e limite de videos por canal.
5. Comentarios apagados, privados, desativados ou inacessiveis ficam ausentes.
6. Contadores do YouTube podem mudar depois da data da coleta.
7. Ainda nao houve classificacao de sentimento: essa analise sera posterior
   e deve considerar ironia, sarcasmo e opinioes ambiguas.
8. Por seguranca de planilha, comentarios iniciados com =, +, - ou @
   recebem apostrofo inicial no CSV.

## 5. Proximas etapas

Na Parte 2, pretende-se mostrar distribuicoes de comentarios e curtidas,
termos recorrentes, comparacoes entre grupos e possiveis sentimentos.
O artigo final avaliara diferencas observadas entre os tres grupos.

## 6. Avisos da execucao

{messages}

## Referencias

- YouTube API search.list: https://developers.google.com/youtube/v3/docs/search/list
- YouTube API videos.list: https://developers.google.com/youtube/v3/docs/videos/list
- YouTube API commentThreads.list: https://developers.google.com/youtube/v3/docs/commentThreads/list
- CCF427 - Projeto Pratico da Disciplina.
"""
    (directory / "relatorio_parte1.md").write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Coletor YouTube para a disciplina CCF427")
    parser.add_argument("--output", type=Path, default=Path("dados"))
    parser.add_argument("--videos-por-tema", type=int, default=4)
    parser.add_argument("--comentarios-por-video", type=int, default=100)
    parser.add_argument("--publicados-desde", default="2024-01-01T00:00:00Z")
    parser.add_argument("--duracao-minima", type=int, default=240)
    parser.add_argument("--comentarios-minimos", type=int, default=50)
    parser.add_argument("--max-videos-por-canal", type=int, default=2)
    args = parser.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("Falta YOUTUBE_API_KEY. Leia README.md para configurar sua chave.", file=sys.stderr)
        return 2
    if min(args.videos_por_tema, args.comentarios_por_video, args.max_videos_por_canal) <= 0:
        parser.error("Os limites por tema, video e canal devem ser positivos")
    if min(args.comentarios_minimos, args.duracao_minima) < 0:
        parser.error("Os filtros minimos nao podem ser negativos")

    try:
        videos = select_videos(key, args.videos_por_tema, args.publicados_desde,
                               args.duracao_minima, args.comentarios_minimos,
                               args.max_videos_por_canal)
        if not videos:
            print("Nenhum video elegivel. Revise os filtros.", file=sys.stderr)
            return 1
        collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        comments: list[dict[str, Any]] = []
        warnings: list[str] = []
        for video in videos:
            try:
                rows = fetch_comments(key, video, args.comentarios_por_video, collected_at)
            except APIError as exc:
                if exc.reason in {"commentsDisabled", "videoNotFound"}:
                    warnings.append(f"Video {video['video_id']}: comentarios indisponiveis ({exc.reason}).")
                    continue
                raise
            video["comentarios_coletados"] = len(rows)
            comments.extend(rows)
            print(f"Video {video['video_id']}: {len(rows)} comentarios")
        if not comments:
            print("Nenhum comentario recuperado; nao foram gerados arquivos vazios.", file=sys.stderr)
            return 1
    except (APIError, RuntimeError) as exc:
        print(f"Coleta interrompida: {exc}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "videos.csv", VIDEO_FIELDS, videos)
    write_csv(args.output / "comentarios.csv", COMMENT_FIELDS, comments)
    summary = {
        "coleta_utc": collected_at, "total_videos": len(videos),
        "total_comentarios": len(comments), "avisos": warnings,
        "criterios": {
            "published_after": args.publicados_desde,
            "videos_per_topic": args.videos_por_tema,
            "comments_per_video": args.comentarios_por_video,
            "min_duration_seconds": args.duracao_minima,
            "min_comment_count": args.comentarios_minimos,
            "max_per_channel": args.max_videos_por_canal,
        },
        "consultas": QUERIES,
        "unidade": "comentario principal; respostas excluidas",
        "metodo_busca": "relevancia da API e filtros de elegibilidade",
        "metodo_comentarios": "mais recentes primeiro",
    }
    (args.output / "resumo_coleta.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(args.output, videos, comments, summary)
    print(f"Concluido: {len(comments)} comentarios em {len(videos)} videos. Arquivos: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
