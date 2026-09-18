package com.hioas.aap.usage;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.usage.UsageMetrics.ModelTokens;
import com.hioas.aap.usage.UsageMetrics.QuotedPrice;
import com.hioas.aap.usage.UsageViews.Bucket;
import com.hioas.aap.usage.UsageViews.Cost;
import com.hioas.aap.usage.UsageViews.Daily;
import com.hioas.aap.usage.UsageViews.Model;
import com.hioas.aap.usage.UsageViews.RefreshResult;
import com.hioas.aap.usage.UsageViews.Summary;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;

/**
 * 用量聚合与对账（USE-01/02、ADM-U01/02；AC-43…46）。
 *
 * <p>数据真源：`aap_usage_hourly`（小时桶，`UQ(stat_hour, channel_id, model_name, group_name)`），
 * 对账指标口径见 `11-同步与用量统计PRD` §4。
 *
 * <p>三个刻意的设计取舍：
 * <ol>
 *   <li>**不用 ORM 跑聚合**：这里全是 GROUP BY / jsonb 展开 / UPSERT，用 {@link JdbcTemplate} 写显式 SQL
 *       比 QueryWrapper 更可读、更贴数据库（同 {@code DocNoGenerator} 的取舍）。</li>
 *   <li>**窗口一律半开 `[from, to)`**（清单 §0 通用约定），`month=YYYY-MM` 模式即当月整月。</li>
 *   <li>**无数据不用 0 冒充**：窗口内没有桶时所有指标回 null（前端占位符），只有桶存在才求真实和。</li>
 * </ol>
 *
 * <p>已知限制（见 tdd-state R12）：`channel_id` 为 null 的桶在 PostgreSQL 唯一索引下**不互相冲突**
 * （NULL 视为互不相同）→ 重跑这类桶会新增行而不是 UPSERT。渠道未映射（U5）应尽早补齐 channel_id。
 */
@Service
public class UsageService {

    private static final Logger log = LoggerFactory.getLogger(UsageService.class);

    private static final DateTimeFormatter RFC3339 =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");
    private static final Pattern MONTH_PATTERN = Pattern.compile("^(\\d{4})-(\\d{1,2})$");

    /** 聚合批次游标的数据源标识（`aap_usage_sync_cursor.data_source`）。 */
    private static final String CURSOR_LOG_API = "LOG_API";

    private final JdbcTemplate jdbc;
    private final Environment environment;

    public UsageService(JdbcTemplate jdbc, Environment environment) {
        this.jdbc = jdbc;
        this.environment = environment;
    }

    // ------------------------------------------------------------------ USE-01

