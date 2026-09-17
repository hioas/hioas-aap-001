package com.hioas.aap.support;

import java.util.List;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

/**
 * 数据层测试基类：真实 PostgreSQL（`aap_server_test`）+ 每个用例前清空业务表。
 *
 * <p>为什么清表而不是 {@code @Transactional} 回滚：本项目的验收测试走**真实 HTTP**（跨线程），
 * 事务不会传播到服务端线程，回滚会给出「绿了但数据没清」的假象。清表是确定的。
 */
@SpringBootTest
@ActiveProfiles("test")
public abstract class DbTestBase {

    @Autowired
    protected DataSource dataSource;

    @Autowired
    protected JdbcTemplate jdbc;

    @BeforeEach
    void truncateApplicationTables() {
        List<String> tables = jdbc.queryForList(
                "select tablename from pg_tables where schemaname = 'public' and tablename like 'aap\\_%' order by tablename",
                String.class);
        if (!tables.isEmpty()) {
            jdbc.execute("truncate table " + String.join(", ", tables) + " restart identity cascade");
        }
    }
}
