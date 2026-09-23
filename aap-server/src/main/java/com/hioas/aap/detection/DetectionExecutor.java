package com.hioas.aap.detection;

import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.credential.CredentialEntity;
import com.hioas.aap.credential.CredentialMapper;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

/**
 * 检测任务执行器：消费 {@code QUEUED} 的检测任务（**缺陷 1 的修复**）。
 *
 * <p>在此之前 {@code DetectionService.recordProbeResults} **全仓零调用方** ——
 * 任务建了就无人消费，永远停在 {@code QUEUED}（实测 {@code updated_at == created_at}，
 * 插入后再没被任何代码碰过），凭证卡在 {@code detection_status=RUNNING}，
 * 再预检即报 {@code E-1301}，该凭证**永久无法重试**，{@code QUEUED} 无限堆积。
 *
 * <p>本执行器按固定间隔扫描待处理任务：置 RUNNING → 跑探针 → 回写结果。
 * 回写走既有的 {@link DetectionService#recordProbeResults}，因此
 * **打分、结论、报告、站内信全部沿用既有逻辑**（不在执行器里重造判定）。
 *
 * <p>失败处置：探针整体失败或执行期异常都要**回写**（全项 FAILED 的分数列表），
 * 由 {@code summarize} 给出诚实结论 —— 否则任务会一直卡 QUEUED/RUNNING，
 * 又回到「永久无法重试」的老问题。
 *
 * <p>调度参数（{@code app.detection.execute-*}）：生产为 15s/20s，测试环境在
 * {@code application-test.yml} 里调到极大以关掉定时器（与 {@code recheck-enabled} 同一考虑：
 * 定时器与用例抢库会产生不可复现的随机失败），其逻辑由测试直接调 {@link #scan()} 覆盖。
 */
@Component
public class DetectionExecutor {

    private static final Logger log = LoggerFactory.getLogger(DetectionExecutor.class);

    /** 每轮最多处理多少个任务（避免一次扫太多把上游打爆）。 */
    private static final int BATCH = 3;

    private final DetectionJobMapper jobMapper;
    private final CredentialMapper credentialMapper;
    private final DetectionService detectionService;
    private final DetectionProbeRunner probeRunner;

    public DetectionExecutor(DetectionJobMapper jobMapper, CredentialMapper credentialMapper,
                             DetectionService detectionService, DetectionProbeRunner probeRunner) {
        this.jobMapper = jobMapper;
        this.credentialMapper = credentialMapper;
        this.detectionService = detectionService;
        this.probeRunner = probeRunner;
    }

    /** 定时扫描并处理待检测任务。 */
    @Scheduled(fixedDelayString = "${app.detection.execute-delay-ms:15000}",
            initialDelayString = "${app.detection.execute-initial-delay-ms:20000}")
    public void scan() {
        List<DetectionJobEntity> jobs;
        try {
            jobs = jobMapper.selectListByQuery(QueryWrapper.create()
                    .where("status = ?", "QUEUED")
                    .and("deleted = false")
                    .orderBy("id asc")
                    .limit(BATCH));
        } catch (RuntimeException e) {
            log.warn("检测任务扫描失败（下轮重试）", e);
            return;
        }
        for (DetectionJobEntity job : jobs) {
            try {
                runOne(job);
            } catch (RuntimeException e) {
                // 单个任务失败不能拖垮整轮扫描；状态已由回写或下轮扫描兜底
                log.warn("检测任务执行异常 job_id={}", job.getId(), e);
            }
        }
    }

    /** 执行单个任务：置 RUNNING → 跑探针 → 回写结果。 */
    private void runOne(DetectionJobEntity job) {
        CredentialEntity credential = credentialMapper.selectOneById(job.getCredentialId());
        if (credential == null) {
            log.warn("检测任务 {} 的凭证 {} 不存在：按全项 FAILED 回写（不留 QUEUED 死区）",
                    job.getId(), job.getCredentialId());
            writeFailure(job.getId(), "凭证不存在或已删除，无法探测");
            return;
        }

        job.setStatus("RUNNING");
        job.setStartedAt(OffsetDateTime.now(ZoneOffset.UTC));
        jobMapper.update(job);

        // 模型取任务的**快照**（每条检测记录版本化，用户口径 2026-09-23）；任务没快照时退回凭证当前清单
        String modelListJson = job.getModelList() == null || job.getModelList().isBlank()
                ? credential.getModelList() : job.getModelList();
        List<String> models = parseModelNames(modelListJson);

        try {
            DetectionProbeRunner.ProbeOutcome outcome = probeRunner.run(
                    credential.getBaseUrl(), credential.getApiKeyCipher(), models);
            detectionService.recordProbeResults(job.getId(), outcome.scores(),
                    outcome.metricsByProbe(), outcome.evidenceByProbe());
            log.info("检测任务完成 job_id={} credential_id={} 探针数={}",
                    job.getId(), credential.getId(), outcome.scores().size());
        } catch (RuntimeException e) {
            // 探针或回写异常也必须让任务离开 RUNNING：否则凭证卡在 RUNNING，再预检仍是 E-1301
            log.warn("检测任务执行异常 job_id={}，按全项 FAILED 回写", job.getId(), e);
            writeFailure(job.getId(), "探针执行异常：" + e.getClass().getSimpleName());
        }
    }

    /** 全项 FAILED 回写（原因只写异常类型/业务原因，不含密钥与上游报文）。 */
    private void writeFailure(Long jobId, String reason) {
        try {
            detectionService.recordProbeResults(jobId, DetectionProbeRunner.allFailed(reason).scores(),
                    Map.of(), Map.of("failure", reason));
        } catch (RuntimeException e) {
            log.warn("检测任务失败回写未成功 job_id={}（下轮扫描会再取一次，任务不会静默消失）", jobId, e);
        }
    }

    /** 任务的 model_list（jsonb 文本）→ 模型名列表；解析失败返回空表（不猜模型）。 */
    private List<String> parseModelNames(String modelListJson) {
        if (modelListJson == null || modelListJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode root = JsonCodec.readTree(modelListJson);
            if (root == null || !root.isArray()) {
                return List.of();
            }
            List<String> names = new ArrayList<>();
            for (JsonNode row : root) {
                JsonNode name = row.path("model_name");
                if (!name.isMissingNode() && !name.isNull()) {
                    String text = name.asText(null);
                    if (text != null && !text.isBlank()) {
                        names.add(text);
                    }
                }
            }
            return names;
        } catch (RuntimeException e) {
            log.warn("凭证 model_list 解析失败，按空处理（不猜模型）");
            return List.of();
        }
    }
}
