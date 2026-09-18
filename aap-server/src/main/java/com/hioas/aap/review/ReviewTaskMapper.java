package com.hioas.aap.review;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 审核任务持久化。
 *
 * <p>只保留「插入」与「按报价单查任务」两条 ORM 路径；状态流转（领取/通过/驳回/复位）
 * 与所有读查询都在 {@link ReviewService} 里用显式 SQL 执行——同一请求内必须做到
 * 「写和读走同一个客户端」，否则会出现「响应还是旧状态」的读写不一致（见 ReviewService 里的说明）。
 */
@Mapper
public interface ReviewTaskMapper extends BaseMapper<ReviewTaskEntity> {

    /** 报价单对应的审核任务（1:1；逻辑删除过滤）。 */
    @Select("""
            select * from aap_review_task where quote_id = #{quoteId} and deleted = false limit 1
            """)
    ReviewTaskEntity selectByQuote(@Param("quoteId") Long quoteId);
}
