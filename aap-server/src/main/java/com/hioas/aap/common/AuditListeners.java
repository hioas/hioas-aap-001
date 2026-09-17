package com.hioas.aap.common;

import com.mybatisflex.annotation.AbstractInsertListener;
import com.mybatisflex.annotation.AbstractUpdateListener;
import java.time.OffsetDateTime;

/**
 * 审计字段自动填充（插入 / 更新各一个监听器，由 {@code @Table(onInsert=..., onUpdate=...)} 挂载）。
 *
 * <p>为什么不用 DB 默认值：应用层填充才能带上操作者与统一时钟，测试也可确定性地断言；
 * DB 端仍保留 {@code default now()} 作为兜底（绕过 ORM 的裸 SQL 也安全）。
 */
public final class AuditListeners {

    private AuditListeners() {
    }

    /** 插入：补 created_at/updated_at、created_by/updated_by、deleted=false、version=0。 */
    public static class Insert extends AbstractInsertListener<BaseEntity> {

        @Override
        public void doInsert(BaseEntity entity) {
            if (entity == null) {
                return;
            }
            OffsetDateTime now = OffsetDateTime.now();
            if (entity.getCreatedAt() == null) {
                entity.setCreatedAt(now);
            }
            if (entity.getUpdatedAt() == null) {
                entity.setUpdatedAt(now);
            }
            if (entity.getDeleted() == null) {
                entity.setDeleted(Boolean.FALSE);
            }
            if (entity.getVersion() == null) {
                entity.setVersion(0);
            }
            Long actorId = AuditContext.currentActorId().orElse(null);
            if (entity.getCreatedBy() == null) {
                entity.setCreatedBy(actorId);
            }
            if (entity.getUpdatedBy() == null) {
                entity.setUpdatedBy(actorId);
            }
        }
    }

    /** 更新：刷新 updated_at 与 updated_by（version 由乐观锁插件递增）。 */
    public static class Update extends AbstractUpdateListener<BaseEntity> {

        @Override
        public void doUpdate(BaseEntity entity) {
            if (entity == null) {
                return;
            }
            entity.setUpdatedAt(OffsetDateTime.now());
            Long actorId = AuditContext.currentActorId().orElse(null);
            if (actorId != null) {
                entity.setUpdatedBy(actorId);
            }
        }
    }
}
