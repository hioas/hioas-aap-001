package com.hioas.aap.adminconfig;

import com.hioas.aap.adminconfig.DetectionConfigViews.DetectionConfig;
import com.hioas.aap.adminconfig.DetectionConfigViews.Probe;
import com.hioas.aap.adminconfig.DetectionConfigViews.ProbeRequest;
import com.hioas.aap.adminconfig.DetectionConfigViews.SaveRequest;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;

/**
 * 检测配置版本（ADM-CFG01…05）。
 *
 * <p>真源：`02-API接口模型清单.md` §2.4 + `01-ER数据模型.md` §`aap_detection_config`/
 * §`aap_detection_config_probe` + `09-检测验证引擎PRD`（检测配置：权重归一化前、超时、否决规则）。
 *
 * <p>四条刻意的口径：
 * <ol>
 *   <li><b>状态机</b> {@code DRAFT → PUBLISHED}，被替代的活版 → {@code SUPERSEDED}：改与发布一律
 *       **条件 UPDATE**（`and status = 'DRAFT'` + 校验影响行数），并发/重复操作只能有一方成功 → 409 {@code E-1601}。</li>
 *   <li><b>版本号全表唯一</b>：`uq_detection_config_version` 决定「新建即新版本号（V1、V2…）」，
 *       同族多版本在当前表结构下不可表达（与报告模板同一取舍，见 tdd-state `D-API-22`）。</li>
 *   <li><b>检测项只能取 D1–D8</b>：允许集合与默认名取自 {@link ProbeScoring}（打分口径的唯一来源），
 *       `weight` 存**归一化前**的原始权重（归一化发生在任务打分时，只对计分项做），
 *       超时缺省按 ER：D1–D3/D6–D8 = 180s，D4/D5 = 600s。</li>
 *   <li><b>修改是 coalesce 语义</b>：请求省略的字段保持原值（省略≠清空）；`probes` 一旦提供即**整体替换**
 *       （旧项软删 + 新项插入），避免「部分更新后权重集合不自洽」。</li>
 * </ol>
 *
 * <p>偏差（记台账 `D-API-23`）：配置发布后**暂未被检测任务消费** —— `DetectionService` 目前仍按
 * {@link ProbeScoring} 默认权重打分，`aap_detection_job.config_snapshot` 也尚未落配置快照。
 * 该接入点跨任务族（T06 检测任务），需人拍板后再做，不在本批次内静默改口径。
 */
@Service
public class DetectionConfigService {

