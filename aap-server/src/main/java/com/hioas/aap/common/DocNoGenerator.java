package com.hioas.aap.common;

import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 业务单号生成（真源：17-spec §3 / 10-PRD §3.1）。
 *
 * <p>用数据库序列而不是「count+1」：并发下不重号、不依赖行数、重启不跳号（除事务回滚的正常损耗）。
 * 格式：
 * <ul>
 *   <li>provider_no：{@code AAP-P-{yyyy}-{4位}}；provider_code：{@code AAP-P-{6位}}</li>
 *   <li>job_no：{@code DJ{yyyyMMdd}{4位}}；report_no：{@code RP{yyyyMMdd}{4位}}</li>
 *   <li>quote_no：{@code Q{yyyyMMdd}{6位}}；contract_no：{@code HT{yyyyMMdd}{4位}}</li>
 *   <li>statement_no：{@code ST{yyyyMM}{4位}}；sync_task_no：{@code SY{yyyyMMdd}{4位}}</li>
 * </ul>
 */
@Component
public class DocNoGenerator {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final DateTimeFormatter MONTH = DateTimeFormatter.ofPattern("yyyyMM");

    private final JdbcTemplate jdbc;

    public DocNoGenerator(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public String providerCode() {
        return "AAP-P-" + pad(nextVal("seq_provider_code"), 6);
    }

    public String providerNo() {
        int year = LocalDate.now(ZoneOffset.UTC).getYear();
        return "AAP-P-" + year + "-" + pad(nextVal("seq_provider_no"), 4);
    }

    public String detectionJobNo() {
        return "DJ" + today() + pad(nextVal("seq_detection_job"), 4);
    }

    public String reportNo() {
        return "RP" + today() + pad(nextVal("seq_report"), 4);
    }

    public String quoteNo() {
        return "Q" + today() + pad(nextVal("seq_quote"), 6);
    }

    public String contractNo() {
        return "HT" + today() + pad(nextVal("seq_contract"), 4);
    }

    public String statementNo() {
        return "ST" + LocalDate.now(ZoneOffset.UTC).format(MONTH) + pad(nextVal("seq_statement"), 4);
    }

    public String syncTaskNo() {
        return "SY" + today() + pad(nextVal("seq_sync_task"), 4);
    }

    private String today() {
        return LocalDate.now(ZoneOffset.UTC).format(DAY);
    }

    private long nextVal(String sequence) {
        Long value = jdbc.queryForObject("select nextval('" + sequence + "')", Long.class);
        return value == null ? 0L : value;
    }

    private static String pad(long value, int width) {
        return String.format("%0" + width + "d", value);
    }
}
