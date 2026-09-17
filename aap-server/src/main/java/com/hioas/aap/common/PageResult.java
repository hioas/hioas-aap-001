package com.hioas.aap.common;

import java.util.List;

/**
 * 分页响应体：{@code data:{items,page,pageSize,total}}（`02-API接口模型清单.md` §0）。
 *
 * <p><b>字段名以客户端为准</b>：`aap-client/src/api/*.ts` 的分页读取统一走 {@code items}
 * （如 `report.ts` 的 {@code items?: {...}[]}）。此前实现用 {@code list} 会导致所有列表页取不到数据，
 * 属契约偏差 → 已按客户端真源修正（见 `.agents/state/aap-server-tdd-state.md` R07）。
 *
 * @param items    当前页数据
 * @param page     页码（从 1 起）
 * @param pageSize 每页条数（默认 20，上限 200）
 * @param total    符合条件的总条数
 */
public record PageResult<T>(List<T> items, int page, int pageSize, long total) {

    public static <T> PageResult<T> of(List<T> items, int page, int pageSize, long total) {
        return new PageResult<>(items == null ? List.of() : items, page, pageSize, total);
    }

    public static <T> PageResult<T> empty(int page, int pageSize) {
        return new PageResult<>(List.of(), page, pageSize, 0L);
    }
}
