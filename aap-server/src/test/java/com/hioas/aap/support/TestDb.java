package com.hioas.aap.support;

import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * 测试库清场工具：清空全部业务表（含分区父表，级联清分区子表），并复位 `seq_*` 独立序列。
 *
 * <p>为什么必须复位序列：`truncate ... restart identity` 只重置**表自有** identity/serial 列关联的序列，
 * 而本项目的单号序列（V2/V4/V5/V12/V14/V15/V16 里的 `create sequence if not exists seq_*`）是独立对象，
 * 不受其影响。若不复位，用例里生成的单号（如 `CFG-B{yyyyMM}-{4位}`、`DJ{yyyyMMdd}{4位}`）宽度取决于
 * **测试库累计历史**：序列过万后 `%04d` 变成 5 位，钉死位数的契约断言就从某一轮起永久变红
 * （R773 实测：同一被测提交 run1 绿、run2 红，`CFG-B202610-10009` 不匹配 `^CFG-B\d{6}-\d{4}$`）。
 * 这属于「夹具依赖共享历史」，修夹具而不是改期望值。
 */
public final class TestDb {

    private static final String BUSINESS_TABLES_SQL = """
            select c.relname from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind in ('r', 'p') and c.relname like 'aap\\_%'
              and not exists (select 1 from pg_inherits i where i.inhrelid = c.oid)
            order by c.relname
            """;

    private static final String BUSINESS_SEQUENCES_SQL = """
            select sequencename from pg_sequences where sequencename like 'seq\\_%'
            order by sequencename
            """;

    private TestDb() {
    }

    public static List<String> businessTables(JdbcTemplate jdbc) {
        return jdbc.queryForList(BUSINESS_TABLES_SQL, String.class);
    }

    /** 单号序列名集合（`seq_*`）；用于清场复位与「复位是否真的发生」的守卫。 */
    public static List<String> businessSequences(JdbcTemplate jdbc) {
        return jdbc.queryForList(BUSINESS_SEQUENCES_SQL, String.class);
    }

    public static void truncateAll(JdbcTemplate jdbc) {
        List<String> tables = businessTables(jdbc);
        if (!tables.isEmpty()) {
            jdbc.execute("truncate table " + String.join(", ", tables) + " restart identity cascade");
        }
        resetSequences(jdbc);
    }

    /** 把全部 `seq_*` 独立序列复位到 1（等价于「本用例从未发过号」）。返回被复位的序列名。 */
    public static List<String> resetSequences(JdbcTemplate jdbc) {
        List<String> sequences = businessSequences(jdbc);
        for (String sequence : sequences) {
            jdbc.execute("alter sequence " + sequence + " restart with 1");
        }
        return sequences;
    }
}
