package com.hioas.aap.catalog;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 厂商（管理端维护；H5 凭证页只读消费其 enabled 状态）。 */
@Mapper
public interface VendorMapper extends BaseMapper<VendorEntity> {
}
