package com.hioas.aap.common;

import java.util.Arrays;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 统一错误码（真源：`.calicat/prd/17-零歧义执行规格spec.md` §9 + `docs/backend/02-API接口模型清单.md` §4）。
 *
 * <p>本枚举与 {@code docs/backend/json-schema/common/error.schema.json} 的 {@code code} 枚举**必须逐条一致**，
 * 由 {@code ApiEnvelopeTest#errorCodeEnumMatchesContract} 断言守住。
 */
public enum ErrorCode {

    SUCCESS("0", 200, "ok"),

    E_1001("E-1001", 400, "参数校验失败"),
    E_1101("E-1101", 400, "凭证预检失败（连通性或鉴权）"),
    E_1102("E-1102", 400, "凭证当前状态不允许该操作"),
    E_1104("E-1104", 409, "唯一性冲突"),
    E_1201("E-1201", 400, "出站地址被拒绝（SSRF 防护）"),

    E_1301("E-1301", 409, "该凭证已有进行中的检测任务"),
    E_1302("E-1302", 429, "今日检测配额已用尽"),
    E_1303("E-1303", 400, "凭证当前不可发起检测"),
    E_1304("E-1304", 404, "检测任务不存在"),
    E_1305("E-1305", 409, "检测任务已结束，不可取消"),

    E_1401("E-1401", 400, "时段区间重叠或资源不存在"),
    E_1402("E-1402", 400, "阶梯区间存在空洞或重叠"),
    E_1403("E-1403", 400, "倍率非法（须大于 0）"),
    E_1404("E-1404", 400, "阶梯首档须从 0 起、末档须开放"),
    E_1405("E-1405", 400, "计费表达式模拟校验未通过"),
    E_1406("E-1406", 404, "资源不存在"),
    E_1407("E-1407", 409, "编译产物未经确认，禁止写入"),

    E_1501("E-1501", 502, "同步 new-api 失败"),
    E_1505("E-1505", 403, "同步接口权限不足"),

    E_1601("E-1601", 409, "状态非法流转"),
    E_1602("E-1602", 400, "报价前置条件不满足（未通过检测）"),
    E_1701("E-1701", 409, "合同未签署，禁止打款"),

    E_1801("E-1801", 503, "用量聚合失败"),

    E_1901("E-1901", 403, "权限不足"),
    E_1902("E-1902", 401, "未认证或登录已过期"),
    E_1903("E-1903", 429, "请求过于频繁"),

    E_2001("E-2001", 500, "内部错误");

    private static final Map<String, ErrorCode> BY_CODE = Arrays.stream(values())
            .collect(Collectors.toUnmodifiableMap(ErrorCode::code, Function.identity()));

    private final String code;
    private final int httpStatus;
    private final String defaultMessage;

    ErrorCode(String code, int httpStatus, String defaultMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.defaultMessage = defaultMessage;
    }

    public String code() {
        return code;
    }

    public int httpStatus() {
        return httpStatus;
    }

    public String defaultMessage() {
        return defaultMessage;
    }

    public boolean isSuccess() {
        return this == SUCCESS;
    }

    /** 按码取枚举；未知码按内部错误处理（不静默丢弃）。 */
    public static ErrorCode of(String code) {
        ErrorCode found = code == null ? null : BY_CODE.get(code.trim());
        return found == null ? E_2001 : found;
    }
}
