package com.hioas.aap.common;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedJdbcTypes;

/**
 * jsonb 列读写：实体里保存**原始 JSON 字符串**，由 {@link JsonCodec} 在服务层转成类型化对象。
 *
 * <p>为什么不直接映射成 Map/List：字段级契约要稳定（哪些键存在、什么类型），
 * 泛型 Map 会把拼写错误留到运行时。也不依赖 MyBatis-Flex 内置的 Jackson2 版 handler
 * （Spring Boot 4 默认 Jackson 3，classpath 上没有 com.fasterxml.jackson.databind）。
 *
 * <p>写参数用 {@code Types.OTHER}（PG 的 unspecified 类型）：服务端按目标列 jsonb 推断转换，
 * 既不用把 postgresql 驱动提到 compile scope，也不会出现
 * "column is of type jsonb but expression is of type character varying"。
 */
@MappedJdbcTypes(JdbcType.OTHER)
public class JsonbTypeHandler extends BaseTypeHandler<String> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, String parameter, JdbcType jdbcType)
            throws SQLException {
        ps.setObject(i, parameter, Types.OTHER);
    }

    @Override
    public String getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return rs.getString(columnName);
    }

    @Override
    public String getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return rs.getString(columnIndex);
    }

    @Override
    public String getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return cs.getString(columnIndex);
    }
}
