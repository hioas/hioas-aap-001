package com.hioas.aap.common;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;

/**
 * JSON 编解码（Spring Boot 4 = Jackson 3：{@code tools.jackson}）。
 *
 * <p>统一出口：entity 的 jsonb 列存字符串，服务层用本类在「字符串 ↔ 类型化对象」之间转换，
 * 保证只有一处 JSON 策略（时间格式、空值、未知字段容忍）。
 */
public final class JsonCodec {

    private static final ObjectMapper MAPPER = JsonMapper.builder().build();

    private JsonCodec() {
    }

    public static String toJson(Object value) {
        return value == null ? null : MAPPER.writeValueAsString(value);
    }

    public static <T> T fromJson(String json, Class<T> type) {
        if (json == null || json.isBlank()) {
            return null;
        }
        return MAPPER.readValue(json, type);
    }

    public static <T> T fromJson(String json, TypeReference<T> type) {
        if (json == null || json.isBlank()) {
            return null;
        }
        return MAPPER.readValue(json, type);
    }

    public static <T> List<T> toList(String json, Class<T> elementType) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        return MAPPER.readValue(json, MAPPER.getTypeFactory().constructCollectionType(List.class, elementType));
    }

    public static List<String> toStringList(String json) {
        return toList(json, String.class);
    }

    public static Map<String, Object> toMap(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyMap();
        }
        return MAPPER.readValue(json, new TypeReference<Map<String, Object>>() {
        });
    }

    public static JsonNode readTree(String json) {
        return json == null || json.isBlank() ? null : MAPPER.readTree(json);
    }

    /** 供需要直接序列化到 HTTP 响应的组件（如安全链的 401 包体）使用。 */
    public static ObjectMapper mapper() {
        return MAPPER;
    }
}
