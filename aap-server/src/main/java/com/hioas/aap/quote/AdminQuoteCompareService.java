package com.hioas.aap.quote;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * 管理端报价历史对比（ADM-Q02；清单 §2.4「`q：quoteIds(逗号) → {items:[QuoteCompare]}`（旧值/新值/涨跌幅）」）。
 *
 * <p>口径（偏差 `D-ADM-02` 已记入 `aap-server-tdd-state.md`；清单未冻结到字段级，此处按 PRD
 * `13-管理端PRD.md` §5.3 左栏「④ 报价历史（该供应商历次报价）」+ §5.6「查看历史报价对比」落地）：
 * <ul>
 *   <li>`quoteIds` 逗号分隔，**按「旧 → 新」顺序**；比较**首单**与**末单**的当前明细价（<2 个 → 400 `E-1001`）</li>
 *   <li>`items` 以两侧 `model_name` 并集为基准、按模型名升序；同一模型按 {@link #PRICE_FIELDS} 固定字段序输出，
 *       只输出「至少一侧有值」的字段（两侧皆空不出行，避免噪声）</li>
 *   <li>单侧缺失 → 该侧 `null`、`change_rate` 也 `null`；`old_value = 0` 同样 `null`（不臆造涨跌幅、不除零）</li>
 *   <li>`change_rate` 是**百分数**（25.0000 = +25%），四位小数 `HALF_UP`；`field` 用数据字典列名</li>
 *   <li>非法 ID / 少于两个 400 `E-1001`；不存在（或已逻辑删除）的报价单 404 `E-1406`</li>
 * </ul>
 *
 * <p>为什么整段用 JdbcTemplate：这是**只读聚合**（跨报价单、跨明细行的集合运算），SQL 显式列出价字段
 * 比 ORM 实体（`QuoteItemEntity` 含规则子表、需逐行再查）更直白，也不会顺手触发 N+1 查询。
 */
@Service
public class AdminQuoteCompareService {

    private static final Logger log = LoggerFactory.getLogger(AdminQuoteCompareService.class);

    /** 参与对比的价字段（数据字典列名；按此顺序输出，保证响应可预期）。 */
    private static final List<String> PRICE_FIELDS = List.of(
            "input_price", "output_price", "cache_read_price", "cache_write_price", "cache_write_1h_price",
            "image_input_price", "audio_input_price", "image_output_price", "audio_output_price");

    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);
    private static final int RATE_SCALE = 4;

    private final JdbcTemplate jdbc;

    public AdminQuoteCompareService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** ADM-Q02 报价历史对比。 */
    public QuoteViews.CompareList compare(String quoteIds) {
        List<Long> ids = parseIds(quoteIds);
        for (Long id : ids) {
            requireQuote(id);
        }
        Long oldQuoteId = ids.get(0);
        Long newQuoteId = ids.get(ids.size() - 1);

        Map<String, Map<String, BigDecimal>> oldItems = loadItems(oldQuoteId);
        Map<String, Map<String, BigDecimal>> newItems = loadItems(newQuoteId);

        TreeSet<String> models = new TreeSet<>();
        models.addAll(oldItems.keySet());
        models.addAll(newItems.keySet());

        List<QuoteViews.Compare> rows = new ArrayList<>();
        for (String model : models) {
            Map<String, BigDecimal> oldRow = oldItems.getOrDefault(model, Map.of());
            Map<String, BigDecimal> newRow = newItems.getOrDefault(model, Map.of());
            for (String field : PRICE_FIELDS) {
                BigDecimal oldValue = oldRow.get(field);
                BigDecimal newValue = newRow.get(field);
                if (oldValue == null && newValue == null) {
                    continue;
                }
                rows.add(new QuoteViews.Compare(model, field, oldValue, newValue,
                        changeRate(oldValue, newValue)));
            }
        }
        log.info("报价历史对比 quote_ids={} → 首单={} 末单={} items={}", ids, oldQuoteId, newQuoteId, rows.size());
        return new QuoteViews.CompareList(rows);
    }

    /** 涨跌幅（百分数，四位小数）：单侧缺失或旧值为 0 一律 null（不臆造、不除零）。 */
    private static BigDecimal changeRate(BigDecimal oldValue, BigDecimal newValue) {
        if (oldValue == null || newValue == null || oldValue.compareTo(BigDecimal.ZERO) == 0) {
            return null;
        }
        return newValue.subtract(oldValue).multiply(HUNDRED)
                .divide(oldValue, RATE_SCALE, RoundingMode.HALF_UP);
    }

    /** 解析 `quoteIds`：逗号分隔、忽略空段；少于两个 → 400 `E-1001`（对比至少需要两份报价）。 */
    private static List<Long> parseIds(String quoteIds) {
        List<Long> ids = new ArrayList<>();
        if (quoteIds != null) {
            for (String token : quoteIds.split(",")) {
                String value = token.trim();
                if (value.isEmpty()) {
                    continue;
                }
                try {
                    ids.add(Long.valueOf(value));
                } catch (NumberFormatException e) {
                    throw ApiException.field(ErrorCode.E_1001, "quoteIds", "不是合法的报价单 ID：" + value);
                }
            }
        }
        if (ids.size() < 2) {
            throw ApiException.field(ErrorCode.E_1001, "quoteIds", "至少需要两个报价单 ID 才能对比");
        }
        return ids;
    }

    private void requireQuote(Long quoteId) {
        Long count = jdbc.queryForObject(
                "select count(*) from aap_quote where id = ? and deleted = false", Long.class, quoteId);
        if (count == null || count == 0) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在：" + quoteId);
        }
    }

    /** 读一份报价单的当前明细价：`model_name → (field → 价)`。 */
    private Map<String, Map<String, BigDecimal>> loadItems(Long quoteId) {
        Map<String, Map<String, BigDecimal>> items = new LinkedHashMap<>();
        List<Map<String, Object>> rows = jdbc.queryForList("select model_name, "
                + String.join(", ", PRICE_FIELDS)
                + " from aap_quote_item where quote_id = ? and deleted = false order by model_name", quoteId);
        for (Map<String, Object> row : rows) {
            Map<String, BigDecimal> prices = new LinkedHashMap<>();
            for (String field : PRICE_FIELDS) {
                prices.put(field, (BigDecimal) row.get(field));
            }
            items.put(String.valueOf(row.get("model_name")), prices);
        }
        return items;
    }
}
