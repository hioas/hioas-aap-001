package com.hioas.aap.common;

import java.util.List;

/**
 * 分页响应体：{@code data:{list,page,pageSize,total}}（`02-API接口模型清单.md` §0）。
 *
 * @param list     当前页数据
 * @param page     页码（从 1 起）
 * @param pageSize 每页条数（默认 20，上限 200）
 * @param total    符合条件的总条数
 */
public record PageResult<T>(List<T> list, int page, int pageSize, long total) {

    public static <T> PageResult<T> of(List<T> list, int page, int pageSize, long total) {
        return new PageResult<>(list == null ? List.of() : list, page, pageSize, total);
    }

    public static <T> PageResult<T> empty(int page, int pageSize) {
        return new PageResult<>(List.of(), page, pageSize, 0L);
    }
}
