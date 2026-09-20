package com.hioas.aap.catalog;

import com.mybatisflex.core.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 模型目录（H5 端「接入凭证」模型下拉的数据源）。 */
@Mapper
public interface ModelCatalogMapper extends BaseMapper<ModelCatalogEntity> {
}
