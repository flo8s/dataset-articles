## 概要

Queria ショーケースに掲載されている記事のメタデータを管理するデータセットです。
Cloudflare D1 から記事情報を取得し、検索用テキストを生成しています。

## テーブル: mart_articles

- slug: 記事の一意識別子
- title: 記事タイトル
- description: 記事の概要
- date: 公開日
- datasources: 使用データソース
- tags: タグ
- search_text: 検索用テキスト（タイトル + 概要 + タグの結合）
