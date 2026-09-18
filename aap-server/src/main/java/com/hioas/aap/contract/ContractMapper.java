package com.hioas.aap.contract;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 合同持久化（T10 仅生成；T11 扩展签发/签署状态流转）。 */
@Mapper
public interface ContractMapper extends BaseMapper<ContractEntity> {
}
