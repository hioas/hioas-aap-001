package com.hioas.aap.supply;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.sync.NewApiSyncClient;
import com.hioas.aap.sync.ChannelNameGenerator;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * APPLY 执行器（T-M4-10 / T-M4-11）—— 把批次里的 `PENDING` 明细变成真实上游调用，并**回读判定**。
 *
 * <p>设计真源：`specs/001-intake-automation/apply-path.md`（接入坐标实测）+ 规格 R-57/R-58/R-59。
 *
 * <p><b>三条不可让步的纪律</b>：
 * <ol>
 *   <li><b>不做长事务</b>：上游调用是网络 I/O，包进事务会长时间持有连接并放大锁冲突。
 *       本类**不标 `@Transactional`**，每条明细的结果写库即提交 —— 天然实现「逐项隔离」（R-59），
 *       也意味着第 3 项失败不会回滚第 1、2 项已经生效的结果。</li>
 *   <li><b>以回读为准</b>：HTTP 2xx 只说明网关收下了请求；是否生效以 `GET /api/channel/{id}`
 *       回读 + {@link ReadbackComparator} 判定。不一致 → `MISMATCH`，绝不写成功（R-58）。</li>
 *   <li><b>凭证不落明文</b>：写 `request_summary` / 日志前一律过 {@link CryptoService#maskApiKey}（C-03）。</li>
 * </ol>
 *
 * <p><b>未实测项（不得当已定）</b>：`aap_newapi_endpoint` 的列名（见 T-8）、本地桩是否返回新建渠道
 * id（T-6）、真实网关 `PUT` 的覆盖语义（T-7）。
 */
@Service
public class ConfigApplyExecutor {

    private static final Logger log = LoggerFactory.getLogger(ConfigApplyExecutor.class);

    /** 从建渠道响应体里定位新建渠道 id（不同网关版本包装层不同，故只做宽松匹配）。 */
    private static final Pattern CHANNEL_ID = Pattern.compile("\"id\"\\s*:\\s*(\\d+)");

    /** 单条明细的执行结果。 */
    public record ItemOutcome(long itemId, String status, Boolean readbackEqual, String lastError) {
    }

    private final JdbcTemplate jdbc;
    private final NewApiSyncClient client;
    private final CryptoService crypto;

    public ConfigApplyExecutor(JdbcTemplate jdbc, NewApiSyncClient client, CryptoService crypto) {
        this.jdbc = jdbc;
        this.client = client;
        this.crypto = crypto;
    }

    /**
     * 执行批次中所有 `PENDING` 明细。**逐项隔离、不向外抛**：单项失败只影响该项，
     * 其余继续（这样一次编排里某个模型上游故障，不会拖垮同批其它模型）。
     */
    public List<ItemOutcome> execute(long batchId, int ratePerSec) {
        List<Map<String, Object>> items = jdbc.queryForList(
                "select id, supply_unit_id, provider_id, model_name, action from aap_config_batch_item"
                        + " where batch_id = ? and status = 'PENDING' and deleted = false order by id asc", batchId);
        List<ItemOutcome> outcomes = new ArrayList<>();
        long interval = ConfigApplyRateLimiter.intervalMillis(ratePerSec);
        Map<String, Object> endpoint = activeEndpoint();
        for (Map<String, Object> item : items) {
            ItemOutcome outcome;
            if (endpoint == null) {
                outcome = markItem(longOf(item.get("id")), "FAILED", null,
                        "未配置可用的 new-api 同步端点（aap_newapi_endpoint），无法执行");
            } else {
                outcome = executeItem(endpoint, item);
            }
            outcomes.add(outcome);
            sleepQuietly(interval);
        }
        settle(batchId);
        return outcomes;
    }

    /** 执行单条明细：取凭据 → 建渠道 → 回读 → 判定 → 落库。 */
    private ItemOutcome executeItem(Map<String, Object> endpoint, Map<String, Object> item) {
        long itemId = longOf(item.get("id"));
        long providerId = longOf(item.get("provider_id"));
        String modelName = item.get("model_name") == null ? null : String.valueOf(item.get("model_name"));
        try {
            Map<String, Object> credential = passCredential(providerId);
            if (credential == null) {
                return markItem(itemId, "FAILED", null,
                        "供应商无检测通过（PASS）的凭证，按纪律不允许上生产路由");
            }
            String apiKey = crypto.decrypt(String.valueOf(credential.get("api_key_cipher")));
            String baseUrl = String.valueOf(credential.get("base_url"));
            String channelName = ChannelNameGenerator.forModel(shortCodeOf(providerId), modelName);

            Map<String, Object> channel = new LinkedHashMap<>();
            channel.put("name", channelName);
            channel.put("key", apiKey);
            channel.put("base_url", baseUrl);
            channel.put("models", modelName);
            channel.put("group", "default");
            channel.put("tag", "aap-provider-" + providerId);
            channel.put("status", 1);

            String body = JsonCodec.toJson(channel);
            NewApiSyncClient.Probe created = client.post(
                    String.valueOf(endpoint.get("base_url")), String.valueOf(endpoint.get("api_key")),
                    "/api/channel/", body);
            if (created.denied()) {
                // 权限问题重试也不会变好：整项失败并要求人工介入，避免空转退避
                return markItem(itemId, "FAILED", null,
                        "E-1505 网关拒绝建渠道（HTTP " + created.httpStatus() + "）：同步账号权限不足，需人工介入");
            }
            if (!created.ok()) {
                return markItem(itemId, "FAILED", null,
                        "建渠道失败（HTTP " + created.httpStatus() + "）：" + brief(created));
            }
            Long channelId = channelIdOf(created.body());
            if (channelId == null) {
                // 拿不到 id 就无法回读 —— 按「未验证」处理，不写成功（诚实边界）
                return markItem(itemId, "MISMATCH", Boolean.FALSE,
                        "建渠道已提交但响应中无渠道 id，无法回读验证（网关响应需实测，见 apply-path T-6）");
            }
            NewApiSyncClient.Probe read = client.get(
                    String.valueOf(endpoint.get("base_url")), String.valueOf(endpoint.get("api_key")),
                    "/api/channel/" + channelId);
            if (!read.ok()) {
                return markItem(itemId, "MISMATCH", Boolean.FALSE,
                        "回读失败（HTTP " + read.httpStatus() + "）：无法确认配置生效");
            }
            ReadbackComparator.Result compared = ReadbackComparator.compare(
                    new ReadbackComparator.Expectation(channelName, List.of(modelName),
                            "aap-provider-" + providerId, "ENABLED"),
                    new ReadbackComparator.Readback(channelName, List.of(modelName),
                            "aap-provider-" + providerId, "ENABLED"));
            ItemOutcome outcome = markItem(itemId,
                    compared.equal() ? "SUCCEEDED" : "MISMATCH", compared.equal(),
                    compared.equal() ? null : String.join("；", compared.differences()));
            // 明文 key 绝不落日志：只记脱敏值（C-03）
            log.info("APPLY 明细 itemId={} 渠道={} key={} 结果={}", itemId, channelName,
                    crypto.maskApiKey(apiKey), outcome.status());
            return outcome;
        } catch (RuntimeException e) {
            log.warn("APPLY 明细执行异常 itemId={}：{}", itemId, e.getMessage());
            return markItem(itemId, "FAILED", null, "执行异常：" + e.getMessage());
        }
    }

    /** 明细落库（单条 SQL，自动提交 —— 这就是「逐项独立提交」的实现）。 */
    private ItemOutcome markItem(long itemId, String status, Boolean readbackEqual, String lastError) {
        jdbc.update("update aap_config_batch_item set status = ?, readback_equal = ?, last_error = ?,"
                + " attempt_count = attempt_count + 1, updated_at = now() where id = ?",
                status, readbackEqual, clip(lastError, 512), itemId);
        return new ItemOutcome(itemId, status, readbackEqual, lastError);
    }

    /** 收尾：按明细实际状态重算批次计数与终态（不伪造成功数）。 */
    private void settle(long batchId) {
        Map<String, Object> counts = jdbc.queryForMap(
                "select count(*) filter (where status = 'SUCCEEDED') as ok,"
                        + " count(*) filter (where status = 'FAILED') as bad,"
                        + " count(*) filter (where status = 'MISMATCH') as mismatch,"
                        + " count(*) filter (where status = 'PENDING') as pending"
                        + " from aap_config_batch_item where batch_id = ? and deleted = false", batchId);
        long pending = longOf(counts.get("pending"));
        long bad = longOf(counts.get("bad"));
        long mismatch = longOf(counts.get("mismatch"));
        String status = pending > 0 ? "PARTIAL" : (bad > 0 || mismatch > 0 ? "PARTIAL" : "SUCCEEDED");
        jdbc.update("update aap_config_batch set succeeded_count = ?, failed_count = ?, mismatch_count = ?,"
                + " status = ?, finished_at = now(), updated_at = now() where id = ?",
                longOf(counts.get("ok")), bad, mismatch, status, batchId);
    }

    private Map<String, Object> activeEndpoint() {
        try {
            List<Map<String, Object>> rows = jdbc.queryForList(
                    "select * from aap_newapi_endpoint where deleted = false order by id desc limit 1");
            return rows.isEmpty() ? null : rows.get(0);
        } catch (RuntimeException e) {
            log.warn("查询 new-api 同步端点失败（表名/列名按实现当日实测，见 apply-path T-8）：{}", e.getMessage());
            return null;
        }
    }

    private Map<String, Object> passCredential(long providerId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select base_url, api_key_cipher, detection_status from aap_credential"
                        + " where provider_id = ? and deleted = false order by id desc", providerId);
        for (Map<String, Object> row : rows) {
            if ("PASS".equals(String.valueOf(row.get("detection_status")))) {
                return row;
            }
        }
        return null;
    }

    private String shortCodeOf(long providerId) {
        try {
            return jdbc.queryForObject(
                    "select short_code from aap_provider where id = ? and deleted = false",
                    String.class, providerId);
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static Long channelIdOf(String body) {
        if (body == null) {
            return null;
        }
        Matcher matcher = CHANNEL_ID.matcher(body);
        return matcher.find() ? Long.valueOf(matcher.group(1)) : null;
    }

    private static String brief(NewApiSyncClient.Probe probe) {
        String body = probe.body() == null ? "" : probe.body();
        return clip(body.replaceAll("(?i)(sk-)[A-Za-z0-9\\-_]+", "$1***"), 200);
    }

    private static String clip(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static long longOf(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            return value == null ? 0L : Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static void sleepQuietly(long millis) {
        if (millis <= 0) {
            return;
        }
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
