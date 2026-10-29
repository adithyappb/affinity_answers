-- Rfam public MySQL database (read-only)
--   mysql --user rfamro --host mysql-rfam-public.ebi.ac.uk --port 4497 --database Rfam
--
-- Tables used
--   taxonomy    (ncbi_id PK, species, tax_string, ...)
--   rfamseq     (rfamseq_acc PK, ncbi_id -> taxonomy, length, ...)
--   family      (rfam_acc PK, rfam_id = family name, description, ...)
--   full_region (rfam_acc -> family, rfamseq_acc -> rfamseq, ...)  family <-> sequence link


-- name: q1_acacia_types
-- How many types of Acacia plants are in the taxonomy table?
-- Each taxonomy row is one taxon; species names start with the genus, so
-- 'Acacia %' (note the space) matches Acacia species but not e.g. 'Acaciella'.
SELECT COUNT(DISTINCT species) AS acacia_types
FROM taxonomy
WHERE species LIKE 'Acacia %';


-- name: q2_longest_wheat_sequence
-- Which type of wheat has the longest DNA sequence?
-- Wheat is the genus Triticum. Join each sequence to its organism, keep the longest.
SELECT t.species,
       r.rfamseq_acc,
       r.length
FROM rfamseq AS r
JOIN taxonomy AS t ON t.ncbi_id = r.ncbi_id
WHERE t.species LIKE 'Triticum %'
ORDER BY r.length DESC
LIMIT 1;


-- name: q3_families_page_9
-- Families whose longest sequence > 1,000,000, longest first,
-- page 9 at 15 rows per page  ->  OFFSET (9 - 1) * 15 = 120.
--
-- "MAX(length) > 1,000,000" holds exactly when a family has at least one
-- sequence longer than 1,000,000, and that MAX is then taken over those long
-- sequences alone. So filtering sequences first (WHERE, before the join)
-- gives the same answer as HAVING after the join, but joins only the long
-- sequences instead of all of full_region; the slow form times out on the
-- public server. family is joined last, onto the small aggregated result.
-- rfam_acc is a tie-breaker so page boundaries are deterministic.
SELECT f.rfam_acc,
       f.rfam_id       AS family_name,
       fam.max_length
FROM (
    SELECT fr.rfam_acc,
           MAX(r.length) AS max_length
    FROM rfamseq AS r
    JOIN full_region AS fr ON fr.rfamseq_acc = r.rfamseq_acc
    WHERE r.length > 1000000
    GROUP BY fr.rfam_acc
) AS fam
JOIN family AS f ON f.rfam_acc = fam.rfam_acc
ORDER BY fam.max_length DESC, f.rfam_acc
LIMIT 15 OFFSET 120;
