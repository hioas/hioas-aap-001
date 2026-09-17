package com.hioas.aap.report;

import com.mybatisflex.core.BaseMapper;
import java.time.OffsetDateTime;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface ReportMapper extends BaseMapper<ReportEntity> {

    /** 供应商最近一次「通过」报告的检测时间（AC-49 定期复测判定用）。 */
    @Select("""
            select max(detected_at) from aap_report
             where provider_id = #{providerId} and result = 'PASS' and deleted = false
            """)
    OffsetDateTime selectLatestPassedAt(@Param("providerId") Long providerId);
}
