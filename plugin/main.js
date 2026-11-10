var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  DEFAULT_SETTINGS: () => DEFAULT_SETTINGS,
  default: () => BaodanAiPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian2 = require("obsidian");

// src/chat-view.ts
var import_obsidian = require("obsidian");
var VIEW_TYPE_BAODAN_CHAT = "baodan-ai-chat-view";
var BaodanChatView = class extends import_obsidian.ItemView {
  plugin;
  currentFile = null;
  messages = [];
  isThinking = false;
  headerTitleEl;
  messagesContainer;
  inputEl;
  sendBtn;
  quickBar;
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }
  getViewType() {
    return VIEW_TYPE_BAODAN_CHAT;
  }
  getDisplayText() {
    return "\u4FDD\u5355 AI \u667A\u80FD\u8FFD\u95EE";
  }
  getIcon() {
    return "message-circle";
  }
  async onOpen() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.addClass("baodan-chat-container");
    const headerEl = containerEl.createDiv({ cls: "baodan-chat-header" });
    const titleBox = headerEl.createDiv({ cls: "baodan-chat-title-box" });
    const botIcon = titleBox.createSpan({ cls: "baodan-chat-icon" });
    (0, import_obsidian.setIcon)(botIcon, "bot");
    this.headerTitleEl = titleBox.createSpan({
      cls: "baodan-chat-title-text",
      text: "\u8BF7\u5728\u4E3B\u7A97\u53E3\u6253\u5F00\u4E00\u4EFD\u4FDD\u5355\u7B14\u8BB0"
    });
    const actions = headerEl.createDiv({ cls: "baodan-chat-actions" });
    const saveBtn = actions.createEl("button", {
      cls: "baodan-icon-btn",
      attr: { title: "\u{1F4CC} \u5C06\u5F53\u524D\u95EE\u7B54\u4FDD\u5B58\u81F3\u4FDD\u5355\u7B14\u8BB0\u672B\u5C3E" }
    });
    (0, import_obsidian.setIcon)(saveBtn, "save");
    saveBtn.onclick = async () => {
      await this.saveCurrentChatToNote();
    };
    const clearBtn = actions.createEl("button", {
      cls: "baodan-icon-btn",
      attr: { title: "\u{1F5D1}\uFE0F \u6E05\u7A7A\u5F53\u524D\u5BF9\u8BDD" }
    });
    (0, import_obsidian.setIcon)(clearBtn, "trash-2");
    clearBtn.onclick = () => {
      this.messages = [];
      this.renderMessages();
      new import_obsidian.Notice("\u5DF2\u6E05\u7A7A\u5F53\u524D\u8FFD\u95EE\u5BF9\u8BDD\u3002");
    };
    this.quickBar = containerEl.createDiv({ cls: "baodan-quick-bar" });
    const quickPrompts = [
      "\u{1F476} \u5C0F\u5B69\u80BA\u708E\u4F4F\u9662\u62A5\u9500\u6D4B\u7B97",
      "\u{1F48A} \u81EA\u8D39\u836F/\u7279\u836F\u80FD\u62A5\u9500\u5417",
      "\u{1F3E5} \u7279\u9700\u90E8/\u79C1\u7ACB\u533B\u9662\u8D54\u4E0D\u8D54",
      "\u{1F396}\uFE0F \u7406\u8D54\u987B\u63D0\u4F9B\u54EA\u4E9B\u8BC1\u660E\u6750\u6599",
      "\u23F3 \u65E2\u5F80\u75C7\u4E0E30\u5929\u7B49\u5F85\u671F\u89C4\u5B9A",
      "\u{1F4DE} \u95E8\u8BCA\u5C31\u533B\u7EFF\u901A\u600E\u4E48\u9884\u7EA6"
    ];
    for (const q of quickPrompts) {
      const pill = this.quickBar.createEl("button", {
        cls: "baodan-quick-pill",
        text: q
      });
      pill.onclick = () => {
        let question = q;
        if (q.includes("\u5C0F\u5B69\u80BA\u708E\u4F4F\u9662\u62A5\u9500\u6D4B\u7B97")) {
          question = "\u5982\u679C4\u5C81\u5C0F\u5B69\u56E0\u6025\u6027\u80BA\u708E\u4F4F\u9662\u82B1\u8D398,000\u5143\uFF0C\u793E\u4FDD\u62A5\u9500\u540E\u5269\u4F593,000\u5143\uFF0C\u8FD9\u4EFD\u4FDD\u5355\u80FD\u8D54\u591A\u5C11\uFF1F\u8BF7\u7ED9\u51FA\u8BE6\u7EC6\u5206\u6BB5\u8BA1\u7B97\u6B65\u9AA4\u3002";
        } else if (q.includes("\u81EA\u8D39\u836F/\u7279\u836F")) {
          question = "\u4F4F\u9662\u671F\u95F4\u533B\u751F\u5F00\u5177\u7684\u533B\u4FDD\u76EE\u5F55\u5916\u81EA\u8D39\u836F\u3001\u9776\u5411\u836F\u80FD\u5426\u5728\u6B64\u4FDD\u5355\u62A5\u9500\uFF1F\u62A5\u9500\u6BD4\u4F8B\u548C\u9650\u5236\u662F\u4EC0\u4E48\uFF1F";
        } else if (q.includes("\u7279\u9700\u90E8/\u79C1\u7ACB\u533B\u9662")) {
          question = "\u5982\u679C\u56E0\u7D27\u6025\u60C5\u51B5\u53BB\u4E86\u4E09\u7532\u533B\u9662\u7279\u9700\u90E8\u3001\u56FD\u9645\u533B\u7597\u90E8\u6216\u79C1\u7ACB\u533B\u9662\u5C31\u8BCA\uFF0C\u672C\u4FDD\u5355\u662F\u5426\u627F\u62C5\u4FDD\u9669\u8D23\u4EFB\uFF1F";
        } else if (q.includes("\u8BC1\u660E\u6750\u6599")) {
          question = "\u7279\u522B\u7EA6\u5B9A\u4E2D\u9488\u5BF9\u51FA\u9669\u7406\u8D54\uFF0C\u5FC5\u987B\u63D0\u4F9B\u54EA\u4E9B\u5177\u4F53\u8BC1\u660E\u6750\u6599\uFF1F\u5982\u8EAB\u4EFD\u51ED\u8BC1\u6216\u5BB6\u5C5E\u5173\u7CFB\u8BC1\u660E\uFF1F";
        } else if (q.includes("\u65E2\u5F80\u75C7\u4E0E30\u5929\u7B49\u5F85\u671F")) {
          question = "\u5728\u4FDD\u5355\u751F\u6548\u540E30\u5929\u7B49\u5F85\u671F\u5185\u751F\u75C5\uFF0C\u4FDD\u8D39\u662F\u5426\u9000\u8FD8\uFF1F\u6295\u4FDD\u524D\u5DF2\u6709\u7684\u75BE\u75C5\uFF08\u65E2\u5F80\u75C7\uFF09\u80FD\u5426\u7406\u8D54\uFF1F";
        } else if (q.includes("\u95E8\u8BCA\u5C31\u533B\u7EFF\u901A")) {
          question = "\u672C\u4FDD\u5355\u81EA\u5E26\u7684\u4E09\u7532\u533B\u9662\u95E8\u8BCA\u7EFF\u901A\u9884\u7EA6\u670D\u52A1\u5982\u4F55\u7533\u8BF7\uFF1F\u6700\u5FEB\u51E0\u4E2A\u5DE5\u4F5C\u65E5\u80FD\u5B89\u6392\uFF1F\u5305\u542B\u54EA\u4E9B\u5C31\u8BCA\u8D39\u7528\uFF1F";
        }
        this.inputEl.value = question;
        this.handleSend();
      };
    }
    this.messagesContainer = containerEl.createDiv({ cls: "baodan-messages-area" });
    const inputArea = containerEl.createDiv({ cls: "baodan-input-area" });
    this.inputEl = inputArea.createEl("textarea", {
      cls: "baodan-chat-textarea",
      attr: { placeholder: "\u8F93\u5165\u4F60\u60F3\u8FFD\u95EE\u7684\u5177\u4F53\u7406\u8D54\u95EE\u9898\uFF08\u6309 Enter \u53D1\u9001\uFF0CShift+Enter \u6362\u884C\uFF09..." }
    });
    this.inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });
    const bottomRow = inputArea.createDiv({ cls: "baodan-input-bottom" });
    const hintText = bottomRow.createSpan({
      cls: "baodan-input-hint",
      text: "\u{1F916} DeepSeek \u4FDD\u5355\u4E13\u5BB6\u5728\u7EBF"
    });
    this.sendBtn = bottomRow.createEl("button", {
      cls: "baodan-send-btn",
      text: "\u{1F680} \u53D1\u9001\u8FFD\u95EE"
    });
    this.sendBtn.onclick = () => this.handleSend();
    this.detectActivePolicy();
    this.registerEvent(
      this.app.workspace.on("active-leaf-change", () => {
        this.detectActivePolicy();
      })
    );
  }
  detectActivePolicy(file) {
    const activeFile = file || this.app.workspace.getActiveFile();
    if (activeFile && activeFile.path.endsWith(".md")) {
      if (this.currentFile?.path !== activeFile.path) {
        this.currentFile = activeFile;
        this.headerTitleEl.setText(`\u{1F6E1}\uFE0F \u6B63\u5728\u7814\u8BFB\uFF1A${activeFile.basename}`);
        this.messages = [];
        this.messages.push({
          role: "assistant",
          content: `\u60A8\u597D\uFF01\u6211\u662F\u60A8\u7684 **\u4FDD\u5355\u7406\u8D54 AI \u987E\u95EE**\u3002

\u5F53\u524D\u5DF2\u8F7D\u5165\u300A**${activeFile.basename}**\u300B\u7684\u5168\u90E8\u6761\u6B3E\u4E0E\u7279\u522B\u7EA6\u5B9A\u3002\u60A8\u53EF\u4EE5\u70B9\u51FB\u4E0A\u65B9\u7684\u5FEB\u6377\u80F6\u56CA\uFF0C\u6216\u8005\u5728\u4E0B\u65B9\u8F93\u5165\u4EFB\u4F55\u60A8\u5173\u5FC3\u7684\u7406\u8D54\u8BA1\u7B97\u3001\u533B\u9662\u9009\u62E9\u3001\u81EA\u8D39\u836F\u6216\u514D\u8D23\u95EE\u9898\uFF01`,
          timestamp: Date.now()
        });
        this.renderMessages();
      }
    }
  }
  setTargetFile(file) {
    this.currentFile = file;
    this.headerTitleEl.setText(`\u{1F6E1}\uFE0F \u6B63\u5728\u7814\u8BFB\uFF1A${file.basename}`);
    this.detectActivePolicy(file);
  }
  renderMessages() {
    this.messagesContainer.empty();
    for (const msg of this.messages) {
      const bubbleEl = this.messagesContainer.createDiv({
        cls: `baodan-bubble ${msg.role === "user" ? "is-user" : "is-assistant"}`
      });
      const metaRow = bubbleEl.createDiv({ cls: "baodan-bubble-meta" });
      metaRow.setText(msg.role === "user" ? "\u{1F464} \u60A8\u7684\u8FFD\u95EE" : "\u{1F916} DeepSeek \u7406\u8D54\u4E13\u5BB6");
      const contentEl = bubbleEl.createDiv({ cls: "baodan-bubble-content markdown-rendered" });
      void import_obsidian.MarkdownRenderer.renderMarkdown(
        msg.content,
        contentEl,
        this.currentFile?.path || "",
        new import_obsidian.Component()
      );
    }
    if (this.isThinking) {
      const loadingBubble = this.messagesContainer.createDiv({
        cls: "baodan-bubble is-assistant is-loading"
      });
      loadingBubble.createDiv({ cls: "baodan-bubble-meta", text: "\u{1F916} DeepSeek \u7406\u8D54\u4E13\u5BB6" });
      const textEl = loadingBubble.createDiv({ cls: "baodan-bubble-content" });
      textEl.setText("\u23F3 \u6B63\u5728\u7FFB\u9605\u4FDD\u5355\u5408\u540C\u4E0E\u6838\u4FDD\u89C4\u5219\uFF0C\u7EC4\u7EC7\u6743\u5A01\u89E3\u7B54...");
    }
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }
  async handleSend() {
    const question = this.inputEl.value.trim();
    if (!question || this.isThinking) return;
    if (!this.currentFile) {
      new import_obsidian.Notice("\u8BF7\u5148\u5728\u4E3B\u7A97\u53E3\u4E2D\u6253\u5F00\u4E00\u4EFD\u4FDD\u5355\u7B14\u8BB0\uFF01");
      return;
    }
    this.inputEl.value = "";
    this.messages.push({ role: "user", content: question, timestamp: Date.now() });
    this.isThinking = true;
    this.sendBtn.disabled = true;
    this.renderMessages();
    try {
      const answer = await this.queryDeepSeekForAnswer(question);
      this.messages.push({ role: "assistant", content: answer, timestamp: Date.now() });
    } catch (err) {
      this.messages.push({
        role: "assistant",
        content: `\u274C \u89E3\u7B54\u5931\u8D25: ${err?.message || err}`,
        timestamp: Date.now()
      });
    } finally {
      this.isThinking = false;
      this.sendBtn.disabled = false;
      this.renderMessages();
    }
  }
  async queryDeepSeekForAnswer(question) {
    if (!this.currentFile) {
      throw new Error("\u672A\u9009\u5B9A\u4FDD\u5355\u6587\u4EF6");
    }
    const settings = this.plugin.settings;
    if (!settings.aiApiKey) {
      throw new Error("\u672A\u914D\u7F6E DeepSeek API Key\uFF0C\u8BF7\u5728\u63D2\u4EF6\u8BBE\u7F6E\u4E2D\u586B\u5199");
    }
    const fullContent = await this.app.vault.read(this.currentFile);
    const policyContext = fullContent.slice(0, 2e4);
    const systemPrompt = `\u4F60\u662F\u4E00\u4F4D\u7CBE\u901A\u4E2D\u56FD\u5927\u9646\u5546\u4E1A\u5065\u5EB7\u9669\u4E0E\u533B\u7597\u9669\u6761\u6B3E\u7684\u8D44\u6DF1\u7CBE\u7B97\u4E0E\u6838\u4FDD\u4E13\u5BB6\u3002
\u5F53\u524D\u7528\u6237\u6B63\u5728\u67E5\u9605\u4E00\u4EFD\u771F\u5B9E\u7684\u4E2A\u4EBA\u4FDD\u9669\u5408\u540C\u7B14\u8BB0\uFF0C\u5E76\u5BF9\u8BE5\u4FDD\u5355\u7684\u5177\u4F53\u7406\u8D54\u89C4\u5219\u3001\u514D\u8D23\u6392\u96F7\u3001\u533B\u9662\u7B49\u7EA7\u3001\u62A5\u9500\u91D1\u989D\u6D4B\u7B97\u6216\u589E\u503C\u6743\u76CA\u63D0\u51FA\u4E86\u8FFD\u95EE\u3002

\u4F60\u7684\u804C\u8D23\uFF1A
1. \u5FC5\u987B\u5B8C\u5168\u57FA\u4E8E\u4FDD\u5355\u7B14\u8BB0\u63D0\u4F9B\u7684\u771F\u5B9E\u5408\u540C\u7EA6\u5B9A\uFF08\u514D\u8D54\u989D\u3001\u5206\u6BB5\u62A5\u9500\u6BD4\u4F8B\u3001\u6709\u65E0\u793E\u4FDD\u5C31\u8BCA\u5DEE\u5F02\u3001\u7ED9\u4ED8\u9650\u989D\u3001\u7279\u6B8A\u9650\u5236\u4E0E\u7EA6\u5B9A\uFF09\u8FDB\u884C\u7CBE\u786E\u8BA1\u7B97\u4E0E\u89E3\u7B54\uFF1B
2. \u82E5\u6D89\u53CA\u8D39\u7528\u62A5\u9500\u6D4B\u7B97\uFF0C\u5FC5\u987B\u7ED9\u51FA\u6E05\u6670\u7684\u6570\u5B66\u516C\u5F0F\u548C\u5206\u6B65\u9AA4\u8BA1\u7B97\u8FC7\u7A0B\uFF1B
3. \u660E\u786E\u63D0\u793A\u7528\u6237\u7406\u8D54\u65F6\u7684\u7EA2\u7EBF\uFF08\u5982\u533B\u4FDD\u7ED3\u7B97\u3001\u4E8C\u7EA7\u4EE5\u4E0A\u516C\u7ACB\u533B\u9662\u666E\u901A\u90E8\u3001\u5FC5\u5907\u8BC1\u4EF6\u6E05\u5355\uFF09\uFF1B
4. \u8BED\u8A00\u4E13\u4E1A\u3001\u5BA2\u89C2\u3001\u4E25\u8C28\uFF0C\u4E25\u7981\u80E1\u7F16\u4E71\u9020\u4E0D\u5B58\u5728\u7684\u8D23\u4EFB\u3002`;
    const recentMessages = this.messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content
    }));
    const userPrompt = `\u3010\u5F53\u524D\u7814\u8BFB\u4FDD\u5355\u3011\uFF1A${this.currentFile.basename}

\u3010\u4FDD\u5355\u5408\u540C\u4E0E\u6838\u67E5\u6838\u5FC3\u4E0A\u4E0B\u6587\u3011\uFF1A
${policyContext}

\u3010\u7528\u6237\u5177\u4F53\u8FFD\u95EE\u95EE\u9898\u3011\uFF1A
${question}`;
    const payload = {
      model: settings.aiModel || "deepseek-chat",
      messages: [
        { role: "system", content: systemPrompt },
        ...recentMessages.filter((m) => m.role !== "system"),
        { role: "user", content: userPrompt }
      ],
      temperature: 0.2,
      max_tokens: 2500
    };
    const url = `${settings.aiApiUrl.replace(/\/+$/, "")}/chat/completions`;
    const response = await (0, import_obsidian.requestUrl)({
      url,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${settings.aiApiKey.trim()}`
      },
      body: JSON.stringify(payload),
      throw: false
    });
    if (response.status !== 200) {
      let errMsg = `HTTP ${response.status}`;
      try {
        const errJson = JSON.parse(response.text);
        if (errJson?.error?.message) errMsg = errJson.error.message;
      } catch {
      }
      throw new Error(errMsg);
    }
    const data = JSON.parse(response.text);
    return data?.choices?.[0]?.message?.content?.trim() || "DeepSeek \u672A\u8FD4\u56DE\u6709\u6548\u89E3\u7B54\u3002";
  }
  async saveCurrentChatToNote() {
    if (!this.currentFile) {
      new import_obsidian.Notice("\u672A\u9009\u5B9A\u4FDD\u5355\u6587\u4EF6\uFF01");
      return;
    }
    const qaPairs = [];
    for (let i = 0; i < this.messages.length - 1; i++) {
      if (this.messages[i].role === "user" && this.messages[i + 1].role === "assistant") {
        qaPairs.push({
          q: this.messages[i].content,
          a: this.messages[i + 1].content,
          time: new Date(this.messages[i + 1].timestamp).toLocaleString()
        });
      }
    }
    if (qaPairs.length === 0) {
      new import_obsidian.Notice("\u5F53\u524D\u6CA1\u6709\u53EF\u4FDD\u5B58\u7684\u8FFD\u95EE\u5BF9\u8BDD\uFF01");
      return;
    }
    let appendMd = `

### \u{1F4AC} \u5386\u53F2 AI \u8FFD\u95EE\u4E0E\u7B54\u7591\u8BB0\u5F55

`;
    for (const pair of qaPairs) {
      appendMd += `> [!QUESTION] \u2753 \u8FFD\u95EE\uFF1A${pair.q.replace(/\n/g, " ")}
`;
      appendMd += `> **\u{1F916} DeepSeek \u4E13\u5BB6\u89E3\u7B54** *(${pair.time})*\uFF1A
>
`;
      const formattedAns = pair.a.split("\n").map((l) => `> ${l}`).join("\n");
      appendMd += `${formattedAns}

`;
    }
    const fileContent = await this.app.vault.read(this.currentFile);
    let newContent = fileContent;
    const header = "### \u{1F4AC} \u5386\u53F2 AI \u8FFD\u95EE\u4E0E\u7B54\u7591\u8BB0\u5F55";
    if (newContent.includes(header)) {
      newContent = newContent + "\n" + appendMd.replace(header + "\n\n", "");
    } else {
      newContent = newContent + appendMd;
    }
    await this.app.vault.modify(this.currentFile, newContent);
    new import_obsidian.Notice(`\u2705 \u5DF2\u6210\u529F\u5C06 ${qaPairs.length} \u6761\u8FFD\u95EE\u8BB0\u5F55\u6301\u4E45\u5316\u4FDD\u5B58\u81F3\u300A${this.currentFile.basename}\u300B\uFF01`);
  }
};

// src/main.ts
var DEFAULT_SETTINGS = {
  aiApiUrl: "https://api.deepseek.com/v1",
  aiApiKey: "",
  aiModel: "deepseek-chat",
  temperature: 0.2
};
var BaodanAiPlugin = class extends import_obsidian2.Plugin {
  settings;
  async onload() {
    await this.loadSettings();
    this.registerView(
      VIEW_TYPE_BAODAN_CHAT,
      (leaf) => new BaodanChatView(leaf, this)
    );
    this.addRibbonIcon("message-square", "\u4FDD\u5355 AI: \u6253\u5F00\u667A\u80FD\u8FFD\u95EE\u4E0E\u7B54\u7591\u9762\u677F", async () => {
      const activeFile = this.app.workspace.getActiveFile();
      await this.openChatView(activeFile || void 0);
    });
    this.addCommand({
      id: "baodan-ai-open-chat",
      name: "\u6253\u5F00\u4FDD\u5355\u667A\u80FD\u8FFD\u95EE\u5BF9\u8BDD\u9762\u677F (Chat)",
      checkCallback: (checking) => {
        const activeFile = this.app.workspace.getActiveFile();
        if (checking) return !!(activeFile && activeFile.path.endsWith(".md"));
        this.openChatView(activeFile || void 0);
      }
    });
    this.addCommand({
      id: "baodan-ai-open-dashboard",
      name: "\u6253\u5F00\u5168\u5BB6\u4FDD\u5355\u591A\u7EF4\u7EDF\u8BA1\u4E0E\u53EF\u89C6\u5316\u5927\u76D8 (Dashboard)",
      callback: async () => {
        const file = this.app.vault.getAbstractFileByPath("00_\u770B\u677F\u4E2D\u5FC3/\u{1F4C8} \u5168\u5BB6\u4FDD\u5355\u591A\u7EF4\u6570\u636E\u7EDF\u8BA1\u5927\u76D8.md");
        if (file instanceof import_obsidian2.TFile) {
          await this.app.workspace.getLeaf(false).openFile(file);
        } else {
          new import_obsidian2.Notice("\u672A\u627E\u5230\u7EDF\u8BA1\u5927\u76D8\u6587\u4EF6");
        }
      }
    });
    this.addCommand({
      id: "baodan-ai-analyze-current",
      name: "\u6267\u884C DeepSeek \u6761\u6B3E\u6DF1\u5EA6\u7CBE\u8BFB\u4E0E\u7406\u8D54\u6392\u96F7",
      checkCallback: (checking) => {
        const activeFile = this.app.workspace.getActiveFile();
        const isValid = activeFile && activeFile.path.endsWith(".md");
        if (checking) return !!isValid;
        if (isValid) {
          this.runAiAnalysis(activeFile);
        }
      }
    });
    this.registerMarkdownCodeBlockProcessor("baodan-ai", (source, el, ctx) => {
      el.empty();
      const container = el.createDiv({ cls: "baodan-ai-box" });
      const header = container.createDiv({ cls: "baodan-ai-header" });
      header.innerHTML = `<span class="baodan-ai-icon">\u{1F916}</span> <strong>DeepSeek \u4FDD\u5355 AI \u52A9\u624B\u4E0E\u667A\u80FD\u95EE\u7B54</strong>`;
      const btnRow = container.createDiv({ cls: "baodan-ai-btn-row" });
      const reanalyzeBtn = btnRow.createEl("button", {
        text: "\u26A1 \u4E00\u952E\u8C03\u7528 DeepSeek \u91CD\u65B0\u6DF1\u5EA6\u7CBE\u8BFB",
        cls: "baodan-ai-btn"
      });
      const openSideChatBtn = btnRow.createEl("button", {
        text: "\u{1F5A5}\uFE0F \u5C55\u5F00\u53F3\u4FA7\u8FFD\u95EE\u4FA7\u8FB9\u680F",
        cls: "baodan-ai-btn baodan-btn-secondary"
      });
      openSideChatBtn.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
        if (file instanceof import_obsidian2.TFile) {
          await this.openChatView(file);
        } else {
          await this.openChatView();
        }
      };
      const statusEl = container.createDiv({ cls: "baodan-ai-status" });
      statusEl.setText("\u{1F4A1} \u652F\u6301\u76F4\u63A5\u5728\u4E0B\u65B9\u8F93\u5165\u6846\u5411 DeepSeek \u8FFD\u95EE\u514D\u8D54\u6D4B\u7B97\u3001\u81EA\u8D39\u836F\u62A5\u9500\u3001\u7279\u9700\u90E8\u9650\u5236\u7B49\u5177\u4F53\u95EE\u9898\uFF1A");
      reanalyzeBtn.onclick = async () => {
        reanalyzeBtn.disabled = true;
        reanalyzeBtn.setText("\u23F3 DeepSeek \u6B63\u5728\u6DF1\u5EA6\u68B3\u7406\u6761\u6B3E\u4E2D\uFF0C\u8BF7\u7A0D\u5019...");
        statusEl.setText("\u6B63\u5728\u8FDE\u63A5 DeepSeek \u4E91\u7AEF\u5927\u6A21\u578B\uFF0C\u63D0\u53D6\u514D\u8D54\u989D\u3001\u5206\u6BB5\u62A5\u9500\u6BD4\u3001\u7B49\u5F85\u671F\u53CA\u5355\u8BC1\u6E05\u5355...");
        try {
          const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
          if (file instanceof import_obsidian2.TFile) {
            await this.runAiAnalysis(file);
            reanalyzeBtn.setText("\u{1F504} \u91CD\u65B0\u6267\u884C DeepSeek \u6761\u6B3E\u7CBE\u8BFB");
            reanalyzeBtn.disabled = false;
            statusEl.setText(`\u2705 \u6761\u6B3E\u6DF1\u5EA6\u7CBE\u8BFB\u5DF2\u4E8E ${(/* @__PURE__ */ new Date()).toLocaleTimeString()} \u5B8C\u6210\u66F4\u65B0\uFF01\u7ED3\u679C\u5448\u73B0\u5728\u4E0B\u65B9\u3002`);
          } else {
            throw new Error("\u672A\u627E\u5230\u5F53\u524D\u4FDD\u5355\u7B14\u8BB0\u6587\u4EF6");
          }
        } catch (err) {
          reanalyzeBtn.disabled = false;
          reanalyzeBtn.setText("\u274C \u5206\u6790\u5931\u8D25\uFF0C\u70B9\u51FB\u91CD\u8BD5");
          statusEl.setText(`\u9519\u8BEF: ${err?.message || err}`);
        }
      };
      const qaSection = container.createDiv({ cls: "baodan-inline-qa-box" });
      const qaTitle = qaSection.createDiv({ cls: "baodan-qa-title" });
      qaTitle.innerHTML = `<strong>\u{1F4AC} \u4FDD\u5355\u667A\u80FD\u8FFD\u95EE\uFF1A</strong> <span class="baodan-qa-sub">\u7ED3\u5408\u5F53\u524D\u4FDD\u5355\u771F\u5B9E\u6761\u6B3E\uFF0C\u5206\u6B65\u9AA4\u8BA1\u7B97\u4E0E\u6392\u96F7</span>`;
      const quickBar = qaSection.createDiv({ cls: "baodan-quick-bar" });
      const quickQuestions = [
        "\u{1F476} \u5C0F\u5B69\u80BA\u708E\u4F4F\u9662\u82B18000\u80FD\u8D54\u591A\u5C11\uFF1F",
        "\u{1F48A} \u533B\u4FDD\u5916\u81EA\u8D39\u836F\u80FD\u62A5\u9500\u5417\uFF1F",
        "\u{1F3E5} \u7279\u9700\u90E8/\u79C1\u7ACB\u533B\u9662\u8D54\u4E0D\u8D54\uFF1F",
        "\u{1F396}\uFE0F \u4F18\u5F85\u8BC1\u4E0E\u5BB6\u5C5E\u5173\u7CFB\u8BC1\u660E\u8981\u6C42\uFF1F",
        "\u23F3 30\u5929\u7B49\u5F85\u671F\u5185\u751F\u75C5\u9000\u4FDD\u8D39\u5417\uFF1F"
      ];
      for (const q of quickQuestions) {
        const pill = quickBar.createEl("button", {
          cls: "baodan-quick-pill",
          text: q
        });
        pill.onclick = () => {
          inputEl.value = q;
          triggerInlineAsk();
        };
      }
      const inputRow = qaSection.createDiv({ cls: "baodan-qa-input-row" });
      const inputEl = inputRow.createEl("textarea", {
        cls: "baodan-qa-input",
        attr: {
          placeholder: "\u4F8B\u5982\uFF1A\u5B69\u5B50\u56E0\u610F\u5916\u9AA8\u6298\u5728\u4E8C\u7EA7\u516C\u7ACB\u533B\u9662\u82B1\u8D395000\u5143\uFF0C\u793E\u4FDD\u672A\u62A5\u9500\uFF0C\u672C\u5355\u80FD\u8D54\u591A\u5C11\uFF1F",
          rows: "2"
        }
      });
      const askBtn = inputRow.createEl("button", {
        cls: "baodan-ai-btn baodan-ask-btn",
        text: "\u{1F680} \u7ACB\u5373\u8FFD\u95EE"
      });
      const resultArea = qaSection.createDiv({ cls: "baodan-qa-result", attr: { style: "display: none;" } });
      const resultHeader = resultArea.createDiv({ cls: "baodan-result-header" });
      resultHeader.innerHTML = `<span>\u{1F916} <strong>DeepSeek \u4E13\u5BB6\u89E3\u7B54\uFF1A</strong></span>`;
      const saveToNoteBtn = resultHeader.createEl("button", {
        cls: "baodan-save-inline-btn",
        text: "\u{1F4CC} \u4FDD\u5B58\u6B64\u95EE\u7B54\u81F3\u4FDD\u5355\u7B14\u8BB0\u672B\u5C3E"
      });
      const answerContent = resultArea.createDiv({ cls: "baodan-answer-content markdown-rendered" });
      let lastQuestion = "";
      let lastAnswer = "";
      const triggerInlineAsk = async () => {
        const qText = inputEl.value.trim();
        if (!qText) return;
        askBtn.disabled = true;
        askBtn.setText("\u23F3 \u601D\u8003\u4E2D...");
        resultArea.style.display = "block";
        answerContent.setText("\u23F3 DeepSeek \u6B63\u5728\u57FA\u4E8E\u4FDD\u5355\u5408\u540C\u6761\u6B3E\u8FDB\u884C\u903B\u8F91\u6F14\u7B97\u4E0E\u6392\u96F7\u89E3\u7B54...");
        try {
          const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
          if (!(file instanceof import_obsidian2.TFile)) {
            throw new Error("\u672A\u5B9A\u4F4D\u5230\u4FDD\u5355\u7B14\u8BB0\u6587\u4EF6");
          }
          const answer = await this.queryDeepSeekFollowUp(file, qText);
          lastQuestion = qText;
          lastAnswer = answer;
          answerContent.empty();
          void import_obsidian2.MarkdownRenderer.renderMarkdown(
            answer,
            answerContent,
            file.path,
            new import_obsidian2.Component()
          );
          askBtn.disabled = false;
          askBtn.setText("\u{1F680} \u7ACB\u5373\u8FFD\u95EE");
        } catch (err) {
          askBtn.disabled = false;
          askBtn.setText("\u{1F680} \u7ACB\u5373\u8FFD\u95EE");
          answerContent.setText(`\u274C \u8FFD\u95EE\u5931\u8D25: ${err?.message || err}`);
        }
      };
      askBtn.onclick = () => triggerInlineAsk();
      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          triggerInlineAsk();
        }
      });
      saveToNoteBtn.onclick = async () => {
        if (!lastQuestion || !lastAnswer) return;
        const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
        if (file instanceof import_obsidian2.TFile) {
          await this.appendQAToFile(file, lastQuestion, lastAnswer);
          saveToNoteBtn.setText("\u2705 \u5DF2\u4FDD\u5B58\u5230\u7B14\u8BB0\u672B\u5C3E");
          saveToNoteBtn.disabled = true;
        }
      };
    });
    this.addSettingTab(new BaodanAiSettingTab(this.app, this));
  }
  async openChatView(file) {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE_BAODAN_CHAT)[0];
    if (!leaf) {
      const rightLeaf = this.app.workspace.getRightLeaf(false);
      if (rightLeaf) {
        leaf = rightLeaf;
        await leaf.setViewState({
          type: VIEW_TYPE_BAODAN_CHAT,
          active: true
        });
      }
    }
    if (leaf) {
      this.app.workspace.revealLeaf(leaf);
      const view = leaf.view;
      if (view && typeof view.setTargetFile === "function") {
        const target = file || this.app.workspace.getActiveFile() || void 0;
        if (target) view.setTargetFile(target);
      }
    }
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  async queryDeepSeekFollowUp(file, question) {
    if (!this.settings.aiApiKey) {
      throw new Error("\u672A\u914D\u7F6E DeepSeek API Key");
    }
    const fullContent = await this.app.vault.read(file);
    const policyContext = fullContent.slice(0, 2e4);
    const systemPrompt = `\u4F60\u662F\u4E00\u4F4D\u7CBE\u901A\u4E2D\u56FD\u5546\u4E1A\u5065\u5EB7\u9669\u4E0E\u533B\u7597\u9669\u6761\u6B3E\u7684\u8D44\u6DF1\u7CBE\u7B97\u4E0E\u6838\u4FDD\u4E13\u5BB6\u3002
\u5F53\u524D\u7528\u6237\u6B63\u5728\u67E5\u9605\u4E00\u4EFD\u771F\u5B9E\u7684\u4E2A\u4EBA\u4FDD\u9669\u5408\u540C\u7B14\u8BB0\uFF0C\u5E76\u5BF9\u8BE5\u4FDD\u5355\u7684\u5177\u4F53\u7406\u8D54\u89C4\u5219\u3001\u514D\u8D23\u6392\u96F7\u3001\u533B\u9662\u7B49\u7EA7\u3001\u62A5\u9500\u91D1\u989D\u6D4B\u7B97\u6216\u589E\u503C\u6743\u76CA\u63D0\u51FA\u4E86\u8FFD\u95EE\u3002

\u4F60\u7684\u804C\u8D23\uFF1A
1. \u5FC5\u987B\u5B8C\u5168\u57FA\u4E8E\u4FDD\u5355\u7B14\u8BB0\u63D0\u4F9B\u7684\u771F\u5B9E\u5408\u540C\u7EA6\u5B9A\uFF08\u514D\u8D54\u989D\u3001\u5206\u6BB5\u62A5\u9500\u6BD4\u4F8B\u3001\u6709\u65E0\u793E\u4FDD\u5C31\u8BCA\u5DEE\u5F02\u3001\u7ED9\u4ED8\u9650\u989D\u3001\u7279\u6B8A\u9650\u5236\u4E0E\u7EA6\u5B9A\uFF09\u8FDB\u884C\u7CBE\u786E\u8BA1\u7B97\u4E0E\u89E3\u7B54\uFF1B
2. \u82E5\u6D89\u53CA\u8D39\u7528\u62A5\u9500\u6D4B\u7B97\uFF0C\u5FC5\u987B\u7ED9\u51FA\u6E05\u6670\u7684\u6570\u5B66\u516C\u5F0F\u548C\u5206\u6B65\u9AA4\u8BA1\u7B97\u8FC7\u7A0B\uFF1B
3. \u660E\u786E\u63D0\u793A\u7528\u6237\u7406\u8D54\u65F6\u7684\u7EA2\u7EBF\uFF08\u5982\u533B\u4FDD\u7ED3\u7B97\u3001\u4E8C\u7EA7\u4EE5\u4E0A\u516C\u7ACB\u533B\u9662\u666E\u901A\u90E8\u3001\u5FC5\u5907\u8BC1\u4EF6\u6E05\u5355\uFF09\uFF1B
4. \u8BED\u8A00\u4E13\u4E1A\u3001\u5BA2\u89C2\u3001\u4E25\u8C28\uFF0C\u4E25\u7981\u80E1\u7F16\u4E71\u9020\u4E0D\u5B58\u5728\u7684\u8D23\u4EFB\u3002`;
    const userPrompt = `\u3010\u5F53\u524D\u7814\u8BFB\u4FDD\u5355\u3011\uFF1A${file.basename}

\u3010\u4FDD\u5355\u5408\u540C\u4E0E\u6838\u67E5\u6838\u5FC3\u4E0A\u4E0B\u6587\u3011\uFF1A
${policyContext}

\u3010\u7528\u6237\u5177\u4F53\u8FFD\u95EE\u95EE\u9898\u3011\uFF1A
${question}`;
    const payload = {
      model: this.settings.aiModel || "deepseek-chat",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.2,
      max_tokens: 2500
    };
    const url = `${this.settings.aiApiUrl.replace(/\/+$/, "")}/chat/completions`;
    const response = await (0, import_obsidian2.requestUrl)({
      url,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.settings.aiApiKey.trim()}`
      },
      body: JSON.stringify(payload),
      throw: false
    });
    if (response.status !== 200) {
      let errMsg = `HTTP ${response.status}`;
      try {
        const errJson = JSON.parse(response.text);
        if (errJson?.error?.message) errMsg = errJson.error.message;
      } catch {
      }
      throw new Error(errMsg);
    }
    const data = JSON.parse(response.text);
    return data?.choices?.[0]?.message?.content?.trim() || "DeepSeek \u672A\u8FD4\u56DE\u6709\u6548\u89E3\u7B54\u3002";
  }
  async appendQAToFile(file, question, answer) {
    const timeStr = (/* @__PURE__ */ new Date()).toLocaleString();
    let appendMd = `

### \u{1F4AC} \u5386\u53F2 AI \u8FFD\u95EE\u4E0E\u7B54\u7591\u8BB0\u5F55

`;
    appendMd += `> [!QUESTION] \u2753 \u8FFD\u95EE\uFF1A${question.replace(/\n/g, " ")}
`;
    appendMd += `> **\u{1F916} DeepSeek \u4E13\u5BB6\u89E3\u7B54** *(${timeStr})*\uFF1A
>
`;
    const formattedAns = answer.split("\n").map((l) => `> ${l}`).join("\n");
    appendMd += `${formattedAns}

`;
    const content = await this.app.vault.read(file);
    const header = "### \u{1F4AC} \u5386\u53F2 AI \u8FFD\u95EE\u4E0E\u7B54\u7591\u8BB0\u5F55";
    let newContent = content;
    if (newContent.includes(header)) {
      newContent = newContent + "\n" + appendMd.replace(header + "\n\n", "");
    } else {
      newContent = newContent + appendMd;
    }
    await this.app.vault.modify(file, newContent);
    new import_obsidian2.Notice(`\u2705 \u5DF2\u6210\u529F\u5C06\u8FFD\u95EE\u8BB0\u5F55\u4FDD\u5B58\u81F3\u300A${file.basename}\u300B\u7B14\u8BB0\u672B\u5C3E\uFF01`);
  }
  async runAiAnalysis(file) {
    if (!this.settings.aiApiKey) {
      new import_obsidian2.Notice("\u274C \u672A\u914D\u7F6E DeepSeek API Key\uFF0C\u8BF7\u5728\u63D2\u4EF6\u8BBE\u7F6E\u4E2D\u586B\u5199\u3002");
      throw new Error("\u672A\u914D\u7F6E DeepSeek API Key");
    }
    new import_obsidian2.Notice(`\u23F3 \u6B63\u5728\u5BF9\u300A${file.basename}\u300B\u6267\u884C DeepSeek \u6761\u6B3E\u6DF1\u5EA6\u7CBE\u8BFB...`, 5e3);
    const content = await this.app.vault.read(file);
    const clauseContext = content.slice(0, 25e3);
    const systemPrompt = `\u4F60\u662F\u4E00\u4F4D\u8D44\u6DF1\u4E13\u4E1A\u7684\u4FDD\u9669\u7406\u8D54\u7CBE\u7B97\u4E0E\u6838\u4FDD\u4E13\u5BB6\u3002
\u5F53\u524D\u4F60\u9700\u8981\u6DF1\u5EA6\u68B3\u7406\u4E00\u4EFD\u5DF2\u7ECF\u5B8C\u6210\u672C\u5730\u8131\u654F\u7684\u771F\u5B9E\u4E2A\u4EBA\u4FDD\u9669\u4FDD\u5355\u3002
\u8BF7\u4E25\u683C\u57FA\u4E8E\u4FDD\u5355\u63D0\u4F9B\u7684\u771F\u5B9E\u5408\u540C\u6761\u6B3E\u8F93\u51FA\u7ED3\u6784\u5316\u7684 Markdown \u62A5\u544A\uFF0C\u4E25\u7981\u7F16\u9020\u4E0D\u5B58\u5728\u7684\u8D23\u4EFB\u3002

\u8F93\u51FA\u7ED3\u6784\u5FC5\u987B\u5305\u542B\uFF1A
1. \u{1F6E1}\uFE0F \u6838\u5FC3\u4FDD\u969C\u8303\u56F4\u4E0E\u8D54\u4ED8\u6807\u51C6\uFF08\u7528\u8868\u683C\u5448\u73B0\uFF1A\u5404\u9879\u8D23\u4EFB\u4FDD\u989D\u3001\u514D\u8D54\u989D\u3001\u6709\u65E0\u793E\u4FDD\u5C31\u8BCA\u7ED3\u7B97\u6BD4\u4F8B\u5DEE\u5F02\u3001\u8D54\u4ED8\u4E0A\u9650\uFF09
2. \u26A0\uFE0F \u514D\u9664\u8D23\u4EFB\u4E0E\u6697\u5751\u6392\u67E5\uFF08\u660E\u786E\u6307\u51FA\u54EA\u4E9B\u60C5\u51B5\u4E0D\u8D54\u3001\u65E2\u5F80\u75C7\u8981\u6C42\u3001\u5C31\u533B\u516C\u7ACB\u533B\u9662\u7B49\u7EA7\u9650\u5236\u3001\u7279\u9700\u90E8/\u79C1\u7ACB\u662F\u5426\u652F\u6301\uFF09
3. \u23F0 \u5173\u952E\u65F6\u95F4\u70B9\u4E0E\u7406\u8D54\u6750\u6599\u6E05\u5355\uFF08\u7B49\u5F85\u671F\u5929\u6570\u3001\u7406\u8D54\u62A5\u6848\u65F6\u6548\u9650\u5236\u3001\u51FA\u9669\u540E\u5FC5\u987B\u51C6\u5907\u7684\u8BC1\u660E\u6750\u6599\uFF09
4. \u{1F4B3} \u7F34\u8D39\u3001\u7EED\u4FDD\u4E0E\u589E\u503C\u6743\u76CA\uFF08\u4EA4\u8D39\u65B9\u5F0F\u3001\u662F\u5426\u4FDD\u8BC1\u7EED\u4FDD\u3001\u5305\u542B\u54EA\u4E9B\u7279\u836F/\u7EFF\u901A\u7B49\u589E\u503C\u670D\u52A1\u53CA\u7533\u8BF7\u9014\u5F84\uFF09
5. \u{1F3AF} \u4E00\u53E5\u8BDD\u7406\u8D54\u6781\u7B80\u53E3\u8BC0\uFF08\u7528\u901A\u4FD7\u53E3\u8BED\u603B\u7ED3\uFF1A\u5728\u4EC0\u4E48\u60C5\u51B5\u4E0B\uFF0C\u53BB\u4EC0\u4E48\u533B\u9662\uFF0C\u51C6\u5907\u4EC0\u4E48\u8D44\u6599\uFF0C\u80FD\u8D54\u591A\u5C11\u94B1\uFF09`;
    const userPrompt = `\u3010\u4FDD\u5355\u7B14\u8BB0\u540D\u79F0\u3011\uFF1A${file.basename}

\u3010\u8131\u654F\u4FDD\u5355\u53CA\u6761\u6B3E\u6838\u5FC3\u3011\uFF1A
${clauseContext}`;
    const url = `${this.settings.aiApiUrl.replace(/\/+$/, "")}/chat/completions`;
    const payload = {
      model: this.settings.aiModel || "deepseek-chat",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: this.settings.temperature || 0.2,
      max_tokens: 4e3
    };
    const response = await (0, import_obsidian2.requestUrl)({
      url,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.settings.aiApiKey.trim()}`
      },
      body: JSON.stringify(payload),
      throw: false
    });
    if (response.status !== 200) {
      let errMsg = `HTTP ${response.status}`;
      try {
        const errJson = JSON.parse(response.text);
        if (errJson?.error?.message) errMsg = errJson.error.message;
      } catch {
      }
      new import_obsidian2.Notice(`\u274C DeepSeek \u8BF7\u6C42\u5931\u8D25: ${errMsg}`);
      throw new Error(`AI \u8BF7\u6C42\u5931\u8D25 (${errMsg})`);
    }
    const data = JSON.parse(response.text);
    const aiReport = data?.choices?.[0]?.message?.content?.trim();
    if (!aiReport) {
      throw new Error("DeepSeek \u672A\u8FD4\u56DE\u6709\u6548\u5185\u5BB9");
    }
    const aiSectionHeader = "## \u{1F916} 2. \u5927\u6A21\u578B\u6761\u6B3E\u6DF1\u5EA6\u68B3\u7406\uFF08DeepSeek \u667A\u80FD\u7CBE\u8BFB\uFF09";
    const nextSectionHeader = "## \u{1F4D1} 3. \u5B8C\u6574\u4FDD\u5355\u6761\u6B3E\u4E0E\u9644\u4EF6\u5B58\u6863";
    const newAiBlock = `${aiSectionHeader}

\`\`\`baodan-ai
button: true
\`\`\`

> [!SUCCESS] \u{1F916} DeepSeek AI \u4E13\u5BB6\u6DF1\u5EA6\u6761\u6B3E\u4E0E\u7406\u8D54\u68B3\u7406\u62A5\u544A
> *(\u751F\u6210\u65F6\u95F4\uFF1A${(/* @__PURE__ */ new Date()).toLocaleString()} \uFF5C \u6A21\u578B\uFF1A${this.settings.aiModel})*

${aiReport}

---

`;
    let newContent = content;
    const startIdx = content.indexOf(aiSectionHeader);
    const endIdx = content.indexOf(nextSectionHeader);
    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
      newContent = content.slice(0, startIdx) + newAiBlock + content.slice(endIdx);
    } else if (startIdx !== -1) {
      const rest = content.slice(startIdx + aiSectionHeader.length);
      const nextHr = rest.indexOf("\n---\n");
      if (nextHr !== -1) {
        newContent = content.slice(0, startIdx) + newAiBlock + rest.slice(nextHr + 5);
      } else {
        newContent = content.slice(0, startIdx) + newAiBlock;
      }
    } else {
      newContent = content + "\n\n" + newAiBlock;
    }
    await this.app.vault.modify(file, newContent);
    new import_obsidian2.Notice(`\u2705\u300A${file.basename}\u300B\u6761\u6B3E\u5DF2\u7531 DeepSeek \u7CBE\u8BFB\u5B8C\u6210\u5E76\u81EA\u52A8\u4FDD\u5B58\uFF01`, 6e3);
  }
};
var BaodanAiSettingTab = class extends import_obsidian2.PluginSettingTab {
  plugin;
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "\u{1F6E1}\uFE0F \u4FDD\u5355 AI \u52A9\u624B (DeepSeek) \u8BBE\u7F6E" });
    new import_obsidian2.Setting(containerEl).setName("DeepSeek API Key").setDesc("\u8C03\u7528 DeepSeek \u5927\u6A21\u578B\u8FDB\u884C\u6761\u6B3E\u7CBE\u8BFB\u4E0E\u667A\u80FD\u8FFD\u95EE\u7684\u79D8\u94A5\u3002").addText((text) => {
      text.inputEl.type = "password";
      text.setPlaceholder("sk-...").setValue(this.plugin.settings.aiApiKey).onChange(async (value) => {
        this.plugin.settings.aiApiKey = value.trim();
        await this.plugin.saveSettings();
      });
    });
    new import_obsidian2.Setting(containerEl).setName("API Base URL").setDesc("DeepSeek \u517C\u5BB9\u63A5\u53E3\u5730\u5740\u3002").addText(
      (text) => text.setPlaceholder("https://api.deepseek.com/v1").setValue(this.plugin.settings.aiApiUrl).onChange(async (value) => {
        this.plugin.settings.aiApiUrl = value.trim();
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian2.Setting(containerEl).setName("AI \u6A21\u578B\u540D\u79F0").setDesc("\u9ED8\u8BA4\u4F7F\u7528 deepseek-chat\uFF08\u6027\u4EF7\u6BD4\u6781\u9AD8\u4E14\u4E13\u4E1A\u4E25\u8C28\uFF09\u3002").addText(
      (text) => text.setPlaceholder("deepseek-chat").setValue(this.plugin.settings.aiModel).onChange(async (value) => {
        this.plugin.settings.aiModel = value.trim();
        await this.plugin.saveSettings();
      })
    );
  }
};