    /** 供应商用量概览（超集响应）。 */
    public Summary summary(Long providerId, String startHour, String endHour, String month) {
        Window window = resolveWindow(startHour, endHour, month);
        Span span = statSpan(providerId, window.from(), window.to());
        String refreshedAt = rfc3339(OffsetDateTime.now(ZoneOffset.UTC));

        if (span.bucketCount() == 0) {
            // 无数据 → 指标全 null（禁止用 0 冒充）；窗口与 provider_id 必备
            return new Summary(String.valueOf(providerId), rfc3339(window.from()), rfc3339(window.to()),
                    window.month(), null, null, null, null, null, null, null, null, null, null, null, null,
                    null, null, null, null, null, null, null, null, Map.of(), List.of(), List.of(), null,
                    null, refreshedAt, false);
        }

        List<ModelAgg> modelAggs = modelAggs(providerId, window);
        List<Model> models = models(modelAggs);
        List<Daily> daily = daily(providerId, window);
        Map<String, BigDecimal> tierDistribution = tierDistribution(providerId, window);

        BigDecimal amountTotal = UsageMetrics.scale6(span.costUsd());
        BigDecimal actualUnitPrice = UsageMetrics.actualUnitPrice(span.costUsd(), span.totalTokens());
        BigDecimal platformFeeRate = platformFeeRate(providerId);
        BigDecimal platformFee = platformFeeRate == null || amountTotal == null ? null
                : UsageMetrics.scale6(platformFeeRate.multiply(amountTotal));

        Double deviationRate = UsageMetrics.deviationRate(actualUnitPrice,
                UsageMetrics.quotedWeightedUnitPrice(modelAggs.stream().map(ModelAgg::toTokens).toList(),
                        quotedPrices(providerId), span.totalTokens()));

        Span previous = statSpan(providerId, window.previousFrom(), window.from());
        BigDecimal previousCost = previous.bucketCount() == 0 ? null : previous.costUsd();

        Double cacheParseRate = UsageMetrics.cacheParseRate(span.okBuckets(), span.bucketCount());

        return new Summary(
                String.valueOf(providerId), rfc3339(window.from()), rfc3339(window.to()), window.month(),
                span.requestCount(), span.promptTokens(), span.completionTokens(), span.totalTokens(),
                span.cacheReadTokens(), span.cacheWriteTokens(), span.cacheWrite1hTokens(),
                span.imageInputTokens(), span.audioInputTokens(), span.videoInputTokens(),
                UsageMetrics.cacheHitRate(span.cacheReadTokens(), span.promptTokens()), cacheParseRate,
                UsageMetrics.scale6(span.quotaRaw()), UsageMetrics.scale6(span.costUsd()), amountTotal,
                amountTotal, UsageMetrics.momRate(span.costUsd(), previousCost),
                UsageMetrics.momSavedAmount(span.costUsd(), previousCost), actualUnitPrice, deviationRate,
                tierDistribution, models, daily,
                new Cost(null, null, platformFee, platformFeeRate, amountTotal),
                span.updatedAt() == null ? null : rfc3339(span.updatedAt()), refreshedAt,
                cacheParseRate != null && cacheParseRate < 1);
    }

    // ------------------------------------------------------------------ USE-02 / ADM-U01

