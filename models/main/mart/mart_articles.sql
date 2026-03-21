{{ config(materialized='view') }}

select
    slug,
    title,
    description,
    date,
    datasources,
    tags,
    concat_ws(' ', title, description, array_to_string(tags, ' ')) as search_text
from {{ ref('raw_articles') }}
