### 证据：QuoteController 全部路由（用于坐实「编辑报价单时表头不可改」）
### 时间: 2026-09-20 08:17:06
### 真源: aap-server/src/main/java/com/hioas/aap/quote/QuoteController.java

116:    @GetMapping
117-    public ApiEnvelope<PageResult<QuoteViews.Row>> list(@AuthenticationPrincipal AuthPrincipal principal,
125:    @PostMapping
126-    public ApiEnvelope<QuoteViews.Created> create(@AuthenticationPrincipal AuthPrincipal principal,
135:    @GetMapping("/{quoteId}")
136-    public ApiEnvelope<QuoteViews.Detail> detail(@AuthenticationPrincipal AuthPrincipal principal,
142:    @DeleteMapping("/{quoteId}")
143-    public ApiEnvelope<Void> delete(@AuthenticationPrincipal AuthPrincipal principal,
153:    @PostMapping("/{quoteId}/items")
154-    public ApiEnvelope<QuoteViews.Items> setItems(@AuthenticationPrincipal AuthPrincipal principal,
165:    @GetMapping("/{quoteId}/items")
166-    public ApiEnvelope<QuoteViews.Items> listItems(@AuthenticationPrincipal AuthPrincipal principal,
174:    @GetMapping("/items/{itemId}")
175-    public ApiEnvelope<QuoteViews.Item> getItem(@AuthenticationPrincipal AuthPrincipal principal,
181:    @PutMapping("/items/{itemId}")
182-    public ApiEnvelope<QuoteViews.Item> saveItem(@AuthenticationPrincipal AuthPrincipal principal,
193:    @PostMapping("/{quoteId}/submit")
194-    public ApiEnvelope<QuoteViews.Detail> submit(@AuthenticationPrincipal AuthPrincipal principal,
200:    @PostMapping("/{quoteId}/withdraw")
201-    public ApiEnvelope<QuoteViews.Detail> withdraw(@AuthenticationPrincipal AuthPrincipal principal,
207:    @GetMapping("/{quoteId}/versions")
208-    public ApiEnvelope<PageResult<QuoteViews.Version>> versions(@AuthenticationPrincipal AuthPrincipal principal,
218:    @PostMapping("/{quoteId}/compile-preview")
220-    public ApiEnvelope<com.hioas.aap.compile.CompilationViews.Result> compilePreview(
@RequestMapping("/api/v1/quotes")
    @GetMapping
    @PostMapping
    @GetMapping("/{quoteId}")
    @DeleteMapping("/{quoteId}")
    @PostMapping("/{quoteId}/items")
    @GetMapping("/{quoteId}/items")
    @GetMapping("/items/{itemId}")
    @PutMapping("/items/{itemId}")
    @PostMapping("/{quoteId}/submit")
    @PostMapping("/{quoteId}/withdraw")
    @GetMapping("/{quoteId}/versions")
    @PostMapping("/{quoteId}/compile-preview")

--- 判定 ---
PUT 映射只有一处，且路径是 /items/{itemId}（明细行），不是 /{quoteId}（表头）。
结论：报价单**表头字段（名称/主体/凭证）没有更新端点**；
      卡片「报价」进入的编辑态只能真正改动**明细行**（POST /{quoteId}/items 整体替换）。
