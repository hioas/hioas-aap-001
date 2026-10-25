package com.hioas.aap.support;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * 清场隔离守卫（R773 红基线回归）：{@link TestDb#truncateAll} 必须同时复位 {@code seq_*} 独立序列。
 *
 * <p>为什么值得单独一条用例：单号生成器（{@code DocNoGenerator}）用数据库序列 + 零填充宽度，
 * 而 {@code truncate ... restart identity} **不重置** 独立 {@code create sequence} 创建的序列。
 * 不复位时，用例产出的单号宽度取决于测试库的累计历史 —— 序列过万后「4 位」变 5 位，
 * 钉死位数的契约断言会从某一轮起**永久**变红（真实返工：同一被测提交 run1 绿 / run2 红）。
 * 这条用例把「清场漏了序列」变成机器可发现的缺陷，而不是等某一轮撞上 10000。
 */
class TestDbIsolationTest extends DbTestBase {

    @Test
    @DisplayName("R773 清场隔离：truncateAll 复位全部 seq_* 序列（单号宽度不随跑测累计漂移）")
    void truncateResetsSequences() {
        // 正向对照 1：序列集合非空（否则「全部为 null」是空转假绿，踩坑 98）
        List<String> sequences = TestDb.businessSequences(jdbc);
        assertThat(sequences).as("seq_* 序列集合不得为空").isNotEmpty();

        // 正向对照 2：先让序列真的前进，证明后面的「已复位」是本方法造成的，而不是库本来干净
        Long advanced = jdbc.queryForObject("select nextval('seq_config_batch')", Long.class);
        assertThat(advanced).as("序列必须先前进").isNotNull().isGreaterThan(0L);
        assertThat(advancedValues("seq_config_batch")).as("前进后应能读到 last_value").isNotNull();

        TestDb.truncateAll(jdbc);

        // 断言：全部 seq_* 已回到「未发号」状态（restart with 1 后 pg_sequences.last_value 为 null）
        Long notReset = jdbc.queryForObject(
                "select count(*) from pg_sequences where sequencename like 'seq\\_%' and last_value is not null",
                Long.class);
        assertThat(notReset).as("truncateAll 之后仍处于已发号状态的 seq_* 个数").isZero();
        assertThat(advancedValues("seq_config_batch")).as("被推进过的序列也必须复位").isNull();
        assertThat(TestDb.resetSequences(jdbc)).as("复位集合与业务序列集合同源").isEqualTo(sequences);
    }

    private Long advancedValues(String sequence) {
        return jdbc.queryForObject(
                "select last_value from pg_sequences where sequencename = ?", Long.class, sequence);
    }
}
