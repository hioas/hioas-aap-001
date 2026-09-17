package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.hioas.aap.support.DbTestBase;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T02 · 持久层底座（MyBatis-Flex）：雪花 ID、审计字段自动填充、逻辑删除、乐观锁、分页。
 */
class PersistenceBaseTest extends DbTestBase {

    @Autowired
    private ProviderMapper providerMapper;

    @AfterEach
    void clearActor() {
        AuditContext.clear();
    }

    private ProviderEntity newProvider(String code) {
        ProviderEntity entity = new ProviderEntity();
        entity.setProviderCode(code);
        entity.setProviderNo("AAP-P-2026-" + code);
        entity.setCompanyName("测试供应商 " + code);
        entity.setShortName("T" + code);
        entity.setShortCode(code.toLowerCase());
        entity.setStatus("PENDING_CREDENTIAL");
        entity.setRecheckIntervalDays(30);
        entity.setManualOverride(false);
        entity.setCompleteness((short) 0);
        return entity;
    }

    @Test
    @DisplayName("插入：雪花 ID 生成、审计字段自动填充（created_at/updated_at/deleted/version）")
    void insertFillsSnowflakeIdAndAuditFields() {
        AuditContext.set(new AuditContext.Actor(9001L, "PROVIDER", "张三", "127.0.0.1"));

        ProviderEntity entity = newProvider("P0001");
        int rows = providerMapper.insert(entity);

        assertThat(rows).isEqualTo(1);
        assertThat(entity.getId()).as("雪花 ID 必须由框架生成").isNotNull().isPositive();
        assertThat(entity.getCreatedAt()).isNotNull();
        assertThat(entity.getUpdatedAt()).isNotNull();
        assertThat(entity.getDeleted()).isFalse();
        assertThat(entity.getVersion()).isZero();
        assertThat(entity.getCreatedBy()).isEqualTo(9001L);
        assertThat(entity.getUpdatedBy()).isEqualTo(9001L);

        ProviderEntity reloaded = providerMapper.selectOneById(entity.getId());
        assertThat(reloaded).isNotNull();
        assertThat(reloaded.getProviderCode()).isEqualTo("P0001");
        assertThat(reloaded.getCreatedAt()).isNotNull();
    }

    @Test
    @DisplayName("雪花 ID 不重复：100 次插入得到 100 个唯一 ID")
    void snowflakeIdsAreUnique() {
        Set<Long> ids = new HashSet<>();
        for (int i = 0; i < 100; i++) {
            ProviderEntity entity = newProvider("S%04d".formatted(i));
            providerMapper.insert(entity);
            ids.add(entity.getId());
        }
        assertThat(ids).hasSize(100);
    }

    @Test
    @DisplayName("逻辑删除：deleteById 后查询不可见，但行仍在库中且 deleted=true（审计留痕）")
    void logicDeleteKeepsRowButHidesIt() {
        ProviderEntity entity = newProvider("P0002");
        providerMapper.insert(entity);
        Long id = entity.getId();

        providerMapper.deleteById(id);

        assertThat(providerMapper.selectOneById(id)).as("逻辑删除后对应用不可见").isNull();
        Boolean deleted = jdbc.queryForObject(
                "select deleted from aap_provider where id = ?", Boolean.class, id);
        assertThat(deleted).as("行必须保留（不得物理删除）").isTrue();
        Long remaining = jdbc.queryForObject("select count(*) from aap_provider where id = ?", Long.class, id);
        assertThat(remaining).isEqualTo(1L);
    }

    @Test
    @DisplayName("乐观锁：携带过期 version 的更新不得覆盖新数据（DB 中 version 与内容都被守住）")
    void optimisticLockRejectsStaleUpdate() {
        ProviderEntity entity = newProvider("P0003");
        providerMapper.insert(entity);
        Long id = entity.getId();

        ProviderEntity loaded = providerMapper.selectOneById(id);
        loaded.setCompanyName("第一次修改");
        assertThat(providerMapper.update(loaded)).as("首次更新（version=0）应成功").isEqualTo(1);

        // 同一实例（内存里 version 仍是 0）再更新一次 → 过期写入必须被乐观锁挡下
        int staleRows = 0;
        try {
            staleRows = providerMapper.update(loaded);
        } catch (RuntimeException expected) {
            // 以异常形式拒绝过期写入同样算通过
        }
        assertThat(staleRows).as("过期 version 的更新必须影响 0 行").isZero();

        assertThat(jdbc.queryForObject("select company_name from aap_provider where id = ?", String.class, id))
                .isEqualTo("第一次修改");
        assertThat(jdbc.queryForObject("select version from aap_provider where id = ?", Integer.class, id))
                .isEqualTo(1);

        // 重新取数（拿到最新 version）后可以继续更新
        ProviderEntity fresh = providerMapper.selectOneById(id);
        fresh.setCompanyName("第二次修改");
        assertThat(providerMapper.update(fresh)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select version from aap_provider where id = ?", Integer.class, id))
                .isEqualTo(2);
        assertThat(jdbc.queryForObject("select company_name from aap_provider where id = ?", String.class, id))
                .isEqualTo("第二次修改");
    }

    @Test
    @DisplayName("分页：Page.of(page,pageSize) 返回 total 与当前页记录（默认排序稳定）")
    void paginationWorks() {
        for (int i = 0; i < 7; i++) {
            providerMapper.insert(newProvider("Q%04d".formatted(i)));
        }
        Page<ProviderEntity> page = providerMapper.paginate(Page.of(1, 3), QueryWrapper.create());
        assertThat(page.getTotalRow()).isEqualTo(7);
        assertThat(page.getRecords()).hasSize(3);
        assertThat(page.getPageNumber()).isEqualTo(1);
        assertThat(page.getTotalPage()).isEqualTo(3);
    }
}
