package com.hioas.aap.settlement;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 打款记录持久化（状态流转在 {@link SettlementService} 用显式 SQL，读写同源）。 */
@Mapper
public interface PaymentRecordMapper extends BaseMapper<PaymentRecordEntity> {
}
