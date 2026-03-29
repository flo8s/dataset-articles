{{ config(materialized='table') }}

select
    slug,
    title,
    description,
    date::DATE as date,
    datasources::VARCHAR[] as datasources,
    tags::VARCHAR[] as tags
from sqlite_scan('.fdl/d1.db', 'articles')
