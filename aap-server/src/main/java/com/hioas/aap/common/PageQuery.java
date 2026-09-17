package com.hioas.aap.common;

/**
 * 分页请求参数（默认 20、上限 200；非法值一律夹取而不是抛错——列表页容忍脏参数）。
 */
public record PageQuery(int page, int pageSize) {

    public static final int DEFAULT_PAGE_SIZE = 20;
    public static final int MAX_PAGE_SIZE = 200;

    public static PageQuery of(Integer page, Integer pageSize) {
        int p = page == null || page < 1 ? 1 : page;
        int size = pageSize == null || pageSize < 1 ? DEFAULT_PAGE_SIZE : Math.min(pageSize, MAX_PAGE_SIZE);
        return new PageQuery(p, size);
    }

    public int offset() {
        return (page - 1) * pageSize;
    }
}
