package com.hioas.aap.support;

import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;

/** 测试库清场工具：清空全部业务表（含分区父表，级联清分区子表）。 */
public final class TestDb {

    private static final String BUSINESS_TABLES_SQL = """
            select c.relname from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind in ('r', 'p') and c.relname like 'aap\\_%'
              and not exists (select 1 from pg_inherits i where i.inhrelid = c.oid)
            order by c.relname
            """;

    private TestDb() {
    }

    public static List<String> businessTables(JdbcTemplate jdbc) {
        return jdbc.queryForList(BUSINESS_TABLES_SQL, String.class);
    }

    public static void truncateAll(JdbcTemplate jdbc) {
        List<String> tables = businessTables(jdbc);
        if (!tables.isEmpty()) {
            jdbc.execute("truncate table " + String.join(", ", tables) + " restart identity cascade");
        }
    }
}
