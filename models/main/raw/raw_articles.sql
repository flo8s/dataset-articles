{{ config(materialized='table') }}

select
    slug,
    title,
    description,
    date::DATE as date,
    datasources::VARCHAR[] as datasources,
    tags::VARCHAR[] as tags
from sqlite_scan('{{ fdl_common.dist_dir() }}/d1.db', 'articles')
