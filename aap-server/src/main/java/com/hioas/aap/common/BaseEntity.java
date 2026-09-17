package com.hioas.aap.common;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import java.time.OffsetDateTime;

/**
 * 业务表通用审计基类（`docs/backend/01-ER数据模型.md` §1）。
 *
 * <ul>
 *   <li>{@code id}：雪花 bigint，由 MyBatis-Flex 生成（非自增、非 DB 序列）</li>
 *   <li>{@code created_at / updated_at}：timestamptz UTC，由审计监听器填充</li>
 *   <li>{@code deleted}：逻辑删除（查询自动过滤，行保留留痕）</li>
 *   <li>{@code version}：乐观锁（更新时自动带 version 条件并递增）</li>
 * </ul>
 *
 * <p>注意：字段名与列名一致（snake_case），不依赖驼峰转换，避免"字典名 ↔ 列名"两套命名。
 */
public abstract class BaseEntity {

    @Id(keyType = KeyType.Generator, value = "snowFlakeId")
    @Column("id")
    private Long id;

    @Column("created_at")
    private OffsetDateTime createdAt;

    @Column("updated_at")
    private OffsetDateTime updatedAt;

    @Column("created_by")
    private Long createdBy;

    @Column("updated_by")
    private Long updatedBy;

    @Column(value = "deleted", isLogicDelete = true)
    private Boolean deleted;

    @Column(value = "version", version = true)
    private Integer version;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Long getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(Long createdBy) {
        this.createdBy = createdBy;
    }

    public Long getUpdatedBy() {
        return updatedBy;
    }

    public void setUpdatedBy(Long updatedBy) {
        this.updatedBy = updatedBy;
    }

    public Boolean getDeleted() {
        return deleted;
    }

    public void setDeleted(Boolean deleted) {
        this.deleted = deleted;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }
}
