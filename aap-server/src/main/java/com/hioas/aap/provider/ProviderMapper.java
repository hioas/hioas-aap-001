package com.hioas.aap.provider;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 供应商主体 Mapper（MyBatis-Flex：继承 {@link BaseMapper} 即得 CRUD + 条件构造 + 分页）。 */
@Mapper
public interface ProviderMapper extends BaseMapper<ProviderEntity> {
}