    private static final Logger log = LoggerFactory.getLogger(DetectionConfigService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final int MAX_NAME_LENGTH = 64;

    /** 长耗时探测项（RPM/TPM 需长时间窗口）默认 600s，其余 180s（ER §`aap_detection_config_probe`）。 */
    private static final Set<String> LONG_TIMEOUT_CODES = Set.of("D4", "D5");

    private static final int DEFAULT_TIMEOUT_SECONDS = 180;

    private static final int LONG_TIMEOUT_SECONDS = 600;

    /** 权重列是 numeric(6,4)：最大 99.9999，超范围会在库里炸成 500，必须在入口拦。 */
    private static final double MAX_WEIGHT = 99.9999;

    private static final String CONFIG_COLUMNS = """
            id, version_no, name, pass_score, veto_rule::text as veto_rule,
            status, published_at, created_at, updated_at
            """;

    private static final String PROBE_COLUMNS = """
            probe_code, probe_name, enabled, weight, timeout_seconds, params::text as params
            """;

    private final JdbcTemplate jdbc;
    private final AuditService auditService;

    public DetectionConfigService(JdbcTemplate jdbc, AuditService auditService) {
        this.jdbc = jdbc;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-CFG01 / 03

    /** ADM-CFG01 配置列表（`status` 可选过滤，大小写不敏感；列表也带检测项明细）。 */
    public PageResult<DetectionConfig> list(Integer page, Integer pageSize, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = upper(?)");
            args.add(status.trim());
        }
        Long total = jdbc.queryForObject("select count(*) from aap_detection_config" + where,
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<DetectionConfig> items = jdbc.query("select " + CONFIG_COLUMNS + " from aap_detection_config" + where
                        + " order by created_at desc, id desc limit ? offset ?",
                (rs, rowNum) -> map(rs), pageArgs.toArray());
        for (DetectionConfig item : items) {
            // 逐份补检测项：列表页要展示启停/权重，缺了就只有壳
            item.probes().addAll(probes(Long.valueOf(item.id())));
        }
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    /** ADM-CFG03 配置详情（不存在 → 404 `E-1406`）。 */
    public DetectionConfig detail(Long id) {
        List<DetectionConfig> rows = jdbc.query("select " + CONFIG_COLUMNS
                + " from aap_detection_config where id = ? and deleted = false", (rs, rowNum) -> map(rs), id);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "检测配置不存在");
        }
        DetectionConfig config = rows.get(0);
        config.probes().addAll(probes(id));
        return config;
    }

    // ------------------------------------------------------------------ ADM-CFG02

    /** ADM-CFG02 新建配置（初始 `DRAFT`，新版本号）。 */
    @Transactional
    public DetectionConfig create(AuthPrincipal principal, SaveRequest request) {
        String name = validateName(request.name(), true);
        int passScore = validatePassScore(request.passScore());
        JsonNode vetoRule = validateVetoRule(request.vetoRule());
        validateStatus(request.status(), true);
        List<Probe> probes = resolveProbes(request.probes());

        Long actor = actorId(principal);
        Long id = jdbc.queryForObject("select nextval('seq_detection_config')", Long.class);
        Long versionSeq = jdbc.queryForObject("select nextval('seq_detection_config_version')", Long.class);
        String versionNo = "V" + versionSeq;
        jdbc.update("""
                insert into aap_detection_config (id, version_no, name, pass_score, veto_rule, status,
                    created_at, updated_at, created_by, updated_by, deleted, version)
                values (?, ?, ?, ?, ?::jsonb, 'DRAFT', now(), now(), ?, ?, false, 0)
                """, id, versionNo, name, passScore, JsonCodec.toJson(vetoRule), actor, actor);
        insertProbes(id, probes, actor);
        log.info("检测配置已创建 id={} version={} name={} 检测项={}", id, versionNo, name, probes.size());
        return detail(id);
    }

    // ------------------------------------------------------------------ ADM-CFG04

    /** ADM-CFG04 修改（仅 `DRAFT`；省略字段保持原值；`probes` 提供即整体替换）。 */
    @Transactional
    public DetectionConfig update(AuthPrincipal principal, Long id, SaveRequest request) {
        DetectionConfig before = detail(id);
        validateStatus(request.status(), false);
        String nextName = validateName(request.name() == null ? before.name() : request.name(), true);
        int nextPassScore = request.passScore() == null ? before.passScore() : validatePassScore(request.passScore());
        JsonNode nextVetoRule = request.vetoRule() == null ? before.vetoRule() : validateVetoRule(request.vetoRule());
        List<Probe> nextProbes = request.probes() == null ? null : resolveProbes(request.probes());

        Long actor = actorId(principal);
        int affected = jdbc.update("""
                update aap_detection_config
                   set name = ?, pass_score = ?, veto_rule = ?::jsonb,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, nextName, nextPassScore, JsonCodec.toJson(nextVetoRule), actor, id);
        if (affected != 1) {
            throw new ApiException(ErrorCode.E_1601,
                    "只有草稿状态的检测配置可以修改（当前：" + before.status() + "）");
        }
        if (nextProbes != null) {
            jdbc.update("""
                    update aap_detection_config_probe
                       set deleted = true, updated_at = now(), updated_by = ?
                     where config_id = ? and deleted = false
                    """, actor, id);
            insertProbes(id, nextProbes, actor);
        }
        return detail(id);
    }

    // ------------------------------------------------------------------ ADM-CFG05

    /** ADM-CFG05 发布（`DRAFT → PUBLISHED`；旧活版置 `SUPERSEDED`；落 `CONFIG_PUBLISH` 审计）。 */
    @Transactional
    public DetectionConfig publish(AuthPrincipal principal, Long id) {
        DetectionConfig before = detail(id);
        Long actor = actorId(principal);
        int affected = jdbc.update("""
                update aap_detection_config
                   set status = 'PUBLISHED', published_at = now(), published_by = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, actor, actor, id);
        if (affected != 1) {
            throw new ApiException(ErrorCode.E_1601,
                    "只有草稿状态的检测配置可以发布（当前：" + before.status() + "）");
        }
        // 活版唯一：旧活版置 SUPERSEDED（检测任务取配置时永远只有一份 PUBLISHED）
        int superseded = jdbc.update("""
                update aap_detection_config
                   set status = 'SUPERSEDED', updated_at = now(), version = version + 1
                 where id <> ? and status = 'PUBLISHED' and deleted = false
                """, id);
        auditService.record(AuditService.AuditAction.CONFIG_PUBLISH, "detection_config", id,
                "发布检测配置 " + before.versionNo() + "（" + before.name() + "），替代旧版 "
                        + superseded + " 份");
        return detail(id);
    }

    // ------------------------------------------------------------------ 内部

    private List<Probe> probes(Long configId) {
        return jdbc.query("select " + PROBE_COLUMNS
                + " from aap_detection_config_probe where config_id = ? and deleted = false order by seq, id",
                DetectionConfigService::mapProbe, configId);
    }

    /** 校验并补全检测项：缺省名取打分组件的同名词典，缺省超时按 ER 规则。 */
    private static List<Probe> resolveProbes(List<ProbeRequest> requests) {
        if (requests == null || requests.isEmpty()) {
            return List.of();
        }
        Set<String> seen = new LinkedHashSet<>();
        List<Probe> resolved = new ArrayList<>();
        for (ProbeRequest request : requests) {
            String code = request.probeCode() == null ? null : request.probeCode().trim();
            if (code == null || !ProbeScoring.PROBE_NAMES.containsKey(code)) {
                throw ApiException.field(ErrorCode.E_1001, "probes.probe_code",
                        "非法检测项：" + request.probeCode() + "（只允许 " + ProbeScoring.PROBE_NAMES.keySet() + "）");
            }
            if (!seen.add(code)) {
                throw ApiException.field(ErrorCode.E_1001, "probes.probe_code", "检测项重复：" + code);
            }
            double weight = request.weight() == null ? 0.0 : request.weight();
            if (weight < 0 || weight > MAX_WEIGHT) {
                throw ApiException.field(ErrorCode.E_1001, "probes.weight",
                        "权重必须在 0 ~ " + MAX_WEIGHT + " 之间（归一化前的原始权重）：" + weight);
            }
            String name = request.probeName() == null || request.probeName().isBlank()
                    ? ProbeScoring.PROBE_NAMES.get(code)
                    : request.probeName().trim();
            if (name.length() > 64) {
                throw ApiException.field(ErrorCode.E_1001, "probes.probe_name", "检测项名称不得超过 64 字符");
            }
            int timeout = request.timeoutSeconds() == null
                    ? (LONG_TIMEOUT_CODES.contains(code) ? LONG_TIMEOUT_SECONDS : DEFAULT_TIMEOUT_SECONDS)
                    : request.timeoutSeconds();
            if (timeout <= 0 || timeout > 3600) {
                throw ApiException.field(ErrorCode.E_1001, "probes.timeout_seconds",
                        "超时必须在 1 ~ 3600 秒之间：" + timeout);
            }
            resolved.add(new Probe(code, name, request.enabled() == null || request.enabled(), weight, timeout,
                    request.params()));
        }
        return resolved;
    }

    private void insertProbes(Long configId, List<Probe> probes, Long actor) {
        int seq = 0;
        for (Probe probe : probes) {
            Long probeId = jdbc.queryForObject("select nextval('seq_detection_config_probe')", Long.class);
            jdbc.update("""
                    insert into aap_detection_config_probe (id, config_id, probe_code, probe_name, enabled, weight,
                        timeout_seconds, params, seq, created_at, updated_at, created_by, updated_by, deleted, version)
                    values (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, now(), now(), ?, ?, false, 0)
                    """, probeId, configId, probe.probeCode(), probe.probeName(), probe.enabled(),
                    BigDecimal.valueOf(probe.weight()), probe.timeoutSeconds(), JsonCodec.toJson(probe.params()),
                    seq++, actor, actor);
        }
    }

    private static String validateName(String name, boolean required) {
        if (name == null || name.isBlank()) {
            if (required) {
                throw ApiException.field(ErrorCode.E_1001, "name", "配置名称必填");
            }
            return null;
        }
        if (name.trim().length() > MAX_NAME_LENGTH) {
            throw ApiException.field(ErrorCode.E_1001, "name", "配置名称不得超过 " + MAX_NAME_LENGTH + " 字符");
        }
        return name.trim();
    }

    private static int validatePassScore(Integer passScore) {
        if (passScore == null) {
            return ProbeScoring.DEFAULT_PASS_SCORE;
        }
        if (passScore < 0 || passScore > 100) {
            throw ApiException.field(ErrorCode.E_1001, "pass_score", "及格分必须在 0 ~ 100 之间：" + passScore);
        }
        return passScore;
    }

    /** 否决规则形如 `{"probe":"D7","lt":40}`：只校验被引用的检测项合法，其余键原样存 jsonb。 */
    private static JsonNode validateVetoRule(JsonNode vetoRule) {
        if (vetoRule == null || vetoRule.isNull()) {
            return null;
        }
        if (!vetoRule.isObject()) {
            throw ApiException.field(ErrorCode.E_1001, "veto_rule", "否决规则必须是 JSON 对象");
        }
        JsonNode probe = vetoRule.get("probe");
        if (probe != null && !probe.isNull()) {
            String code = probe.asText();
            if (!ProbeScoring.PROBE_NAMES.containsKey(code)) {
                throw ApiException.field(ErrorCode.E_1001, "veto_rule.probe",
                        "否决规则引用了非法检测项：" + code);
            }
        }
        return vetoRule;
    }

    /**
     * `status` 只允许在草稿态出现：状态推进必须走 ADM-CFG05。
     * 否则客户端可绕过发布（无 `published_at/by`、无审计）直接把配置置为生效。
     */
    private static void validateStatus(String status, boolean creating) {
        if (status == null || status.isBlank() || "DRAFT".equalsIgnoreCase(status.trim())) {
            return;
        }
        throw ApiException.field(ErrorCode.E_1001, "status",
                (creating ? "新建" : "修改") + "检测配置的状态只能是 DRAFT，生效请调用发布接口：收到 " + status);
    }

    private static DetectionConfig map(ResultSet rs) throws SQLException {
        Long id = rs.getLong("id");
        return new DetectionConfig(
                String.valueOf(id),
                String.valueOf(id),
                rs.getString("version_no"),
                rs.getString("name"),
                rs.getInt("pass_score"),
                JsonCodec.readTree(rs.getString("veto_rule")),
                rs.getString("status"),
                new ArrayList<>(),
                rfc3339(rs.getObject("published_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("updated_at", OffsetDateTime.class)));
    }

    private static Probe mapProbe(ResultSet rs, int rowNum) throws SQLException {
        BigDecimal weight = rs.getBigDecimal("weight");
        return new Probe(
                rs.getString("probe_code"),
                rs.getString("probe_name"),
                rs.getBoolean("enabled"),
                weight == null ? null : weight.doubleValue(),
                rs.getInt("timeout_seconds"),
                JsonCodec.readTree(rs.getString("params")));
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private static Long actorId(AuthPrincipal principal) {
        return principal == null ? null : principal.accountId();
    }
}
