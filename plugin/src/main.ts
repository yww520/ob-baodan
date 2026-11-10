import {
  Plugin,
  PluginSettingTab,
  Setting,
  Notice,
  requestUrl,
  TFile,
  MarkdownRenderer,
  Component,
  WorkspaceLeaf
} from 'obsidian';
import { BaodanChatView, VIEW_TYPE_BAODAN_CHAT } from './chat-view';

export interface BaodanAiSettings {
  aiApiUrl: string;
  aiApiKey: string;
  aiModel: string;
  temperature: number;
}

export const DEFAULT_SETTINGS: BaodanAiSettings = {
  aiApiUrl: 'https://api.deepseek.com/v1',
  aiApiKey: '',
  aiModel: 'deepseek-chat',
  temperature: 0.2
};

export default class BaodanAiPlugin extends Plugin {
  settings: BaodanAiSettings;

  async onload() {
    await this.loadSettings();

    // 1. 注册右侧 AI 追问聊天视图
    this.registerView(
      VIEW_TYPE_BAODAN_CHAT,
      (leaf: WorkspaceLeaf) => new BaodanChatView(leaf, this)
    );

    // 2. 添加左侧侧边栏快捷功能按钮 (Ribbon Icon)
    this.addRibbonIcon('message-square', '保单 AI: 打开智能追问与答疑面板', async () => {
      const activeFile = this.app.workspace.getActiveFile();
      await this.openChatView(activeFile || undefined);
    });

    // 3. 注册命令面板快捷指令 (Cmd + P)
    this.addCommand({
      id: 'baodan-ai-open-chat',
      name: '打开保单智能追问对话面板 (Chat)',
      checkCallback: (checking: boolean) => {
        const activeFile = this.app.workspace.getActiveFile();
        if (checking) return !!(activeFile && activeFile.path.endsWith('.md'));
        this.openChatView(activeFile || undefined);
      }
    });

    this.addCommand({
      id: 'baodan-ai-open-dashboard',
      name: '打开全家保单多维统计与可视化大盘 (Dashboard)',
      callback: async () => {
        const file = this.app.vault.getAbstractFileByPath('00_看板中心/📈 全家保单多维数据统计大盘.md');
        if (file instanceof TFile) {
          await this.app.workspace.getLeaf(false).openFile(file);
        } else {
          new Notice('未找到统计大盘文件');
        }
      }
    });

    this.addCommand({
      id: 'baodan-ai-analyze-current',
      name: '执行 DeepSeek 条款深度精读与理赔排雷',
      checkCallback: (checking: boolean) => {
        const activeFile = this.app.workspace.getActiveFile();
        const isValid = activeFile && activeFile.path.endsWith('.md');
        if (checking) return !!isValid;
        if (isValid) {
          this.runAiAnalysis(activeFile);
        }
      }
    });

    // 4. 注册保单笔记内的一键 AI 解读交互卡片代码块 ```baodan-ai
    this.registerMarkdownCodeBlockProcessor('baodan-ai', (source, el, ctx) => {
      el.empty();
      const container = el.createDiv({ cls: 'baodan-ai-box' });

      // 顶部标题
      const header = container.createDiv({ cls: 'baodan-ai-header' });
      header.innerHTML = `<span class="baodan-ai-icon">🤖</span> <strong>DeepSeek 保单 AI 助手与智能问答</strong>`;

      // 按钮操作行
      const btnRow = container.createDiv({ cls: 'baodan-ai-btn-row' });

      const reanalyzeBtn = btnRow.createEl('button', {
        text: '⚡ 一键调用 DeepSeek 重新深度精读',
        cls: 'baodan-ai-btn'
      });

      const openSideChatBtn = btnRow.createEl('button', {
        text: '🖥️ 展开右侧追问侧边栏',
        cls: 'baodan-ai-btn baodan-btn-secondary'
      });

      openSideChatBtn.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
        if (file instanceof TFile) {
          await this.openChatView(file);
        } else {
          await this.openChatView();
        }
      };

      const statusEl = container.createDiv({ cls: 'baodan-ai-status' });
      statusEl.setText('💡 支持直接在下方输入框向 DeepSeek 追问免赔测算、自费药报销、特需部限制等具体问题：');

      reanalyzeBtn.onclick = async () => {
        reanalyzeBtn.disabled = true;
        reanalyzeBtn.setText('⏳ DeepSeek 正在深度梳理条款中，请稍候...');
        statusEl.setText('正在连接 DeepSeek 云端大模型，提取免赔额、分段报销比、等待期及单证清单...');

        try {
          const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
          if (file instanceof TFile) {
            await this.runAiAnalysis(file);
            reanalyzeBtn.setText('🔄 重新执行 DeepSeek 条款精读');
            reanalyzeBtn.disabled = false;
            statusEl.setText(`✅ 条款深度精读已于 ${new Date().toLocaleTimeString()} 完成更新！结果呈现在下方。`);
          } else {
            throw new Error('未找到当前保单笔记文件');
          }
        } catch (err: any) {
          reanalyzeBtn.disabled = false;
          reanalyzeBtn.setText('❌ 分析失败，点击重试');
          statusEl.setText(`错误: ${err?.message || err}`);
        }
      };

      // 5. 笔记内置追问交互组件
      const qaSection = container.createDiv({ cls: 'baodan-inline-qa-box' });
      const qaTitle = qaSection.createDiv({ cls: 'baodan-qa-title' });
      qaTitle.innerHTML = `<strong>💬 保单智能追问：</strong> <span class="baodan-qa-sub">结合当前保单真实条款，分步骤计算与排雷</span>`;

      // 快捷追问胶囊
      const quickBar = qaSection.createDiv({ cls: 'baodan-quick-bar' });
      const quickQuestions = [
        '👶 小孩肺炎住院花8000能赔多少？',
        '💊 医保外自费药能报销吗？',
        '🏥 特需部/私立医院赔不赔？',
        '🎖️ 优待证与家属关系证明要求？',
        '⏳ 30天等待期内生病退保费吗？'
      ];

      for (const q of quickQuestions) {
        const pill = quickBar.createEl('button', {
          cls: 'baodan-quick-pill',
          text: q
        });
        pill.onclick = () => {
          inputEl.value = q;
          triggerInlineAsk();
        };
      }

      // 输入框与提交按钮行
      const inputRow = qaSection.createDiv({ cls: 'baodan-qa-input-row' });
      const inputEl = inputRow.createEl('textarea', {
        cls: 'baodan-qa-input',
        attr: {
          placeholder: '例如：孩子因意外骨折在二级公立医院花费5000元，社保未报销，本单能赔多少？',
          rows: '2'
        }
      });

      const askBtn = inputRow.createEl('button', {
        cls: 'baodan-ai-btn baodan-ask-btn',
        text: '🚀 立即追问'
      });

      // 结果展示区
      const resultArea = qaSection.createDiv({ cls: 'baodan-qa-result', attr: { style: 'display: none;' } });
      const resultHeader = resultArea.createDiv({ cls: 'baodan-result-header' });
      resultHeader.innerHTML = `<span>🤖 <strong>DeepSeek 专家解答：</strong></span>`;

      const saveToNoteBtn = resultHeader.createEl('button', {
        cls: 'baodan-save-inline-btn',
        text: '📌 保存此问答至保单笔记末尾'
      });

      const answerContent = resultArea.createDiv({ cls: 'baodan-answer-content markdown-rendered' });

      let lastQuestion = '';
      let lastAnswer = '';

      const triggerInlineAsk = async () => {
        const qText = inputEl.value.trim();
        if (!qText) return;

        askBtn.disabled = true;
        askBtn.setText('⏳ 思考中...');
        resultArea.style.display = 'block';
        answerContent.setText('⏳ DeepSeek 正在基于保单合同条款进行逻辑演算与排雷解答...');

        try {
          const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
          if (!(file instanceof TFile)) {
            throw new Error('未定位到保单笔记文件');
          }

          const answer = await this.queryDeepSeekFollowUp(file, qText);
          lastQuestion = qText;
          lastAnswer = answer;

          answerContent.empty();
          void MarkdownRenderer.renderMarkdown(
            answer,
            answerContent,
            file.path,
            new Component()
          );

          askBtn.disabled = false;
          askBtn.setText('🚀 立即追问');
        } catch (err: any) {
          askBtn.disabled = false;
          askBtn.setText('🚀 立即追问');
          answerContent.setText(`❌ 追问失败: ${err?.message || err}`);
        }
      };

      askBtn.onclick = () => triggerInlineAsk();

      inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          triggerInlineAsk();
        }
      });

      saveToNoteBtn.onclick = async () => {
        if (!lastQuestion || !lastAnswer) return;
        const file = this.app.vault.getAbstractFileByPath(ctx.sourcePath);
        if (file instanceof TFile) {
          await this.appendQAToFile(file, lastQuestion, lastAnswer);
          saveToNoteBtn.setText('✅ 已保存到笔记末尾');
          saveToNoteBtn.disabled = true;
        }
      };
    });

    // 6. 注册设置面板
    this.addSettingTab(new BaodanAiSettingTab(this.app, this));
  }

  async openChatView(file?: TFile) {
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
      const view = leaf.view as BaodanChatView;
      if (view && typeof view.setTargetFile === 'function') {
        const target = file || this.app.workspace.getActiveFile() || undefined;
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

  async queryDeepSeekFollowUp(file: TFile, question: string): Promise<string> {
    if (!this.settings.aiApiKey) {
      throw new Error('未配置 DeepSeek API Key');
    }

    const fullContent = await this.app.vault.read(file);
    const policyContext = fullContent.slice(0, 20000);

    const systemPrompt = `你是一位精通中国商业健康险与医疗险条款的资深精算与核保专家。
当前用户正在查阅一份真实的个人保险合同笔记，并对该保单的具体理赔规则、免责排雷、医院等级、报销金额测算或增值权益提出了追问。

你的职责：
1. 必须完全基于保单笔记提供的真实合同约定（免赔额、分段报销比例、有无社保就诊差异、给付限额、特殊限制与约定）进行精确计算与解答；
2. 若涉及费用报销测算，必须给出清晰的数学公式和分步骤计算过程；
3. 明确提示用户理赔时的红线（如医保结算、二级以上公立医院普通部、必备证件清单）；
4. 语言专业、客观、严谨，严禁胡编乱造不存在的责任。`;

    const userPrompt = `【当前研读保单】：${file.basename}

【保单合同与核查核心上下文】：
${policyContext}

【用户具体追问问题】：
${question}`;

    const payload = {
      model: this.settings.aiModel || 'deepseek-chat',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.2,
      max_tokens: 2500
    };

    const url = `${this.settings.aiApiUrl.replace(/\/+$/, '')}/chat/completions`;
    const response = await requestUrl({
      url,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
      } catch {}
      throw new Error(errMsg);
    }

    const data = JSON.parse(response.text);
    return data?.choices?.[0]?.message?.content?.trim() || 'DeepSeek 未返回有效解答。';
  }

  async appendQAToFile(file: TFile, question: string, answer: string) {
    const timeStr = new Date().toLocaleString();
    let appendMd = `\n\n### 💬 历史 AI 追问与答疑记录\n\n`;
    appendMd += `> [!QUESTION] ❓ 追问：${question.replace(/\n/g, ' ')}\n`;
    appendMd += `> **🤖 DeepSeek 专家解答** *(${timeStr})*：\n>\n`;
    const formattedAns = answer
      .split('\n')
      .map((l) => `> ${l}`)
      .join('\n');
    appendMd += `${formattedAns}\n\n`;

    const content = await this.app.vault.read(file);
    const header = '### 💬 历史 AI 追问与答疑记录';
    let newContent = content;

    if (newContent.includes(header)) {
      newContent = newContent + '\n' + appendMd.replace(header + '\n\n', '');
    } else {
      newContent = newContent + appendMd;
    }

    await this.app.vault.modify(file, newContent);
    new Notice(`✅ 已成功将追问记录保存至《${file.basename}》笔记末尾！`);
  }

  async runAiAnalysis(file: TFile) {
    if (!this.settings.aiApiKey) {
      new Notice('❌ 未配置 DeepSeek API Key，请在插件设置中填写。');
      throw new Error('未配置 DeepSeek API Key');
    }

    new Notice(`⏳ 正在对《${file.basename}》执行 DeepSeek 条款深度精读...`, 5000);

    const content = await this.app.vault.read(file);
    const clauseContext = content.slice(0, 25000);

    const systemPrompt = `你是一位资深专业的保险理赔精算与核保专家。
当前你需要深度梳理一份已经完成本地脱敏的真实个人保险保单。
请严格基于保单提供的真实合同条款输出结构化的 Markdown 报告，严禁编造不存在的责任。

输出结构必须包含：
1. 🛡️ 核心保障范围与赔付标准（用表格呈现：各项责任保额、免赔额、有无社保就诊结算比例差异、赔付上限）
2. ⚠️ 免除责任与暗坑排查（明确指出哪些情况不赔、既往症要求、就医公立医院等级限制、特需部/私立是否支持）
3. ⏰ 关键时间点与理赔材料清单（等待期天数、理赔报案时效限制、出险后必须准备的证明材料）
4. 💳 缴费、续保与增值权益（交费方式、是否保证续保、包含哪些特药/绿通等增值服务及申请途径）
5. 🎯 一句话理赔极简口诀（用通俗口语总结：在什么情况下，去什么医院，准备什么资料，能赔多少钱）`;

    const userPrompt = `【保单笔记名称】：${file.basename}\n\n【脱敏保单及条款核心】：\n${clauseContext}`;

    const url = `${this.settings.aiApiUrl.replace(/\/+$/, '')}/chat/completions`;
    const payload = {
      model: this.settings.aiModel || 'deepseek-chat',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      temperature: this.settings.temperature || 0.2,
      max_tokens: 4000
    };

    const response = await requestUrl({
      url,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
      } catch {}
      new Notice(`❌ DeepSeek 请求失败: ${errMsg}`);
      throw new Error(`AI 请求失败 (${errMsg})`);
    }

    const data = JSON.parse(response.text);
    const aiReport = data?.choices?.[0]?.message?.content?.trim();
    if (!aiReport) {
      throw new Error('DeepSeek 未返回有效内容');
    }

    const aiSectionHeader = '## 🤖 2. 大模型条款深度梳理（DeepSeek 智能精读）';
    const nextSectionHeader = '## 📑 3. 完整保单条款与附件存档';

    const newAiBlock = `${aiSectionHeader}

\`\`\`baodan-ai
button: true
\`\`\`

> [!SUCCESS] 🤖 DeepSeek AI 专家深度条款与理赔梳理报告
> *(生成时间：${new Date().toLocaleString()} ｜ 模型：${this.settings.aiModel})*

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
      const nextHr = rest.indexOf('\n---\n');
      if (nextHr !== -1) {
        newContent = content.slice(0, startIdx) + newAiBlock + rest.slice(nextHr + 5);
      } else {
        newContent = content.slice(0, startIdx) + newAiBlock;
      }
    } else {
      newContent = content + '\n\n' + newAiBlock;
    }

    await this.app.vault.modify(file, newContent);
    new Notice(`✅《${file.basename}》条款已由 DeepSeek 精读完成并自动保存！`, 6000);
  }
}

class BaodanAiSettingTab extends PluginSettingTab {
  plugin: BaodanAiPlugin;

  constructor(app: any, plugin: BaodanAiPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: '🛡️ 保单 AI 助手 (DeepSeek) 设置' });

    new Setting(containerEl)
      .setName('DeepSeek API Key')
      .setDesc('调用 DeepSeek 大模型进行条款精读与智能追问的秘钥。')
      .addText((text) => {
        text.inputEl.type = 'password';
        text
          .setPlaceholder('sk-...')
          .setValue(this.plugin.settings.aiApiKey)
          .onChange(async (value) => {
            this.plugin.settings.aiApiKey = value.trim();
            await this.plugin.saveSettings();
          });
      });

    new Setting(containerEl)
      .setName('API Base URL')
      .setDesc('DeepSeek 兼容接口地址。')
      .addText((text) =>
        text
          .setPlaceholder('https://api.deepseek.com/v1')
          .setValue(this.plugin.settings.aiApiUrl)
          .onChange(async (value) => {
            this.plugin.settings.aiApiUrl = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('AI 模型名称')
      .setDesc('默认使用 deepseek-chat（性价比极高且专业严谨）。')
      .addText((text) =>
        text
          .setPlaceholder('deepseek-chat')
          .setValue(this.plugin.settings.aiModel)
          .onChange(async (value) => {
            this.plugin.settings.aiModel = value.trim();
            await this.plugin.saveSettings();
          })
      );
  }
}
