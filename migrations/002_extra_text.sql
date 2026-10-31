-- One table for content the existing tables have no column for:
--   Chinese text (lang = 'zh'), English-only extras like project type (lang = 'en'),
--   and language-neutral values like the skill icon (lang = '').
CREATE TABLE IF NOT EXISTS extra_text (
    id        SERIAL PRIMARY KEY,
    entity    VARCHAR(50) NOT NULL,   -- 'project', 'experience' or 'skill_group'
    entity_id INTEGER     NOT NULL,   -- id of the row it belongs to
    field     VARCHAR(50) NOT NULL,   -- e.g. 'title', 'description', 'icon'
    lang      VARCHAR(5)  NOT NULL DEFAULT '',
    value     TEXT,
    UNIQUE (entity, entity_id, field, lang)
);