    /** 分时用量分页（`providerId == null` = 管理端全量）。 */
    public PageResult<Bucket> hourly(Long providerId, Long channelId, String fromRaw, String toRaw,
                                     String model, String group, int page, int pageSize) {
        OffsetDateTime from = parseInstant(fromRaw, "from");
        OffsetDateTime to = parseInstant(toRaw, "to");
        if (!from.isBefore(to)) {
            throw new ApiException(ErrorCode.E_1001, "from 必须早于 to（半开区间 [from, to)）");
        }
        List<Object> filter = new ArrayList<>();
        StringBuilder where = new StringBuilder(" where deleted = false and stat_hour >= ? and stat_hour < ?");
        filter.add(from);
        filter.add(to);
        if (providerId != null) {
            where.append(" and provider_id = ?");
            filter.add(providerId);
        }
        if (channelId != null) {
            where.append(" and channel_id = ?");
            filter.add(channelId);
        }
        if (model != null && !model.isBlank()) {
            where.append(" and model_name = ?");
            filter.add(model);
        }
        if (group != null && !group.isBlank()) {
            where.append(" and group_name = ?");
            filter.add(group);
        }

        Long total = jdbc.queryForObject("select count(*) from aap_usage_hourly" + where, Long.class,
                filter.toArray());
        List<Object> pageArgs = new ArrayList<>(filter);
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Bucket> items = jdbc.query(
                "select * from aap_usage_hourly" + where + " order by stat_hour, model_name, group_name"
                        + " limit ? offset ?",
                (rs, rowNum) -> new Bucket(
                        rfc3339(rs.getObject("stat_hour", OffsetDateTime.class)),
                        idText(rs.getObject("channel_id", Long.class)),
                        rs.getString("channel_name"),
                        idText(rs.getObject("provider_id", Long.class)),
                        rs.getString("model_name"), rs.getString("group_name"),
                        rs.getObject("request_count", Long.class), rs.getObject("prompt_tokens", Long.class),
                        rs.getObject("completion_tokens", Long.class), rs.getObject("total_tokens", Long.class),
                        rs.getObject("cache_read_tokens", Long.class),
                        rs.getObject("cache_write_tokens", Long.class),
                        rs.getObject("cache_write_1h_tokens", Long.class),
                        rs.getObject("image_input_tokens", Long.class),
                        rs.getObject("audio_input_tokens", Long.class),
                        rs.getObject("video_input_tokens", Long.class),
                        rs.getBigDecimal("quota_raw"), rs.getBigDecimal("cost_usd"),
                        rs.getString("cache_parse_status"), rs.getString("source"),
                        JsonCodec.toMap(rs.getString("tier_distribution")),
                        rfc3339(rs.getObject("collected_at", OffsetDateTime.class))),
                pageArgs.toArray());
        return PageResult.of(items, page, pageSize, total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ ADM-U02

    /**
     * 从日志源拉取小时桶并 UPSERT 落库（AC-43/44/45）。
     *
     * <p>幂等键 = 表唯一键 `(stat_hour, channel_id, model_name, group_name)`：同窗口重跑
     * 不新增行、只更新（AC-44）。
     *
     * <p>窗口缺省 = 最近一个**已结束**的整点小时 `[floor(now)-1h, floor(now))`——
     * 不做「拉当前小时」（数据还在写入，重跑会得到不同结果，破坏幂等的可验证性）。
     */
    @Transactional
    public RefreshResult refresh(String fromRaw, String toRaw) {
        OffsetDateTime from;
        OffsetDateTime to;
        if ((fromRaw == null || fromRaw.isBlank()) && (toRaw == null || toRaw.isBlank())) {
            to = OffsetDateTime.now(ZoneOffset.UTC).truncatedTo(ChronoUnit.HOURS);
            from = to.minusHours(1);
        } else {
            from = parseInstant(fromRaw, "from");
            to = parseInstant(toRaw, "to");
            if (!from.isBefore(to)) {
                throw new ApiException(ErrorCode.E_1001, "from 必须早于 to（半开区间 [from, to)）");
            }
        }
        List<SourceBucket> buckets = readLogSource(from, to);
        long batchId = jdbc.queryForObject("select nextval('seq_usage_batch')", Long.class);

        int inserted = 0;
        int updated = 0;
        boolean allCacheParsed = true;
        for (SourceBucket bucket : buckets) {
            Long existing = jdbc.queryForObject("""
                    select count(*) from aap_usage_hourly
                     where stat_hour = ? and channel_id is not distinct from cast(? as bigint)
                       and model_name = ? and group_name = ? and deleted = false
                    """, Long.class, bucket.statHour(), bucket.channelId(), bucket.modelName(), bucket.groupName());
            if (existing == null || existing == 0) {
                inserted++;
            } else {
                updated++;
            }
            upsert(bucket, batchId);
            allCacheParsed = allCacheParsed && !"NO_CACHE_FIELD".equals(bucket.cacheParseStatus());
        }

        String batchStatus = buckets.isEmpty() ? null : (allCacheParsed ? "OK" : "NO_CACHE_FIELD");
        touchCursor(from, to, batchId, batchStatus == null ? "OK" : batchStatus);
        log.info("用量聚合批次 batch_id={} 窗口=[{}, {}) 新增={} 更新={} 缓存解析={}",
                batchId, from, to, inserted, updated, batchStatus);
        return new RefreshResult(String.valueOf(batchId), inserted, updated, buckets.size(), batchStatus,
                rfc3339(from), rfc3339(to));
    }

    private void upsert(SourceBucket bucket, long batchId) {
        jdbc.update("""
                insert into aap_usage_hourly (id, stat_hour, channel_id, channel_name, provider_id, model_name,
                    group_name, request_count, prompt_tokens, completion_tokens, total_tokens, cache_read_tokens,
                    cache_write_tokens, cache_write_1h_tokens, image_input_tokens, audio_input_tokens,
                    video_input_tokens, quota_raw, cost_usd, tier_distribution, cache_parse_status, source,
                    batch_id, collected_at)
                values (nextval('seq_usage_hourly'), cast(? as timestamptz), cast(? as bigint), ?,
                        cast(? as bigint), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, cast(? as numeric),
                        cast(? as numeric), cast(? as jsonb), ?, ?, ?, cast(? as timestamptz))
                on conflict (stat_hour, channel_id, model_name, group_name) do update set
                    channel_name = excluded.channel_name, provider_id = excluded.provider_id,
                    request_count = excluded.request_count, prompt_tokens = excluded.prompt_tokens,
                    completion_tokens = excluded.completion_tokens, total_tokens = excluded.total_tokens,
                    cache_read_tokens = excluded.cache_read_tokens,
                    cache_write_tokens = excluded.cache_write_tokens,
                    cache_write_1h_tokens = excluded.cache_write_1h_tokens,
                    image_input_tokens = excluded.image_input_tokens,
                    audio_input_tokens = excluded.audio_input_tokens,
                    video_input_tokens = excluded.video_input_tokens, quota_raw = excluded.quota_raw,
                    cost_usd = excluded.cost_usd, tier_distribution = excluded.tier_distribution,
                    cache_parse_status = excluded.cache_parse_status, source = excluded.source,
                    batch_id = excluded.batch_id, collected_at = excluded.collected_at,
                    updated_at = now(), version = aap_usage_hourly.version + 1
                """,
                rfc3339(bucket.statHour()), bucket.channelId(), bucket.channelName(), bucket.providerId(),
                bucket.modelName(), bucket.groupName(), bucket.requestCount(), bucket.promptTokens(),
                bucket.completionTokens(), bucket.totalTokens(), bucket.cacheReadTokens(),
                bucket.cacheWriteTokens(), bucket.cacheWrite1hTokens(), bucket.imageInputTokens(),
                bucket.audioInputTokens(), bucket.videoInputTokens(), bucket.quotaRaw(), bucket.costUsd(),
                bucket.tierDistribution(), bucket.cacheParseStatus(), bucket.source(),
                batchId, rfc3339(bucket.collectedAt()));
    }

    private void touchCursor(OffsetDateTime from, OffsetDateTime to, long batchId, String status) {
        int rows = jdbc.update("""
                update aap_usage_sync_cursor
                   set cursor_hour = ?, last_run_at = now(), last_batch_id = ?, status = ?,
                       updated_at = now(), version = version + 1
                 where data_source = ? and deleted = false
                """, to, batchId, status, CURSOR_LOG_API);
        if (rows == 0) {
            jdbc.update("""
                    insert into aap_usage_sync_cursor (id, data_source, cursor_hour, last_run_at, last_batch_id, status)
                    values (nextval('seq_usage_batch'), ?, ?, now(), ?, ?)
                    """, CURSOR_LOG_API, to, batchId, status);
        }
        log.debug("用量游标更新 data_source={} 窗口起点={} 批次={}", CURSOR_LOG_API, from, batchId);
    }

    /**
     * 读取日志源（本项目 **mock 适配器**：`app.usage.log-file` 指向的 JSON 文件，形状
     * `{"buckets":[{stat_hour,channel_id,model_name,…,cache_parse_status}]}`）。
     *
     * <p>真实 new-api Log 表拉取未接入（无冻结契约）→ 未配置/不可读/格式非法一律回 E-1801，
     * 既不静默返回空结果（会把「源故障」显示成「零用量」），也不臆造上游字段语义。
     */
    private List<SourceBucket> readLogSource(OffsetDateTime from, OffsetDateTime to) {
        String location = environment.getProperty("app.usage.log-file", "");
        if (location == null || location.isBlank()) {
            throw new ApiException(ErrorCode.E_1801, "用量日志源未配置（app.usage.log-file），无法聚合");
        }
        String text;
        try {
            text = Files.readString(Path.of(location.trim()), StandardCharsets.UTF_8);
        } catch (IOException | RuntimeException e) {
            throw new ApiException(ErrorCode.E_1801, "用量日志源不可读（文件缺失或权限不足）");
        }
        JsonNode root;
        try {
            root = JsonCodec.fromJson(text, JsonNode.class);
        } catch (RuntimeException e) {
            throw new ApiException(ErrorCode.E_1801, "用量日志源格式非法（无法解析为 JSON）");
        }
        List<SourceBucket> buckets = new ArrayList<>();
        if (root == null || !root.path("buckets").isArray()) {
            throw new ApiException(ErrorCode.E_1801, "用量日志源缺少 buckets 数组");
        }
        for (JsonNode node : root.path("buckets")) {
            String statHourText = text(node, "stat_hour");
            if (statHourText == null || statHourText.isBlank()) {
                throw new ApiException(ErrorCode.E_1801, "用量日志源记录缺少 stat_hour");
            }
            OffsetDateTime statHour = parseSourceInstant(statHourText, "stat_hour");
            if (statHour.isBefore(from) || !statHour.isBefore(to)) {
                continue;   // 只聚合请求窗口内的桶（源文件可能含更宽的范围）
            }
            boolean cacheFieldsPresent = node.hasNonNull("cache_read_tokens") || node.hasNonNull("cache_write_tokens");
            String declaredStatus = text(node, "cache_parse_status");
            String declaredSource = text(node, "source");
            String collectedAtText = text(node, "collected_at");
            buckets.add(new SourceBucket(
                    statHour,
                    longOrNull(node, "channel_id"),
                    text(node, "channel_name"),
                    longOrNull(node, "provider_id"),
                    orEmpty(text(node, "model_name")),
                    orEmpty(text(node, "group_name")),
                    longOrZero(node, "request_count"),
                    longOrZero(node, "prompt_tokens"),
                    longOrZero(node, "completion_tokens"),
                    longOrZero(node, "total_tokens"),
                    longOrZero(node, "cache_read_tokens"),
                    longOrZero(node, "cache_write_tokens"),
                    longOrZero(node, "cache_write_1h_tokens"),
                    longOrZero(node, "image_input_tokens"),
                    longOrZero(node, "audio_input_tokens"),
                    longOrZero(node, "video_input_tokens"),
                    decimalOrZero(node, "quota_raw"),
                    decimalOrZero(node, "cost_usd"),
                    node.hasNonNull("tier_distribution") ? node.get("tier_distribution").toString() : null,
                    // U2/AC-45：源里没有缓存字段 → NO_CACHE_FIELD（记 0，不臆造数值）；有则 OK
                    declaredStatus == null || declaredStatus.isBlank()
                            ? (cacheFieldsPresent ? "OK" : "NO_CACHE_FIELD") : declaredStatus,
                    declaredSource == null || declaredSource.isBlank() ? "LOG_API" : declaredSource,
                    collectedAtText == null || collectedAtText.isBlank()
                            ? statHour : parseSourceInstant(collectedAtText, "collected_at")));
        }
        return buckets;
    }

    /** 日志源里的时间戳解析失败属**源故障**（E-1801），不是请求参数错误（E-1001）。 */
    private static OffsetDateTime parseSourceInstant(String value, String field) {
        try {
            return OffsetDateTime.parse(value.trim()).withOffsetSameInstant(ZoneOffset.UTC);
        } catch (RuntimeException e) {
            throw new ApiException(ErrorCode.E_1801, "用量日志源的 " + field + " 不是合法 RFC3339 时间");
        }
    }

    // ------------------------------------------------------------------ 聚合查询

    private record Window(OffsetDateTime from, OffsetDateTime to, String month) {
        OffsetDateTime previousFrom() {
            return from.minusSeconds(java.time.Duration.between(from, to).getSeconds());
        }
    }

    /** 窗口内求和结果（bucketCount = 0 表示窗口无数据）。 */
    private record Span(long bucketCount, long okBuckets, Long requestCount, Long promptTokens,
                        Long completionTokens, Long totalTokens, Long cacheReadTokens, Long cacheWriteTokens,
                        Long cacheWrite1hTokens, Long imageInputTokens, Long audioInputTokens,
                        Long videoInputTokens, BigDecimal quotaRaw, BigDecimal costUsd,
                        OffsetDateTime updatedAt) {
    }

    private Span statSpan(Long providerId, OffsetDateTime from, OffsetDateTime to) {
        // ★ sum(bigint) 在 PostgreSQL 里返回 numeric（不是 bigint）→ 必须显式 ::bigint，
        //   否则 rs.getObject(..., Long.class) 抛「conversion to class java.lang.Long from numeric」。
        return jdbc.queryForObject("""
                select count(*) as bucket_count,
                       count(*) filter (where cache_parse_status = 'OK') as ok_buckets,
                       coalesce(sum(request_count), 0)::bigint as request_count,
                       coalesce(sum(prompt_tokens), 0)::bigint as prompt_tokens,
                       coalesce(sum(completion_tokens), 0)::bigint as completion_tokens,
                       coalesce(sum(total_tokens), 0)::bigint as total_tokens,
                       coalesce(sum(cache_read_tokens), 0)::bigint as cache_read_tokens,
                       coalesce(sum(cache_write_tokens), 0)::bigint as cache_write_tokens,
                       coalesce(sum(cache_write_1h_tokens), 0)::bigint as cache_write_1h_tokens,
                       coalesce(sum(image_input_tokens), 0)::bigint as image_input_tokens,
                       coalesce(sum(audio_input_tokens), 0)::bigint as audio_input_tokens,
                       coalesce(sum(video_input_tokens), 0)::bigint as video_input_tokens,
                       coalesce(sum(quota_raw), 0) as quota_raw,
                       coalesce(sum(cost_usd), 0) as cost_usd,
                       max(collected_at) as updated_at
                  from aap_usage_hourly
                 where deleted = false and provider_id = ? and stat_hour >= ? and stat_hour < ?
                """, (rs, rowNum) -> new Span(
                        rs.getLong("bucket_count"), rs.getLong("ok_buckets"),
                        rs.getObject("request_count", Long.class), rs.getObject("prompt_tokens", Long.class),
                        rs.getObject("completion_tokens", Long.class), rs.getObject("total_tokens", Long.class),
                        rs.getObject("cache_read_tokens", Long.class),
                        rs.getObject("cache_write_tokens", Long.class),
                        rs.getObject("cache_write_1h_tokens", Long.class),
                        rs.getObject("image_input_tokens", Long.class),
                        rs.getObject("audio_input_tokens", Long.class),
                        rs.getObject("video_input_tokens", Long.class),
                        rs.getBigDecimal("quota_raw"), rs.getBigDecimal("cost_usd"),
                        rs.getObject("updated_at", OffsetDateTime.class)),
                providerId, from, to);
    }

    private List<Model> models(List<ModelAgg> modelAggs) {
        List<Model> models = modelAggs.stream()
                .map(agg -> new Model(agg.modelName(), agg.requestCount(), agg.totalTokens(),
                        UsageMetrics.scale6(agg.amount()), null, null))
                .toList();
        BigDecimal total = modelAggs.stream().map(ModelAgg::amount).filter(java.util.Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        List<Model> withShare = new ArrayList<>(models.size());
        for (Model model : models) {
            BigDecimal share = total.signum() == 0 || model.amount() == null ? null
                    : model.amount().divide(total, 6, RoundingMode.HALF_UP);
            withShare.add(new Model(model.modelName(), model.requestCount(), model.totalTokens(), model.amount(),
                    share, share == null ? null : share.multiply(BigDecimal.valueOf(100))
                            .setScale(2, RoundingMode.HALF_UP)));
        }
        return withShare;
    }

    /** 单模型聚合（含词元结构，供报价加权单价使用）。 */
    private record ModelAgg(String modelName, long requestCount, long promptTokens, long completionTokens,
                            long cacheReadTokens, long totalTokens, BigDecimal amount) {

        ModelTokens toTokens() {
            return new ModelTokens(modelName, promptTokens, completionTokens, cacheReadTokens, totalTokens);
        }
    }

    private List<ModelAgg> modelAggs(Long providerId, Window window) {
        return jdbc.query("""
                select model_name,
                       coalesce(sum(request_count), 0)::bigint as request_count,
                       coalesce(sum(prompt_tokens), 0)::bigint as prompt_tokens,
                       coalesce(sum(completion_tokens), 0)::bigint as completion_tokens,
                       coalesce(sum(cache_read_tokens), 0)::bigint as cache_read_tokens,
                       coalesce(sum(total_tokens), 0)::bigint as total_tokens,
                       coalesce(sum(cost_usd), 0) as amount
                  from aap_usage_hourly
                 where deleted = false and provider_id = ? and stat_hour >= ? and stat_hour < ?
                 group by model_name
                 order by amount desc, model_name
                """, (rs, rowNum) -> new ModelAgg(rs.getString("model_name"),
                rs.getLong("request_count"), rs.getLong("prompt_tokens"), rs.getLong("completion_tokens"),
                rs.getLong("cache_read_tokens"), rs.getLong("total_tokens"), rs.getBigDecimal("amount")),
                providerId, window.from(), window.to());
    }

    private List<Daily> daily(Long providerId, Window window) {
        return jdbc.query("""
                select to_char(stat_hour at time zone 'UTC', 'YYYY-MM-DD') as stat_date,
                       coalesce(sum(request_count), 0)::bigint as request_count,
                       coalesce(sum(total_tokens), 0)::bigint as total_tokens,
                       coalesce(sum(cost_usd), 0) as amount
                  from aap_usage_hourly
                 where deleted = false and provider_id = ? and stat_hour >= ? and stat_hour < ?
                 group by 1
                 order by 1
                """, (rs, rowNum) -> {
            String date = rs.getString("stat_date");
            Long tokens = rs.getObject("total_tokens", Long.class);
            return new Daily(date, date, date, rs.getObject("request_count", Long.class), tokens, tokens,
                    UsageMetrics.scale6(rs.getBigDecimal("amount")));
        }, providerId, window.from(), window.to());
    }

    private Map<String, BigDecimal> tierDistribution(Long providerId, Window window) {
        Map<String, BigDecimal> tiers = new LinkedHashMap<>();
        jdbc.query("""
                select t.key as tier_key, sum(t.value::numeric) as tier_total
                  from aap_usage_hourly u
                  cross join lateral jsonb_each_text(u.tier_distribution) as t(key, value)
                 where u.deleted = false and u.provider_id = ? and u.stat_hour >= ? and u.stat_hour < ?
                 group by t.key
                 order by t.key
                """, rs -> {
            tiers.put(rs.getString("tier_key"), rs.getBigDecimal("tier_total"));
        }, providerId, window.from(), window.to());
        return tiers;
    }

    /** 报价基准：该供应商**最近**一条 APPROVED 报价单里各模型的单价（USD/1M）。 */
    private Map<String, QuotedPrice> quotedPrices(Long providerId) {
        Map<String, QuotedPrice> prices = new LinkedHashMap<>();
        jdbc.query("""
                select distinct on (i.model_name) i.model_name, i.input_price, i.output_price, i.cache_read_price
                  from aap_quote_item i
                  join aap_quote q on q.id = i.quote_id
                 where q.provider_id = ? and q.status = 'APPROVED' and q.deleted = false and i.deleted = false
                 order by i.model_name, q.id desc
                """, rs -> {
            prices.put(rs.getString("model_name"), new QuotedPrice(rs.getBigDecimal("input_price"),
                    rs.getBigDecimal("output_price"), rs.getBigDecimal("cache_read_price")));
        }, providerId);
        return prices;
    }

    /** 平台服务费率：已签署合同（`aap_contract.status = SIGNED`）的最新费率；无合同 → null。 */
    private BigDecimal platformFeeRate(Long providerId) {
        List<BigDecimal> rates = jdbc.queryForList("""
                select platform_fee_rate from aap_contract
                 where provider_id = ? and status = 'SIGNED' and deleted = false
                 order by valid_from desc nulls last, id desc
                 limit 1
                """, BigDecimal.class, providerId);
        return rates.isEmpty() ? null : rates.get(0);
    }

    // ------------------------------------------------------------------ 窗口与格式

    private Window resolveWindow(String startHour, String endHour, String month) {
        boolean hasStart = startHour != null && !startHour.isBlank();
        boolean hasEnd = endHour != null && !endHour.isBlank();
        if (month != null && !month.isBlank()) {
            YearMonth yearMonth = parseMonth(month);
            return new Window(yearMonth.atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC),
                    yearMonth.plusMonths(1).atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC), yearMonth.toString());
        }
        if (hasStart || hasEnd) {
            if (!hasStart || !hasEnd) {
                throw new ApiException(ErrorCode.E_1001, "startHour 与 endHour 必须成对出现（半开区间 [from, to)）");
            }
            OffsetDateTime from = parseInstant(startHour, "startHour");
            OffsetDateTime to = parseInstant(endHour, "endHour");
            if (!from.isBefore(to)) {
                throw new ApiException(ErrorCode.E_1001, "startHour 必须早于 endHour（半开区间）");
            }
            return new Window(from, to, null);
        }
        LocalDate firstOfMonth = LocalDate.now(ZoneOffset.UTC).withDayOfMonth(1);
        return new Window(firstOfMonth.atStartOfDay().atOffset(ZoneOffset.UTC),
                firstOfMonth.plusMonths(1).atStartOfDay().atOffset(ZoneOffset.UTC),
                YearMonth.from(firstOfMonth).toString());
    }

    private static YearMonth parseMonth(String month) {
        Matcher matcher = MONTH_PATTERN.matcher(month.trim());
        if (!matcher.matches()) {
            throw new ApiException(ErrorCode.E_1001, "month 格式非法（应为 YYYY-MM）");
        }
        int value = Integer.parseInt(matcher.group(2));
        if (value < 1 || value > 12) {
            throw new ApiException(ErrorCode.E_1001, "month 月份超出 1–12");
        }
        return YearMonth.of(Integer.parseInt(matcher.group(1)), value);
    }

    private static OffsetDateTime parseInstant(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new ApiException(ErrorCode.E_1001, field + " 缺失（RFC3339 UTC）");
        }
        try {
            return OffsetDateTime.parse(value.trim()).withOffsetSameInstant(ZoneOffset.UTC);
        } catch (RuntimeException e) {
            throw new ApiException(ErrorCode.E_1001, field + " 不是合法的 RFC3339 时间");
        }
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private static String idText(Long value) {
        return value == null ? null : String.valueOf(value);
    }

    private static String orEmpty(String value) {
        return value == null ? "" : value;
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private static Long longOrNull(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asLong();
    }

    private static long longOrZero(JsonNode node, String field) {
        Long value = longOrNull(node, field);
        return value == null ? 0L : value;
    }

    private static BigDecimal decimalOrZero(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? BigDecimal.ZERO : value.decimalValue();
    }

    /** 日志源里的一条小时桶原始记录。 */
    private record SourceBucket(OffsetDateTime statHour, Long channelId, String channelName, Long providerId,
                                String modelName, String groupName, long requestCount, long promptTokens,
                                long completionTokens, long totalTokens, long cacheReadTokens,
                                long cacheWriteTokens, long cacheWrite1hTokens, long imageInputTokens,
                                long audioInputTokens, long videoInputTokens, BigDecimal quotaRaw,
                                BigDecimal costUsd, String tierDistribution, String cacheParseStatus,
                                String source, OffsetDateTime collectedAt) {
    }
}
