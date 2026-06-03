-- ============================================================
-- PIRO · BDDI — Consultas analiticas (Oracle SQL)
-- 6 consultas (minimo exigido: 5). Usam filtros, agrupamentos,
-- funcoes de agregacao, ordenacao e JOINs.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Ranking de estados com mais focos no ultimo mes
--    (WHERE por data + GROUP BY + COUNT + ORDER BY)
-- ------------------------------------------------------------
SELECT estado,
       COUNT(*)            AS total_focos,
       ROUND(AVG(frp), 1)  AS frp_medio
FROM   focos_incendio
WHERE  data_foco >= ADD_MONTHS(TRUNC(SYSDATE), -1)
GROUP  BY estado
ORDER  BY total_focos DESC;

-- ------------------------------------------------------------
-- 2) Evolucao diaria de focos nos ultimos 30 dias
--    (agregacao temporal por dia)
-- ------------------------------------------------------------
SELECT TRUNC(data_foco)   AS dia,
       COUNT(*)           AS focos_no_dia
FROM   focos_incendio
WHERE  data_foco >= TRUNC(SYSDATE) - 30
GROUP  BY TRUNC(data_foco)
ORDER  BY dia;

-- ------------------------------------------------------------
-- 3) Correlacao clima x focos por BIOMA  (JOIN entre tabelas)
--    Junta focos com clima e agrega por bioma.
-- ------------------------------------------------------------
SELECT f.bioma,
       COUNT(*)                       AS qtd_focos,
       ROUND(AVG(c.temperatura), 1)   AS temp_media,
       ROUND(AVG(c.umidade), 1)       AS umidade_media,
       ROUND(AVG(c.vento), 1)         AS vento_medio,
       SUM(c.estacao_seca)            AS focos_em_seca
FROM   focos_incendio f
JOIN   clima_associado c ON c.id_externo = f.id_externo
GROUP  BY f.bioma
ORDER  BY qtd_focos DESC;

-- ------------------------------------------------------------
-- 4) Top 10 areas mais criticas por intensidade (FRP)
--    (ordenacao + limite de linhas)
-- ------------------------------------------------------------
SELECT id_externo, estado, bioma, frp, brilho, data_foco
FROM   focos_incendio
ORDER  BY frp DESC
FETCH  FIRST 10 ROWS ONLY;

-- ------------------------------------------------------------
-- 5) Estatisticas por satelite  (MIN / MAX / AVG / COUNT)
-- ------------------------------------------------------------
SELECT satelite,
       COUNT(*)            AS qtd,
       MIN(frp)            AS frp_min,
       ROUND(AVG(frp), 1)  AS frp_medio,
       MAX(frp)            AS frp_max,
       ROUND(AVG(confianca), 1) AS confianca_media
FROM   focos_incendio
GROUP  BY satelite
HAVING COUNT(*) > 0
ORDER  BY frp_medio DESC;

-- ------------------------------------------------------------
-- 6) Focos criticos cruzados com classificacao da CNN
--    JOIN de 3 tabelas (foco + clima + imagem) + filtros compostos.
--    LEFT JOIN com imagens_satelite_metadata garante linhas mesmo
--    quando a camada ACV ainda nao classificou o tile.
-- ------------------------------------------------------------
SELECT f.estado,
       f.bioma,
       COUNT(*)                       AS focos_criticos,
       ROUND(AVG(f.frp), 1)           AS frp_medio,
       ROUND(AVG(c.umidade), 1)       AS umidade_media,
       ROUND(MAX(f.frp), 1)           AS frp_max
FROM   focos_incendio f
JOIN   clima_associado c                ON c.id_externo = f.id_externo
LEFT   JOIN imagens_satelite_metadata i ON i.id_externo = f.id_externo
WHERE  f.frp > 50
  AND  (i.classificacao = 'fogo' OR i.classificacao IS NULL)
GROUP  BY f.estado, f.bioma
ORDER  BY focos_criticos DESC;
