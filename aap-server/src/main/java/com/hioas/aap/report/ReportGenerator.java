package com.hioas.aap.report;

/**
 * 报告生成接口：检测完成后由 {@code DetectionService} 调用，避免「检测 ←→ 报告」双向依赖。
 */
public interface ReportGenerator {

    /** 为检测任务生成报告（幂等）；返回报告 id。 */
    Long generate(Long jobId);
}
