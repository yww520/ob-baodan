import {
  ItemView,
  WorkspaceLeaf,
  Notice,
  setIcon,
  TFile,
  MarkdownRenderer,
  Component,
  requestUrl
} from 'obsidian';
import type BaodanAiPlugin from './main';

export const VIEW_TYPE_BAODAN_CHAT = 'baodan-ai-chat-view';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export class BaodanChatView extends ItemView {
  plugin: BaodanAiPlugin;
  private currentFile: TFile | null = null;
  private messages: ChatMessage[] = [];
  private isThinking = false;

  private headerTitleEl!: HTMLElement;
  private messagesContainer!: HTMLElement;
  private inputEl!: HTMLTextAreaElement;
  private sendBtn!: HTMLButtonElement;
  private quickBar!: HTMLElement;

  constructor(leaf: WorkspaceLeaf, plugin: BaodanAiPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE_BAODAN_CHAT;
  }

  getDisplayText(): string {
    return '保单 AI 智能追问';
  }

  getIcon(): string {
    return 'message-circle';
  }

  async onOpen() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.addClass('baodan-chat-container');

    // 1. 顶部 Header
    const headerEl = containerEl.createDiv({ cls: 'baodan-chat-header' });
    const titleBox = headerEl.createDiv({ cls: 'baodan-chat-title-box' });
    const botIcon = titleBox.createSpan({ cls: 'baodan-chat-icon' });
    setIcon(botIcon, 'bot');

    this.headerTitleEl = titleBox.createSpan({
      cls: 'baodan-chat-title-text',
      text: '请在主窗口打开一份保单笔记'
    });

    const actions = headerEl.createDiv({ cls: 'baodan-chat-actions' });

    // 保存到笔记按钮
    const saveBtn = actions.createEl('button', {
      cls: 'baodan-icon-btn',
      attr: { title: '📌 将当前问答保存至保单笔记末尾' }
    });
    setIcon(saveBtn, 'save');
    saveBtn.onclick = async () => {
      await this.saveCurrentChatToNote();
    };

    // 清空历史按钮
    const clearBtn = actions.createEl('button', {
      cls: 'baodan-icon-btn',
      attr: { title: '🗑️ 清空当前对话' }
    });
    setIcon(clearBtn, 'trash-2');
    clearBtn.onclick = () => {
      this.messages = [];
      this.renderMessages();
      new Notice('已清空当前追问对话。');
    };

    // 2. 快捷追问胶囊区 (Quick Prompts)
    this.quickBar = containerEl.createDiv({ cls: 'baodan-quick-bar' });
    const quickPrompts = [
      '👶 小孩肺炎住院报销测算',
      '💊 自费药/特药能报销吗',
      '🏥 特需部/私立医院赔不赔',
      '🎖️ 理赔须提供哪些证明材料',
      '⏳ 既往症与30天等待期规定',
      '📞 门诊就医绿通怎么预约'
    ];

    for (const q of quickPrompts) {
      const pill = this.quickBar.createEl('button', {
        cls: 'baodan-quick-pill',
        text: q
      });
      pill.onclick = () => {
        let question = q;
        if (q.includes('小孩肺炎住院报销测算')) {
          question = '如果4岁小孩因急性肺炎住院花费8,000元，社保报销后剩余3,000元，这份保单能赔多少？请给出详细分段计算步骤。';
        } else if (q.includes('自费药/特药')) {
          question = '住院期间医生开具的医保目录外自费药、靶向药能否在此保单报销？报销比例和限制是什么？';
        } else if (q.includes('特需部/私立医院')) {
          question = '如果因紧急情况去了三甲医院特需部、国际医疗部或私立医院就诊，本保单是否承担保险责任？';
        } else if (q.includes('证明材料')) {
          question = '特别约定中针对出险理赔，必须提供哪些具体证明材料？如身份凭证或家属关系证明？';
        } else if (q.includes('既往症与30天等待期')) {
          question = '在保单生效后30天等待期内生病，保费是否退还？投保前已有的疾病（既往症）能否理赔？';
        } else if (q.includes('门诊就医绿通')) {
          question = '本保单自带的三甲医院门诊绿通预约服务如何申请？最快几个工作日能安排？包含哪些就诊费用？';
        }
        this.inputEl.value = question;
        this.handleSend();
      };
    }

    // 3. 消息流容器
    this.messagesContainer = containerEl.createDiv({ cls: 'baodan-messages-area' });

    // 4. 底部输入区
    const inputArea = containerEl.createDiv({ cls: 'baodan-input-area' });
    this.inputEl = inputArea.createEl('textarea', {
      cls: 'baodan-chat-textarea',
      attr: { placeholder: '输入你想追问的具体理赔问题（按 Enter 发送，Shift+Enter 换行）...' }
    });

    this.inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    const bottomRow = inputArea.createDiv({ cls: 'baodan-input-bottom' });
    const hintText = bottomRow.createSpan({
      cls: 'baodan-input-hint',
      text: '🤖 DeepSeek 保单专家在线'
    });

    this.sendBtn = bottomRow.createEl('button', {
      cls: 'baodan-send-btn',
      text: '🚀 发送追问'
    });
    this.sendBtn.onclick = () => this.handleSend();

    // 自动捕获当前活动保单笔记
    this.detectActivePolicy();

    // 监听标签页切换
    this.registerEvent(
      this.app.workspace.on('active-leaf-change', () => {
        this.detectActivePolicy();
      })
    );
  }

  detectActivePolicy(file?: TFile) {
    const activeFile = file || this.app.workspace.getActiveFile();
    if (activeFile && activeFile.path.endsWith('.md')) {
      if (this.currentFile?.path !== activeFile.path) {
        this.currentFile = activeFile;
        this.headerTitleEl.setText(`🛡️ 正在研读：${activeFile.basename}`);
        this.messages = [];
        this.messages.push({
          role: 'assistant',
          content: `您好！我是您的 **保单理赔 AI 顾问**。\n\n当前已载入《**${activeFile.basename}**》的全部条款与特别约定。您可以点击上方的快捷胶囊，或者在下方输入任何您关心的理赔计算、医院选择、自费药或免责问题！`,
          timestamp: Date.now()
        });
        this.renderMessages();
      }
    }
  }

  setTargetFile(file: TFile) {
    this.currentFile = file;
    this.headerTitleEl.setText(`🛡️ 正在研读：${file.basename}`);
    this.detectActivePolicy(file);
  }

  private renderMessages() {
    this.messagesContainer.empty();

    for (const msg of this.messages) {
      const bubbleEl = this.messagesContainer.createDiv({
        cls: `baodan-bubble ${msg.role === 'user' ? 'is-user' : 'is-assistant'}`
      });

      const metaRow = bubbleEl.createDiv({ cls: 'baodan-bubble-meta' });
      metaRow.setText(msg.role === 'user' ? '👤 您的追问' : '🤖 DeepSeek 理赔专家');

      const contentEl = bubbleEl.createDiv({ cls: 'baodan-bubble-content markdown-rendered' });
      // 渲染 Markdown
      void MarkdownRenderer.renderMarkdown(
        msg.content,
        contentEl,
        this.currentFile?.path || '',
        new Component()
      );
    }

    if (this.isThinking) {
      const loadingBubble = this.messagesContainer.createDiv({
        cls: 'baodan-bubble is-assistant is-loading'
      });
      loadingBubble.createDiv({ cls: 'baodan-bubble-meta', text: '🤖 DeepSeek 理赔专家' });
      const textEl = loadingBubble.createDiv({ cls: 'baodan-bubble-content' });
      textEl.setText('⏳ 正在翻阅保单合同与核保规则，组织权威解答...');
    }

    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  private async handleSend() {
    const question = this.inputEl.value.trim();
    if (!question || this.isThinking) return;

    if (!this.currentFile) {
      new Notice('请先在主窗口中打开一份保单笔记！');
      return;
    }

    this.inputEl.value = '';
    this.messages.push({ role: 'user', content: question, timestamp: Date.now() });
    this.isThinking = true;
    this.sendBtn.disabled = true;
    this.renderMessages();

    try {
      const answer = await this.queryDeepSeekForAnswer(question);
      this.messages.push({ role: 'assistant', content: answer, timestamp: Date.now() });
    } catch (err: any) {
      this.messages.push({
        role: 'assistant',
        content: `❌ 解答失败: ${err?.message || err}`,
        timestamp: Date.now()
      });
    } finally {
      this.isThinking = false;
      this.sendBtn.disabled = false;
      this.renderMessages();
    }
  }

  async queryDeepSeekForAnswer(question: string): Promise<string> {
    if (!this.currentFile) {
      throw new Error('未选定保单文件');
    }

    const settings = this.plugin.settings;
    if (!settings.aiApiKey) {
      throw new Error('未配置 DeepSeek API Key，请在插件设置中填写');
    }

    const fullContent = await this.app.vault.read(this.currentFile);
    // 截取前 20,000 字的核心参数、人员核验表、精读报告与条款摘录
    const policyContext = fullContent.slice(0, 20000);

    const systemPrompt = `你是一位精通中国大陆商业健康险与医疗险条款的资深精算与核保专家。
当前用户正在查阅一份真实的个人保险合同笔记，并对该保单的具体理赔规则、免责排雷、医院等级、报销金额测算或增值权益提出了追问。

你的职责：
1. 必须完全基于保单笔记提供的真实合同约定（免赔额、分段报销比例、有无社保就诊差异、给付限额、特殊限制与约定）进行精确计算与解答；
2. 若涉及费用报销测算，必须给出清晰的数学公式和分步骤计算过程；
3. 明确提示用户理赔时的红线（如医保结算、二级以上公立医院普通部、必备证件清单）；
4. 语言专业、客观、严谨，严禁胡编乱造不存在的责任。`;

    // 组装历史多轮会话上下文
    const recentMessages = this.messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content
    }));

    const userPrompt = `【当前研读保单】：${this.currentFile.basename}

【保单合同与核查核心上下文】：
${policyContext}

【用户具体追问问题】：
${question}`;

    const payload = {
      model: settings.aiModel || 'deepseek-chat',
      messages: [
        { role: 'system', content: systemPrompt },
        ...recentMessages.filter((m) => m.role !== 'system'),
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.2,
      max_tokens: 2500
    };

    const url = `${settings.aiApiUrl.replace(/\/+$/, '')}/chat/completions`;
    const response = await requestUrl({
      url,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
      } catch {}
      throw new Error(errMsg);
    }

    const data = JSON.parse(response.text);
    return data?.choices?.[0]?.message?.content?.trim() || 'DeepSeek 未返回有效解答。';
  }

  async saveCurrentChatToNote() {
    if (!this.currentFile) {
      new Notice('未选定保单文件！');
      return;
    }

    // 提取所有问答对
    const qaPairs: Array<{ q: string; a: string; time: string }> = [];
    for (let i = 0; i < this.messages.length - 1; i++) {
      if (this.messages[i].role === 'user' && this.messages[i + 1].role === 'assistant') {
        qaPairs.push({
          q: this.messages[i].content,
          a: this.messages[i + 1].content,
          time: new Date(this.messages[i + 1].timestamp).toLocaleString()
        });
      }
    }

    if (qaPairs.length === 0) {
      new Notice('当前没有可保存的追问对话！');
      return;
    }

    let appendMd = `\n\n### 💬 历史 AI 追问与答疑记录\n\n`;
    for (const pair of qaPairs) {
      appendMd += `> [!QUESTION] ❓ 追问：${pair.q.replace(/\n/g, ' ')}\n`;
      appendMd += `> **🤖 DeepSeek 专家解答** *(${pair.time})*：\n>\n`;
      const formattedAns = pair.a
        .split('\n')
        .map((l) => `> ${l}`)
        .join('\n');
      appendMd += `${formattedAns}\n\n`;
    }

    const fileContent = await this.app.vault.read(this.currentFile);
    let newContent = fileContent;

    // 检查是否已有问答章节
    const header = '### 💬 历史 AI 追问与答疑记录';
    if (newContent.includes(header)) {
      // 替换或追加
      newContent = newContent + '\n' + appendMd.replace(header + '\n\n', '');
    } else {
      newContent = newContent + appendMd;
    }

    await this.app.vault.modify(this.currentFile, newContent);
    new Notice(`✅ 已成功将 ${qaPairs.length} 条追问记录持久化保存至《${this.currentFile.basename}》！`);
  }
}
