package com.hioas.aap.compile;

import com.hioas.aap.quote.PriceRequestRuleMapper;
import com.hioas.aap.quote.PriceTierEntity;
import com.hioas.aap.quote.PriceTierMapper;
import com.hioas.aap.quote.PriceTierRuleEntity;
import com.hioas.aap.quote.PriceTierRuleMapper;
import com.hioas.aap.quote.PriceTimeRuleEntity;
import com.hioas.aap.quote.PriceTimeRuleMapper;
import com.hioas.aap.quote.PriceTimeSegmentEntity;
import com.hioas.aap.quote.PriceTimeSegmentMapper;
import com.hioas.aap.quote.QuoteItemEntity;
import com.hioas.aap.quote.QuoteItemMapper;
import com.hioas.aap.quote.QuoteValidation;
import com.mybatisflex.core.query.QueryWrapper;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * 编译输入装配：把报价单的明细行与三类规则读成 {@link BillingCompiler.ItemRules}。
 *
 * <p>放在 `compile` 包而不是 `quote` 包：依赖方向单向 `compile → quote`，避免两个包互相 import。
 */
@Component
public class CompileInputLoader {

    private final QuoteItemMapper itemMapper;
    private final PriceTimeRuleMapper timeRuleMapper;
    private final PriceTimeSegmentMapper segmentMapper;
    private final PriceTierRuleMapper tierRuleMapper;
    private final PriceTierMapper tierMapper;
    private final PriceRequestRuleMapper requestRuleMapper;

    public CompileInputLoader(QuoteItemMapper itemMapper, PriceTimeRuleMapper timeRuleMapper,
                              PriceTimeSegmentMapper segmentMapper, PriceTierRuleMapper tierRuleMapper,
                              PriceTierMapper tierMapper, PriceRequestRuleMapper requestRuleMapper) {
        this.itemMapper = itemMapper;
        this.timeRuleMapper = timeRuleMapper;
        this.segmentMapper = segmentMapper;
        this.tierRuleMapper = tierRuleMapper;
        this.tierMapper = tierMapper;
        this.requestRuleMapper = requestRuleMapper;
    }

    /** 读取报价单的全部明细行（含规则），按 id 升序保证编译稳定。 */
    public List<BillingCompiler.ItemRules> load(Long quoteId) {
        List<BillingCompiler.ItemRules> items = new ArrayList<>();
        for (QuoteItemEntity row : itemMapper.selectListByQuery(QueryWrapper.create()
                .where("quote_id = ?", quoteId).and("deleted = false").orderBy("id asc"))) {
            items.add(new BillingCompiler.ItemRules(row.getModelName(),
                    row.getInputPrice(), row.getOutputPrice(), row.getCacheReadPrice(), row.getCacheWritePrice(),
                    loadTimeRule(row.getId()), loadTierRule(row.getId()), loadRequestRules(row.getId())));
        }
        return items;
    }

    /** 明细行的归属报价单（权限校验用）。 */
    public Long quoteIdOfItem(Long itemId) {
        QuoteItemEntity item = itemMapper.selectOneById(itemId);
        return item == null ? null : item.getQuoteId();
    }

    QuoteValidation.TimeRule loadTimeRule(Long itemId) {
        PriceTimeRuleEntity rule = timeRuleMapper.selectOneByQuery(
                QueryWrapper.create().where("item_id = ?", itemId).limit(1));
        if (rule == null) {
            return null;
        }
        List<QuoteValidation.Segment> segments = new ArrayList<>();
        for (PriceTimeSegmentEntity row : segmentMapper.selectListByQuery(QueryWrapper.create()
                .where("time_rule_id = ?", rule.getId()).orderBy("seq asc"))) {
            segments.add(new QuoteValidation.Segment(String.valueOf(row.getStartTime()),
                    String.valueOf(row.getEndTime())));
        }
        return new QuoteValidation.TimeRule(rule.getTz(), rule.getWeekdayScope(), rule.getPeakMultiplier(),
                rule.getOffpeakMultiplier(), rule.getPeakPriceOverride(), segments);
    }

    QuoteValidation.TierRule loadTierRule(Long itemId) {
        PriceTierRuleEntity rule = tierRuleMapper.selectOneByQuery(
                QueryWrapper.create().where("item_id = ?", itemId).limit(1));
        if (rule == null) {
            return null;
        }
        List<QuoteValidation.Tier> tiers = new ArrayList<>();
        for (PriceTierEntity row : tierMapper.selectListByQuery(QueryWrapper.create()
                .where("tier_rule_id = ?", rule.getId()).orderBy("seq asc"))) {
            tiers.add(new QuoteValidation.Tier(row.getSeq(), row.getMinValue(), row.getMaxValue(), row.getLabel(),
                    row.getInputPrice(), row.getOutputPrice(), row.getCacheReadPrice(), row.getMultiplier()));
        }
        return new QuoteValidation.TierRule(rule.getTierField(), rule.getPriceStrategy(), tiers);
    }

    List<QuoteValidation.RequestRule> loadRequestRules(Long itemId) {
        List<QuoteValidation.RequestRule> rules = new ArrayList<>();
        for (var row : requestRuleMapper.selectListByQuery(QueryWrapper.create()
                .where("item_id = ?", itemId).orderBy("id asc"))) {
            rules.add(new QuoteValidation.RequestRule(null, null, null, null, null,
                    row.getMultiplier(), row.getWhenExpr()));
        }
        return rules;
    }
}
