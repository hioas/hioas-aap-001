package com.hioas.aap.review;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 审核记录（只插不改，时间线天然有序）。 */
@Mapper
public interface ReviewRecordMapper extends BaseMapper<ReviewRecordEntity> {
}
