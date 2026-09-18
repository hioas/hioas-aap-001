package com.hioas.aap.settlement;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 结算单持久化。 */
@Mapper
public interface SettlementStatementMapper extends BaseMapper<SettlementStatementEntity> {
}
