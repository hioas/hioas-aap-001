package com.hioas.aap.contract;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 合同签署记录持久化（只插不改；状态流转在 {@link ContractService} 用显式 SQL）。 */
@Mapper
public interface ContractSignMapper extends BaseMapper<ContractSignEntity> {
}
