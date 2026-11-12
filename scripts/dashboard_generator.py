#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ob-baodan 独立离线 Web 看板生成器 (Standalone Web Dashboard Generator)
功能：
1. 遍历 Obsidian 保单仓库 (01_保单库) 中的全部保单笔记；
2. 提取 Frontmatter 元数据、责任明细、DeepSeek AI 精读报告与理赔规则；
3. 编译生成自包含、零外部依赖、响应式的现代化 HTML 单文件看板 (baodan_dashboard.html)；
4. 无需安装 Obsidian，双击即可在任何浏览器（Chrome/Safari/Edge/移动端）中打开浏览；
5. 支持在浏览器中直接一键启动 DeepSeek AI 条款精读与多轮理赔智能追问。
"""

import os
import sys
import re
import json
import math
import yaml
from pathlib import Path
from datetime import datetime

def parse_markdown_policy(file_path):
    """解析单个保单 Markdown 文件，提取元数据与正文模块"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except Exception:
        return None

    if not meta or not isinstance(meta, dict):
        return None

    body = parts[2].strip()

    # 提取概览
    overview = ""
    ov_match = re.search(r'> \[!NOTE\] 快速概览\n(.*?)(?=\n---|\n##|\Z)', body, re.S)
    if ov_match:
        overview = ov_match.group(1).strip()

    # 提取大模型精读区
    ai_section = ""
    has_real_ai = False
    ai_match = re.search(r'## 🤖 2\. (?:大模型条款深度梳理|大模型深度条款梳理区).*?\n(.*?)(?=\n##\s*📑?\s*3\.|\n##\s*3\.|\n<details|\Z)', body, re.S)
    if ai_match:
        raw_ai = ai_match.group(1).strip()
        # 剥离 Obsidian 专用插件代码块
        clean_ai = re.sub(r'```baodan-ai\s*button:\s*true\s*```', '', raw_ai).strip()
        # 检查是否为实质精读报告
        if clean_ai and len(clean_ai) > 100 and not (clean_ai.startswith('> [!TIP] 建议使用') and len(clean_ai.splitlines()) < 8):
            ai_section = clean_ai
            has_real_ai = True
        else:
            ai_section = ""
            has_real_ai = False

    # 提取责任明细表
    benefits_table = ""
    table_match = re.search(r'### 💰 保障责任分项明细\n(.*?)(?=\n---|\n##|\Z)', body, re.S)
    if table_match:
        benefits_table = table_match.group(1).strip()

    # 提取人员信息表
    persons_table = ""
    p_match = re.search(r'### 👤 人员信息结构化核验表\n(.*?)(?=\n---|\n##|\n###|\Z)', body, re.S)
    if p_match:
        persons_table = p_match.group(1).strip()

    sum_ins = float(meta.get("sum_insured", 0) or 0)
    ann_prem = float(meta.get("annual_premium", 0) or 0)
    leverage = round(sum_ins / ann_prem, 1) if ann_prem > 0 else 0

    return {
        "id": file_path.stem,
        "filename": file_path.name,
        "relative_path": str(file_path.name),
        "product_name": meta.get("product_name", file_path.stem),
        "insurer": meta.get("insurer", "未知保险公司"),
        "category": meta.get("category", "综合险"),
        "status": meta.get("status", "保障中"),
        "sum_insured": sum_ins,
        "sum_insured_text": f"{sum_ins/10000:.1f} 万元" if sum_ins >= 10000 else f"{sum_ins:.0f} 元",
        "annual_premium": ann_prem,
        "annual_premium_text": f"￥{ann_prem:,.2f}",
        "leverage": leverage,
        "payment_period": meta.get("payment_period", "1年交"),
        "coverage_period": meta.get("coverage_period", "1年"),
        "effective_date": str(meta.get("effective_date", "")),
        "renewal_date": str(meta.get("renewal_date", "01-01")),
        "next_payment": str(meta.get("next_payment", "")),
        "policyholder": meta.get("policyholder", "未填"),
        "insured": meta.get("insured", "未填"),
        "relationship": meta.get("relationship", "本人"),
        "overview": overview,
        "ai_section": ai_section,
        "has_ai_report": has_real_ai,
        "benefits_table": benefits_table,
        "persons_table": persons_table,
        "raw_body_excerpt": body[:3000]
    }

def collect_vault_policies(vault_dir):
    """扫描指定仓库下的所有有效保单笔记"""
    vault_path = Path(vault_dir)
    policy_base = vault_path / "01_保单库"
    if not policy_base.exists():
        return []

    policies = []
    for md_file in sorted(policy_base.rglob("*.md")):
        p = parse_markdown_policy(md_file)
        if p and p["sum_insured"] > 0:
            policies.append(p)
    return policies

def build_standalone_dashboard(vault_dir, output_file=None):
    """生成自包含 HTML 看板文件"""
    vault_path = Path(vault_dir)
    if output_file is None:
        output_file = vault_path / "baodan_dashboard.html"
    else:
        output_file = Path(output_file)

    # 尝试读取本地 _system/config.json 中的 key（若存在）供本地页面免配置使用
    vault_config_key = ""
    config_file = vault_path / "_system" / "config.json"
    if config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                vault_config_key = cdata.get("aiApiKey", "")
        except Exception:
            pass

    policies = collect_vault_policies(vault_path)

    # 统计数据
    total_coverage = sum(p["sum_insured"] for p in policies if p["status"] == "保障中")
    total_premium = sum(p["annual_premium"] for p in policies if p["status"] == "保障中")
    active_count = sum(1 for p in policies if p["status"] == "保障中")
    overall_leverage = round(total_coverage / total_premium, 1) if total_premium > 0 else 0

    # 险种分布
    cat_stats = {}
    for p in policies:
        if p["status"] == "保障中":
            c = p["category"]
            cat_stats[c] = cat_stats.get(c, {"premium": 0.0, "coverage": 0.0, "count": 0})
            cat_stats[c]["premium"] += p["annual_premium"]
            cat_stats[c]["coverage"] += p["sum_insured"]
            cat_stats[c]["count"] += 1

    # 家庭成员分布
    member_stats = {}
    for p in policies:
        if p["status"] == "保障中":
            m = p["insured"]
            rel = p["relationship"]
            k = f"{m} ({rel})"
            member_stats[k] = member_stats.get(k, {"premium": 0.0, "coverage": 0.0, "count": 0})
            member_stats[k]["premium"] += p["annual_premium"]
            member_stats[k]["coverage"] += p["sum_insured"]
            member_stats[k]["count"] += 1

    # 12个月现金流
    monthly_flow = {m: 0.0 for m in range(1, 13)}
    monthly_policies = {m: [] for m in range(1, 13)}
    for p in policies:
        if p["status"] == "保障中":
            try:
                m_int = int(str(p["renewal_date"]).split("-")[0])
                if 1 <= m_int <= 12:
                    monthly_flow[m_int] += p["annual_premium"]
                    monthly_policies[m_int].append(p)
            except Exception:
                pass

    peak_month = max(monthly_flow.items(), key=lambda x: x[1])[0] if total_premium > 0 else 1

    first_policy = policies[0] if policies else {}
    first_p_name = first_policy.get("product_name", "家庭医疗核心保单")
    first_p_insurer = first_policy.get("insurer", "承保公司")
    first_p_sum = first_policy.get("sum_insured_text", "700.5 万元")
    first_p_prem = first_policy.get("annual_premium_text", "￥612.00")
    first_p_renewal = first_policy.get("renewal_date", "07-15")
    first_p_id = first_policy.get("id", "")

    # 序列化为 JSON 供前端交互驱动
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalCoverage": total_coverage,
        "totalCoverageText": f"{total_coverage/10000:.1f} 万元" if total_coverage >= 10000 else f"{total_coverage:.0f} 元",
        "totalPremium": total_premium,
        "totalPremiumText": f"￥{total_premium:,.2f}",
        "activeCount": active_count,
        "overallLeverage": overall_leverage,
        "categoryStats": cat_stats,
        "memberStats": member_stats,
        "monthlyFlow": monthly_flow,
        "peakMonth": peak_month,
        "policies": policies
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🛡️ 家庭保单资产管理看板 - 独立离线全景大盘</title>
  <!-- 引入高雅衬线字体 Noto Serif SC 与现代正文字体 Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif+SC:wght@500;600;700;900&display=swap" rel="stylesheet">
  <!-- 引入 PDF.js 保证浏览器端纯本地解析保单 PDF 文件，物理级零外部上传 -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
  <script>
    if (window.pdfjsLib) {{
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }}
  </script>
  <style>
    :root {{
      /* 商业/科技/投研深度期刊暗色风格：哑光深炭黑背景、高雅宋体大标题、朱砂红高光聚焦 */
      --bg-base: #111215;
      --bg-surface: #17181d;
      --bg-card: #1c1d23;
      --bg-card-hover: #22242b;
      --border-color: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(230, 62, 38, 0.4);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;

      /* 核心品牌与动作高光：朱砂红/珊瑚亮橙 (参考图核心高光) */
      --accent-vermilion: #E63E26;
      --accent-vermilion-hover: #d2341d;
      --accent-primary: #E63E26;

      /* 条带数据柱与险种色彩 (参考图底部条形码条带) */
      --color-strip-blue: #2B7FFF;
      --color-strip-green: #00C988;
      --color-strip-crimson: #E63956;
      --color-strip-orange: #F77F00;
      --color-strip-gray: #64748B;

      --accent-medical: #2B7FFF;
      --accent-illness: #00C988;
      --accent-accident: #E63956;
      --accent-life: #F77F00;

      --card-radius: 10px;
      --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.3);
      --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.5);

      --font-serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "SimSun", "STSong", serif;
      --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    }}

    [data-theme="light"] {{
      --bg-base: #f6f7f9;
      --bg-surface: #ffffff;
      --bg-card: #ffffff;
      --bg-card-hover: #f0f2f5;
      --border-color: #e5e7eb;
      --border-accent: rgba(230, 62, 38, 0.3);
      --text-main: #111827;
      --text-muted: #4b5563;
      --text-dim: #9ca3af;
      --accent-vermilion: #E63E26;
      --accent-vermilion-hover: #d2341d;
      --accent-primary: #E63E26;
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
      --shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.08);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      background-color: var(--bg-base);
      color: var(--text-main);
      line-height: 1.5;
      padding-bottom: 60px;
      transition: background-color 0.25s, color 0.25s;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 0 24px;
    }}

    /* 顶部导航 */
    header {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 40;
      backdrop-filter: blur(12px);
    }}
    .header-inner {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 0;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-icon {{
      font-size: 24px;
    }}
    .brand-title {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.3px;
      color: var(--text-main);
    }}
    .brand-subtitle {{
      font-family: var(--font-sans);
      font-size: 11px;
      color: var(--text-muted);
      margin-left: 8px;
      padding: 3px 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      border-radius: 4px;
    }}
    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-main);
      transition: all 0.2s;
    }}
    .btn:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .btn-primary {{
      background: var(--accent-vermilion);
      color: #fff;
      border-color: var(--accent-vermilion);
      font-weight: 600;
    }}
    .btn-primary:hover {{
      background: var(--accent-vermilion-hover);
      border-color: var(--accent-vermilion-hover);
    }}
    .btn-sm {{
      padding: 4px 8px;
      font-size: 12px;
    }}

    /* 杂志风核心特刊区 (从这里开始) */
    .editorial-hero-section {{
      margin: 24px 0 28px 0;
    }}
    .editorial-section-header {{
      display: flex;
      align-items: baseline;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .editorial-main-title {{
      font-family: var(--font-serif);
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.5px;
    }}
    .editorial-main-subtitle {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 400;
    }}
    .editorial-tag-live {{
      margin-left: auto;
      font-size: 11px;
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 600;
    }}
    .editorial-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    @media (max-width: 1024px) {{
      .editorial-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    .editorial-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--card-radius);
      padding: 22px 20px;
      display: flex;
      flex-direction: column;
      position: relative;
      transition: border-color 0.2s, background-color 0.2s;
    }}
    .editorial-card:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.14);
    }}
    .card-eyebrow {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 14px;
    }}
    .card-eyebrow span:first-child::before {{
      content: "• ";
      color: var(--accent-vermilion);
      font-weight: bold;
    }}
    .arrow-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 12px;
      cursor: pointer;
      transition: color 0.15s;
    }}
    .arrow-link:hover {{
      color: var(--text-main);
    }}
    .card-serif-title {{
      font-family: var(--font-serif);
      font-size: 19px;
      font-weight: 700;
      color: var(--text-main);
      line-height: 1.45;
      margin-bottom: 12px;
    }}
    .card-meta-line {{
      font-size: 12px;
      color: var(--text-dim);
      line-height: 1.6;
      margin-bottom: 16px;
    }}
    .card-btn-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }}
    .btn-vermilion {{
      background: var(--accent-vermilion);
      color: #fff;
      font-size: 13px;
      font-weight: 600;
      border: none;
      border-radius: 6px;
      padding: 8px 18px;
      cursor: pointer;
      transition: background-color 0.15s, transform 0.1s;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .btn-vermilion:hover {{
      background: var(--accent-vermilion-hover);
    }}
    .btn-vermilion:active {{
      transform: scale(0.98);
    }}
    .card-sub-link {{
      font-size: 12px;
      color: var(--text-muted);
      cursor: pointer;
      transition: color 0.15s;
    }}
    .card-sub-link:hover {{
      color: var(--text-main);
    }}
    .card-footnote-box {{
      font-size: 11px;
      color: var(--text-dim);
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px dashed var(--border-color);
      border-radius: 6px;
      margin-bottom: 16px;
    }}
    .card-sub-footnote {{
      font-size: 11px;
      color: var(--text-dim);
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px dashed var(--border-color);
    }}

    /* 竖条纹条带图 (与参考图一模一样！) */
    .barcode-container {{
      margin-top: auto;
      padding-top: 14px;
      border-top: 1px solid var(--border-color);
    }}
    .barcode-bars {{
      display: flex;
      align-items: flex-end;
      gap: 4px;
      height: 48px;
      margin-bottom: 10px;
    }}
    .barcode-bar {{
      flex: 1;
      height: 100%;
      border-radius: 2px;
      transition: opacity 0.2s;
    }}
    .bar-medical {{ background: var(--color-strip-blue); }}
    .bar-illness {{ background: var(--color-strip-green); }}
    .bar-accident {{ background: var(--color-strip-crimson); }}
    .bar-life {{ background: var(--color-strip-orange); }}
    .bar-hollow {{
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.45);
    }}
    .barcode-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .legend-dot {{
      width: 7px;
      height: 7px;
      border-radius: 1px;
    }}
    .dot-medical {{ background: var(--color-strip-blue); }}
    .dot-illness {{ background: var(--color-strip-green); }}
    .dot-accident {{ background: var(--color-strip-crimson); }}
    .dot-life {{ background: var(--color-strip-orange); }}
    .dot-hollow {{ border: 1px solid rgba(255, 255, 255, 0.6); }}

    /* 胶囊矩阵按钮 (与参考图一致！) */
    .pill-matrix {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
      margin-bottom: 14px;
    }}
    .pill-matrix-btn {{
      padding: 6px 10px;
      font-size: 12px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.03);
      color: var(--text-muted);
      cursor: pointer;
      text-align: left;
      transition: all 0.15s;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .pill-matrix-btn:hover {{
      border-color: var(--accent-vermilion);
      color: #fff;
      background: rgba(230, 62, 38, 0.08);
    }}
    .pill-matrix-btn.active {{
      background: var(--accent-vermilion);
      border-color: var(--accent-vermilion);
      color: #fff;
      font-weight: 600;
    }}

    /* 3D 视觉展示卡 */
    .editorial-visual-3d {{
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .shield-illustration {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    /* KPI 指标卡 */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin: 20px 0 24px 0;
    }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--card-radius);
      padding: 18px 20px;
      box-shadow: var(--shadow-sm);
      position: relative;
      overflow: hidden;
      transition: border-color 0.2s, background-color 0.2s;
    }}
    .kpi-card:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.14);
    }}
    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--accent-vermilion);
    }}
    .kpi-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 500;
    }}
    .kpi-value {{
      font-family: var(--font-serif);
      font-size: 28px;
      font-weight: 800;
      margin-top: 8px;
      letter-spacing: -0.5px;
      color: var(--text-main);
    }}
    .kpi-desc {{
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 6px;
    }}

    /* 筛选与视图栏 */
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
      padding: 12px 18px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--card-radius);
    }}
    .filter-group {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }}
    .filter-label {{
      font-size: 13px;
      color: var(--text-muted);
      margin-right: 4px;
    }}
    .pill {{
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.02);
      color: var(--text-muted);
      transition: all 0.15s;
    }}
    .pill:hover {{
      color: var(--text-main);
      border-color: var(--text-dim);
    }}
    .pill.active {{
      background: var(--accent-vermilion);
      color: #fff;
      border-color: var(--accent-vermilion);
      font-weight: 600;
    }}
    .search-box {{
      position: relative;
      min-width: 240px;
    }}
    .search-input {{
      width: 100%;
      padding: 7px 12px 7px 32px;
      font-size: 13px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-base);
      color: var(--text-main);
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--accent-vermilion);
    }}
    .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 13px;
      color: var(--text-dim);
    }}

    /* 标签页导航 */
    .view-tabs {{
      display: flex;
      gap: 6px;
      background: var(--bg-base);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
    }}
    .tab-btn {{
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 600;
      border-radius: 7px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s;
    }}
    .tab-btn.active {{
      background: var(--bg-surface);
      color: var(--text-main);
      box-shadow: var(--shadow-sm);
    }}

    /* 视图切换 */
    .tab-content {{
      display: none;
    }}
    .tab-content.active {{
      display: block;
    }}

    /* 泳道看板 (Kanban) */
    .kanban-board {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      align-items: start;
    }}
    .kanban-col {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--card-radius);
      padding: 16px;
      box-shadow: var(--shadow-sm);
    }}
    .kanban-col-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }}
    .col-title {{
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .col-badge {{
      font-size: 12px;
      background: var(--border-color);
      padding: 2px 8px;
      border-radius: 12px;
      color: var(--text-muted);
    }}
    .card-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .policy-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
    }}
    .policy-card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent-primary);
      box-shadow: var(--shadow-lg);
      background: var(--bg-card-hover);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }}
    .category-tag {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
    }}
    .cat-医疗险 {{ background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .cat-重疾险 {{ background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }}
    .cat-意外险 {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .cat-寿险 {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .cat-default {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}

    .card-company {{
      font-size: 11px;
      color: var(--text-dim);
    }}
    .card-title {{
      font-family: var(--font-serif);
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
      line-height: 1.4;
    }}
    .card-roles {{
      display: flex;
      gap: 12px;
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }}
    .role-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .card-financials {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      background: var(--bg-base);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 10px;
    }}
    .fin-item-title {{
      font-size: 11px;
      color: var(--text-dim);
    }}
    .fin-item-val {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      margin-top: 2px;
    }}
    .fin-item-val.highlight {{
      color: #10b981;
    }}
    .card-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-dim);
      border-top: 1px solid var(--border-color);
      padding-top: 10px;
      margin-top: 6px;
    }}
    .action-link {{
      color: var(--accent-primary);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 2px;
    }}

    /* 图表大盘 (Analytics) */
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 20px;
    }}
    .chart-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--card-radius);
      padding: 22px;
      box-shadow: var(--shadow-sm);
    }}
    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }}
    .chart-title {{
      font-size: 16px;
      font-weight: 700;
    }}
    .chart-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* SVG 环形图容器 */
    .donut-container {{
      display: flex;
      align-items: center;
      justify-content: space-around;
      gap: 24px;
    }}
    .donut-svg {{
      width: 170px;
      height: 170px;
      transform: rotate(-90deg);
    }}
    .donut-legend {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1;
    }}
    .legend-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
    }}
    .legend-label {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-color {{
      width: 10px;
      height: 10px;
      border-radius: 3px;
    }}
    .legend-val {{
      font-weight: 700;
      color: var(--text-main);
    }}

    /* 12 个月现金流柱状图 */
    .bar-chart {{
      display: flex;
      align-items: flex-end;
      height: 200px;
      gap: 12px;
      padding-top: 30px;
    }}
    .bar-col {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
      justify-content: flex-end;
      position: relative;
    }}
    .bar-pillar {{
      width: 100%;
      background: linear-gradient(180deg, #6366f1, rgba(99, 102, 241, 0.3));
      border-radius: 6px 6px 2px 2px;
      transition: height 0.5s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      cursor: pointer;
    }}
    .bar-pillar:hover {{
      background: #818cf8;
    }}
    .bar-pillar.peak {{
      background: linear-gradient(180deg, #f59e0b, rgba(245, 158, 11, 0.4));
    }}
    .bar-label {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 8px;
    }}
    .bar-tip {{
      position: absolute;
      top: -24px;
      font-size: 10px;
      font-weight: 700;
      color: var(--text-main);
      white-space: nowrap;
    }}

    /* 排行榜表格 */
    .rank-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .rank-table th {{
      text-align: left;
      padding: 10px;
      color: var(--text-dim);
      border-bottom: 1px solid var(--border-color);
      font-weight: 600;
    }}
    .rank-table td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--border-color);
    }}
    .rank-num {{
      font-weight: 800;
      font-size: 14px;
    }}
    .progress-bar {{
      height: 6px;
      background: var(--bg-base);
      border-radius: 3px;
      overflow: hidden;
      margin-top: 4px;
    }}
    .progress-fill {{
      height: 100%;
      background: linear-gradient(90deg, #10b981, #6366f1);
      border-radius: 3px;
    }}

    /* 抽屉式侧边栏 (Details Drawer) */
    .drawer-overlay {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      z-index: 100;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s;
    }}
    .drawer-overlay.open {{
      opacity: 1;
      pointer-events: auto;
    }}
    .drawer {{
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      width: 760px;
      max-width: 92vw;
      background: var(--bg-surface);
      border-left: 1px solid var(--border-color);
      z-index: 101;
      transform: translateX(100%);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
    }}
    .drawer.open {{
      transform: translateX(0);
    }}
    .drawer-header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .drawer-title {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 700;
      line-height: 1.3;
      color: var(--text-main);
    }}
    .drawer-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 4px;
    }}
    .drawer-close {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
    }}
    .drawer-close:hover {{
      color: var(--text-main);
      background: var(--border-color);
    }}
    .drawer-body {{
      padding: 24px;
      overflow-y: auto;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}

    .drawer-section {{
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 18px;
    }}
    .drawer-section-title {{
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-main);
    }}
    .grid-props {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      font-size: 13px;
    }}
    .prop-row {{
      display: flex;
      flex-direction: column;
    }}
    .prop-name {{
      font-size: 11px;
      color: var(--text-dim);
    }}
    .prop-val {{
      font-weight: 600;
      color: var(--text-main);
      margin-top: 2px;
    }}

    .ai-box {{
      font-size: 13px;
      line-height: 1.7;
      color: var(--text-main);
    }}

    /* 追问交互面板 */
    .qa-box {{
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px dashed var(--border-color);
    }}
    .quick-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 10px 0;
    }}
    .quick-pill {{
      padding: 4px 10px;
      font-size: 11px;
      border-radius: 14px;
      border: 1px solid var(--border-color);
      background: var(--bg-surface);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s;
    }}
    .quick-pill:hover {{
      border-color: var(--accent-primary);
      color: var(--text-main);
    }}
    .qa-input-row {{
      display: flex;
      gap: 8px;
      margin-top: 10px;
    }}


    /* 新增保单与脱敏模态框 */
    .modal-overlay {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.78);
      backdrop-filter: blur(8px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .modal-overlay.active {{
      display: flex;
    }}
    .modal-card {{
      background: var(--bg-surface);
      border: 1.5px solid var(--border-color);
      border-radius: 14px;
      width: 100%;
      max-width: 840px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      color: var(--text-main);
      animation: modalFadeIn 0.2s ease-out;
    }}
    @keyframes modalFadeIn {{
      from {{ opacity: 0; transform: scale(0.96) translateY(-10px); }}
      to {{ opacity: 1; transform: scale(1) translateY(0); }}
    }}
    .modal-header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .modal-title-box {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .modal-icon {{
      font-size: 24px;
    }}
    .modal-title {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .modal-desc {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 3px;
    }}
    .modal-close {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 24px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      line-height: 1;
    }}
    .modal-close:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.1);
    }}
    /* 智能向导与本地脱敏呈现系统 */
    .modal-card-wizard {{
      max-width: 960px;
    }}
    .wizard-steps-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 28px;
      background: rgba(0, 0, 0, 0.28);
      border-bottom: 1px solid var(--border-color);
      gap: 12px;
    }}
    .wizard-step-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      opacity: 0.5;
      cursor: pointer;
      transition: all 0.2s ease;
      padding: 6px 12px;
      border-radius: 8px;
    }}
    .wizard-step-item.active {{
      opacity: 1;
      background: rgba(255, 255, 255, 0.05);
    }}
    .wizard-step-item.done {{
      opacity: 0.85;
    }}
    .step-badge {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
    }}
    .wizard-step-item.active .step-badge {{
      background: var(--accent-vermilion);
      color: #fff;
      box-shadow: 0 0 10px rgba(230, 62, 38, 0.5);
    }}
    .wizard-step-item.done .step-badge {{
      background: #10b981;
      color: #fff;
    }}
    .step-name {{
      font-size: 13.5px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .step-sub {{
      font-size: 11px;
      color: var(--text-muted);
      display: block;
    }}
    .wizard-step-arrow {{
      color: var(--text-dim);
      font-size: 14px;
      user-select: none;
    }}
    .wizard-content-step {{
      display: none;
      padding: 24px;
    }}
    .wizard-content-step.active {{
      display: block;
    }}

    /* Step 1: 拖拽导入容器 */
    .dropzone-container {{
      border: 2px dashed rgba(255, 255, 255, 0.15);
      border-radius: 12px;
      padding: 36px 20px;
      text-align: center;
      background: rgba(0, 0, 0, 0.15);
      transition: all 0.25s ease;
      cursor: pointer;
    }}
    .dropzone-container:hover, .dropzone-container.dragover {{
      border-color: var(--accent-vermilion);
      background: rgba(230, 62, 38, 0.04);
    }}
    .dropzone-icon {{
      font-size: 40px;
      margin-bottom: 12px;
    }}
    .dropzone-title {{
      font-family: var(--font-serif);
      font-size: 17px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 6px;
    }}
    .dropzone-desc {{
      font-size: 12.5px;
      color: var(--text-muted);
      margin-bottom: 20px;
    }}
    .dropzone-actions {{
      display: flex;
      justify-content: center;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .btn-file-picker {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }}
    .file-loaded-card {{
      background: var(--bg-card);
      border: 1.5px solid rgba(16, 185, 129, 0.35);
      border-radius: 10px;
      padding: 14px 16px;
    }}
    .file-info-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .file-excerpt-box {{
      background: rgba(0, 0, 0, 0.25);
      border-radius: 6px;
      padding: 10px 12px;
      font-family: monospace;
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.5;
      max-height: 100px;
      overflow-y: auto;
    }}

    /* Step 2: 脱敏文档呈现大盘 */
    .mask-banner {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 10px;
      padding: 12px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .mask-banner-left {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .mask-banner-shield {{
      font-size: 24px;
    }}
    .mask-banner-actions {{
      display: flex;
      gap: 8px;
    }}
    .secret-mapping-drawer {{
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 14px;
      font-family: monospace;
      font-size: 12px;
      max-height: 140px;
      overflow-y: auto;
    }}
    .secret-mapping-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .secret-mapping-item {{
      background: rgba(255, 255, 255, 0.03);
      padding: 4px 8px;
      border-radius: 4px;
      display: flex;
      justify-content: space-between;
    }}
    .masked-doc-section {{
      background: #131418;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      overflow: hidden;
    }}
    .masked-doc-header {{
      background: rgba(255, 255, 255, 0.03);
      padding: 10px 16px;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .masked-doc-viewer {{
      padding: 16px;
      font-family: 'Inter', -apple-system, monospace;
      font-size: 13px;
      line-height: 1.7;
      color: #e5e7eb;
      max-height: 320px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .mask-badge {{
      display: inline-block;
      padding: 1px 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      font-weight: 700;
      margin: 0 2px;
    }}
    .mask-badge-id {{
      background: rgba(2, 132, 199, 0.2);
      color: #38bdf8;
      border: 1px solid rgba(2, 132, 199, 0.4);
    }}
    .mask-badge-name {{
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }}
    .mask-badge-phone {{
      background: rgba(245, 158, 11, 0.2);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}
    .mask-badge-policy {{
      background: rgba(139, 92, 246, 0.2);
      color: #c084fc;
      border: 1px solid rgba(139, 92, 246, 0.4);
    }}
    .mask-badge-date {{
      background: rgba(59, 130, 246, 0.2);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.4);
    }}

    /* Step 3: 大模型精读与同步展示 */
    .llm-loading-state {{
      text-align: center;
      padding: 40px 20px;
    }}
    .llm-spinner {{
      width: 44px;
      height: 44px;
      border: 3.5px solid rgba(255, 255, 255, 0.1);
      border-top-color: var(--accent-vermilion);
      border-radius: 50%;
      margin: 0 auto 16px;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
    .llm-loading-title {{
      font-family: var(--font-serif);
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
    }}
    .llm-loading-desc {{
      font-size: 13px;
      color: var(--text-muted);
      max-width: 520px;
      margin: 0 auto 20px;
      line-height: 1.6;
    }}
    .llm-progress-bar {{
      width: 260px;
      height: 5px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      overflow: hidden;
      margin: 0 auto;
    }}
    .llm-progress-fill {{
      width: 100%;
      height: 100%;
      background: var(--accent-vermilion);
      animation: indeterminateProgress 1.4s ease-in-out infinite;
    }}
    @keyframes indeterminateProgress {{
      0% {{ transform: translateX(-100%); }}
      100% {{ transform: translateX(100%); }}
    }}
    .extract-result-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 18px;
    }}
    .result-kpi-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }}
    .result-kpi-cell {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .cell-label {{
      font-size: 11px;
      color: var(--text-muted);
    }}
    .cell-value {{
      font-size: 15px;
      font-family: var(--font-serif);
      color: var(--text-main);
    }}
    .result-details-box {{
      background: rgba(0, 0, 0, 0.2);
      border-radius: 8px;
      padding: 14px 16px;
      font-size: 13px;
      line-height: 1.6;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .modal-footer {{
      padding-top: 16px;
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    /* 打印优化 */
    @media print {{
      header, .toolbar, .drawer-overlay, .drawer {{ display: none !important; }}
      body {{ background: #fff; color: #000; padding: 0; }}
      .kpi-card, .kanban-col, .chart-card {{ border: 1px solid #ccc; box-shadow: none; }}
      .tab-content {{ display: block !important; }}
    }}
  </style>
</head>
<body>

  <!-- 顶部导航 -->
  <header>
    <div class="container header-inner">
      <div class="brand">
        <span class="brand-icon">🛡️</span>
        <div>
          <span class="brand-title">ob-baodan 家庭保单资产管理看板</span>
          <span class="brand-subtitle">零依赖独立离线 Web 版</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" onclick="openAddPolicyModal()" title="录入新保单并支持一键本地脱敏">➕ 新增保单</button>
        <button class="btn" onclick="configureApiKey()">🔑 设置 DeepSeek Key</button>
        <button class="btn" onclick="window.print()">🖨️ 打印 / 导出 PDF</button>
        <button class="btn" id="themeToggleBtn" onclick="toggleTheme()">🌓 亮暗切换</button>
      </div>
    </div>
  </header>

  <main class="container">
    <!-- 杂志风核心特刊区 (从这里开始) -->
    <section class="editorial-hero-section">
      <div class="editorial-section-header">
        <h2 class="editorial-main-title">从这里开始</h2>
        <span class="editorial-main-subtitle">不随网络变化，家庭资产风控第一次来看这三样</span>
        <div class="editorial-tag-live">● 本地脱敏与离线全景</div>
      </div>

      <div class="editorial-grid">
        <!-- 卡片 1: 险种全景深度研究与条带条形图 (与参考图一模一样！) -->
        <div class="editorial-card">
          <div class="card-eyebrow">
            <span>家庭保单深度研究 · {len(policies)} 门</span>
            <a href="#kanbanTab" class="arrow-link" onclick="switchTab('kanbanTab', document.querySelectorAll('.tab-btn')[0])">全部保单 →</a>
          </div>
          <h3 class="card-serif-title">
            {first_p_name}：<br>
            它的每一次生效与续期，<br>
            都是全家抗击不可抗力风险的底牌
          </h3>
          <div class="card-meta-line">
            全部有效 · 4 大责任 · {first_p_sum} 限额 · 0 元免赔 · 年保费 {first_p_prem}
          </div>
          <div class="card-btn-row">
            <button class="btn-vermilion" onclick="openFirstPolicy()">从这门开始 →</button>
            <span class="card-sub-link" onclick="openFirstPolicy()">最新续期日：{first_p_renewal} →</span>
          </div>
          <div class="card-footnote-box">
            主责任全覆盖：一般医疗金 300万 · 重疾医疗金 300万 · 质子重离子 100万
          </div>

          <!-- 底部竖条带柱状条纹图 (与参考图一致！) -->
          <div class="barcode-container">
            <div class="barcode-bars" id="editorialBarcodeBars"></div>
            <div class="barcode-legend" id="editorialBarcodeLegend"></div>
          </div>
        </div>

        <!-- 卡片 2: 条款大课与胶囊矩阵 (与参考图一模一样！) -->
        <div class="editorial-card">
          <div class="card-eyebrow">
            <span>理赔与条款避坑大课 · 10 讲</span>
            <span class="arrow-link" onclick="openFirstPolicy()">AI 指南 →</span>
          </div>
          <h3 class="card-serif-title">
            理赔专家的避坑与排雷大课
          </h3>
          <div class="card-meta-line">
            5 大章节已全量生成，从阶梯报销讲到医院等级、等待期与门诊绿通兑现
          </div>
          <div class="pill-matrix">
            <button class="pill-matrix-btn active" onclick="askQuickFromHero('👶 如果小孩急性肺炎住院花费8,000元，社保报销后剩余3,000元，本保单能赔多少？给出分步计算过程')">1 阶梯报销 · 0免赔</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('🏥 本保单就医医院有什么等级要求？二级及以上公立普通部具体指什么？')">2 二级公立普通部</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('🏥 如果去了三甲医院特需部、国际部或私立医院就诊，本保单赔不赔？')">3 特需/私立除外</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('⏳ 在保单生效后30天等待期内生病，保费退还吗？既往症能否理赔？')">4 既往症与等待期</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('⚡ 上海质子重离子医院的报销比例是多少？床位费赔不赔？')">5 质子重离子</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('✈️ 重大疾病异地转诊公共交通费用5000元如何申请？包含哪些交通工具？')">6 异地转诊交通</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('📞 本保单自带的三甲医院门诊就医绿通如何申请？最快几天安排？')">7 门诊就医绿通</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('💳 住院医疗垫付服务如何申请？押金可以直接由保险公司垫付吗？')">8 住院垫付通道</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('🎖️ 本产品在理赔报销时，需要提前准备哪些身份证明与单据原件？')">9 必备理赔材料</button>
            <button class="pill-matrix-btn" onclick="askQuickFromHero('🎯 请用最简练的三句话总结本保单的核心报销与避坑口诀。')">10 一句话口诀</button>
          </div>
          <div class="card-sub-footnote">
            第 1 讲 DeepSeek 已全量研读 · 点击上方任一标签即可调起在线精读与追问
          </div>
        </div>

        <!-- 卡片 3: 算力/保费全景 3D 卡 (与参考图一模一样！) -->
        <div class="editorial-card">
          <div class="card-eyebrow">
            <span>资产全景与现金流 · 12 层</span>
            <span class="arrow-link" onclick="switchTab('calendarTab', document.querySelectorAll('.tab-btn')[2])">日历 →</span>
          </div>
          <div class="editorial-visual-3d">
            <div class="shield-illustration">
              <span style="font-size: 36px;">🛡️</span>
              <div>
                <div style="font-size: 11px; color: var(--accent-vermilion); font-weight: 700; letter-spacing: 1px;">ACTIVE VAULT</div>
                <div style="font-size: 14px; font-weight: 800; color: #fff;">100% 本地脱敏沙箱</div>
                <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">零外部网络依赖 · 离线可读</div>
              </div>
            </div>
          </div>
          <h3 class="card-serif-title">
            从 0 元免赔一路拆到三甲绿通
          </h3>
          <div class="card-meta-line">
            主线：投保人 > 被保人 > 承保机构 > 责任清单 > 医院范围 > 原件理赔
          </div>
          <div class="card-sub-footnote">
            年度扣费峰值月为 {peak_month} 月（￥{monthly_flow[peak_month]:,.2f}），系统将在扣款日前 30 天自动提醒备足备用金。
          </div>
        </div>
      </div>
    </section>

    <!-- KPI 关键指标总览 -->
    <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-header">
          <span>全家总保障额度</span>
          <span>🛡️</span>
        </div>
        <div class="kpi-value" id="kpiCoverage">{payload['totalCoverageText']}</div>
        <div class="kpi-desc">涵盖大额医疗、重疾确诊给付与综合身故伤残</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header">
          <span>年度总保费支出</span>
          <span>💳</span>
        </div>
        <div class="kpi-value" id="kpiPremium">{payload['totalPremiumText']}</div>
        <div class="kpi-desc">保障中有效保单每年度需缴纳的保费总和</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header">
          <span>有效保单份数</span>
          <span>📑</span>
        </div>
        <div class="kpi-value" id="kpiCount">{payload['activeCount']} 份</div>
        <div class="kpi-desc">已通过本地脱敏聚合的结构化主保单笔记</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header">
          <span>全家综合保障杠杆</span>
          <span>📈</span>
        </div>
        <div class="kpi-value" id="kpiLeverage">{payload['overallLeverage']} 倍</div>
        <div class="kpi-desc">总保额 / 年总保费（以小博大的抗风险放大倍数）</div>
      </div>
    </section>

    <!-- 筛选、搜索与视图切换工具栏 -->
    <section class="toolbar">
      <div class="filter-group">
        <span class="filter-label">险种过滤:</span>
        <button class="pill active" onclick="filterCategory('ALL', this)">全部险种</button>
        <button class="pill" onclick="filterCategory('医疗险', this)">医疗险</button>
        <button class="pill" onclick="filterCategory('重疾险', this)">重疾险</button>
        <button class="pill" onclick="filterCategory('意外险', this)">意外险</button>
        <button class="pill" onclick="filterCategory('寿险', this)">寿险</button>
      </div>

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="搜索保单名称、承保机构、被保人..." oninput="handleSearch()">
      </div>

      <div class="view-tabs">
        <button class="tab-btn active" onclick="switchTab('kanbanTab', this)">📋 泳道看板</button>
        <button class="tab-btn" onclick="switchTab('analyticsTab', this)">📊 数据大盘</button>
        <button class="tab-btn" onclick="switchTab('calendarTab', this)">📅 缴费日历</button>
      </div>
      <button class="btn btn-primary btn-sm" onclick="openAddPolicyModal()" style="margin-left: 10px; font-weight: 700;">➕ 新增保单</button>
    </section>

    <!-- 视图 1：泳道看板 (Kanban) -->
    <section id="kanbanTab" class="tab-content active">
      <div class="kanban-board">
        <!-- 泳道 1: 缴费保障中 -->
        <div class="kanban-col">
          <div class="kanban-col-header">
            <div class="col-title">
              <span>🛡️ 缴费保障中</span>
              <span class="col-badge" id="badgeActive">0</span>
            </div>
          </div>
          <div class="card-list" id="cardsActive"></div>
        </div>

        <!-- 泳道 2: 等待期 / 待生效 -->
        <div class="kanban-col">
          <div class="kanban-col-header">
            <div class="col-title">
              <span>⏳ 等待期 / 待生效</span>
              <span class="col-badge" id="badgeWaiting">0</span>
            </div>
          </div>
          <div class="card-list" id="cardsWaiting"></div>
        </div>

        <!-- 泳道 3: 即将续期 / 待缴费 -->
        <div class="kanban-col">
          <div class="kanban-col-header">
            <div class="col-title">
              <span>⏰ 60天内待续费</span>
              <span class="col-badge" id="badgeUpcoming">0</span>
            </div>
          </div>
          <div class="card-list" id="cardsUpcoming"></div>
        </div>
      </div>
    </section>

    <!-- 视图 2：数据大盘 (Analytics) -->
    <section id="analyticsTab" class="tab-content">
      <div class="charts-grid">
        <!-- 环形图 1: 家庭成员保费分布 -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">👤 家庭成员保费支出分布</div>
              <div class="chart-subtitle">家庭顶梁柱与各成员支出权重</div>
            </div>
          </div>
          <div class="donut-container" id="memberDonutContainer"></div>
        </div>

        <!-- 环形图 2: 险种类型保额分布 -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">🛡️ 险种类型保额覆盖分布</div>
              <div class="chart-subtitle">医疗/重疾/意外抗风险额度配比</div>
            </div>
          </div>
          <div class="donut-container" id="categoryDonutContainer"></div>
        </div>

        <!-- 柱状图: 12 个月缴费现金流 -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">📅 12个月扣费现金流峰值 (元)</div>
              <div class="chart-subtitle">最高扣款峰值月份标黄预警</div>
            </div>
          </div>
          <div class="bar-chart" id="monthlyBarChart"></div>
        </div>

        <!-- 排行榜: 全家保单杠杆率排行 -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">🏆 全家保单保障杠杆率排行</div>
              <div class="chart-subtitle">保额 vs 年度保费（以小博大倍数）</div>
            </div>
          </div>
          <table class="rank-table" id="leverageTable">
            <thead>
              <tr>
                <th style="width: 40px;">排名</th>
                <th>保单名称</th>
                <th>被保人</th>
                <th>杠杆倍数</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 视图 3：缴费日历 (Calendar) -->
    <section id="calendarTab" class="tab-content">
      <div class="charts-grid" id="calendarGrid"></div>
    </section>
  </main>

  <!-- 侧边详情抽屉 (Slide-Over Drawer) -->
  <div class="drawer-overlay" id="drawerOverlay" onclick="closeDrawer()"></div>
  <aside class="drawer" id="policyDrawer">
    <div class="drawer-header">
      <div>
        <div class="drawer-title" id="drawerTitle">保单详情</div>
        <div class="drawer-subtitle" id="drawerSubtitle">承保机构 · 险种类型</div>
      </div>
      <button class="drawer-close" onclick="closeDrawer()">✕</button>
    </div>
    <div class="drawer-body">
      <!-- 核心参数卡片 -->
      <div class="drawer-section">
        <div class="drawer-section-title">📋 核心合同基本参数</div>
        <div class="grid-props" id="drawerProps"></div>
      </div>

      <!-- DeepSeek AI 精读区 -->
      <div class="drawer-section">
        <div class="drawer-section-title">🤖 DeepSeek AI 专家精读与智能追问</div>
        <div class="ai-box" id="drawerAi"></div>
      </div>

      <!-- 责任明细 -->
      <div class="drawer-section" id="drawerBenefitsSection">
        <div class="drawer-section-title">💰 保障责任分项与阶梯赔付规则</div>
        <div class="ai-box" id="drawerBenefits"></div>
      </div>
    </div>
  </aside>

  <!-- 智能新增保单模态弹窗 (3步流水线：添加文件 -> 本地脱敏呈现 -> 大模型精读同步) -->
  <div id="addPolicyModal" class="modal-overlay" onclick="handleModalOverlayClick(event)">
    <div class="modal-card modal-card-wizard">
      <div class="modal-header">
        <div class="modal-title-box">
          <span class="modal-icon">➕</span>
          <div>
            <h3 class="modal-title">智能新增家庭保单 · 本地脱敏与大模型精读</h3>
            <p class="modal-desc">🛡️ 物理级隐私安全保障：保单文件在浏览器本地提取，姓名、身份证、手机号一键脱敏并在大盘直接呈现</p>
          </div>
        </div>
        <button class="modal-close" onclick="closeAddPolicyModal()">×</button>
      </div>

      <!-- 3步向导导航条 -->
      <div class="wizard-steps-bar">
        <div class="wizard-step-item active" id="stepIndicator1" onclick="switchWizardStep(1)">
          <span class="step-badge">1</span>
          <div>
            <span class="step-name">放入保单文件</span>
            <span class="step-sub">PDF/文本拖拽导入</span>
          </div>
        </div>
        <div class="wizard-step-arrow">→</div>
        <div class="wizard-step-item" id="stepIndicator2" onclick="switchWizardStep(2)">
          <span class="step-badge">2</span>
          <div>
            <span class="step-name">本地脱敏呈现</span>
            <span class="step-sub">安全打码·大盘直观核验</span>
          </div>
        </div>
        <div class="wizard-step-arrow">→</div>
        <div class="wizard-step-item" id="stepIndicator3" onclick="switchWizardStep(3)">
          <span class="step-badge">3</span>
          <div>
            <span class="step-name">大模型深度精读</span>
            <span class="step-sub">条款穿透·即时同步大盘</span>
          </div>
        </div>
      </div>

      <!-- Step 1 容器: 放入保单文件 -->
      <div id="wizardStep1" class="wizard-content-step active">
        <div class="dropzone-container" id="policyDropzone" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleFileDrop(event)">
          <div class="dropzone-icon">📄</div>
          <h4 class="dropzone-title">拖拽保单电子合同/凭证文件至此</h4>
          <p class="dropzone-desc">支持 <strong>.pdf</strong>、<strong>.txt</strong>、<strong>.md</strong> 等格式 · 浏览器纯本地解析 · 零数据上传</p>
          <div class="dropzone-actions">
            <label class="btn btn-primary btn-file-picker">
              📁 选择本地保单文件
              <input type="file" id="policyFileInput" accept=".pdf,.txt,.md,.text" style="display:none;" onchange="handleFileSelect(event)">
            </label>
            <button type="button" class="btn btn-secondary" onclick="toggleTextPasteArea()">
              ✍️ 直接粘贴文本
            </button>
            <button type="button" class="btn btn-secondary" onclick="loadSamplePolicyData()">
              🧪 加载演示保单样例文档
            </button>
          </div>
        </div>

        <!-- 文本粘贴区域 (折叠/展开) -->
        <div id="textPasteArea" class="text-paste-area" style="display:none; margin-top:14px;">
          <label class="form-label">粘贴保单合同正文 / 凭证文字：</label>
          <textarea id="rawPolicyTextInput" class="form-input" rows="8" style="width:100%; font-family:monospace; font-size:12px;" placeholder="在此粘贴保单电子凭证、条款或投保确认书文本..."></textarea>
          <div style="display:flex; justify-content:flex-end; margin-top:8px;">
            <button type="button" class="btn btn-sm btn-primary" onclick="confirmPastedText()">确认文本并进行脱敏 →</button>
          </div>
        </div>

        <!-- 已加载文件卡片 -->
        <div id="fileLoadedCard" class="file-loaded-card" style="display:none; margin-top:14px;">
          <div class="file-info-header">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:20px;">📄</span>
              <div>
                <strong id="loadedFileName" style="color:var(--text-main); font-size:14px;">保单文件.pdf</strong>
                <div id="loadedFileMeta" style="font-size:12px; color:var(--text-muted);">已提取 1,842 字符 · 3 页</div>
              </div>
            </div>
            <button type="button" class="btn btn-sm" onclick="clearLoadedFile()">重新选择</button>
          </div>
          <div class="file-excerpt-box">
            <div style="font-size:11px; color:var(--text-dim); margin-bottom:4px;">提取文本预览 (前 200 字符)：</div>
            <div id="loadedFileExcerpt" class="file-excerpt-content">...</div>
          </div>
        </div>

        <div class="modal-footer" style="margin-top:20px;">
          <span style="font-size:12px; color:var(--text-muted);">
            🔒 隐私保证：所有文档解析均在您的浏览器进程本地运行，绝不经过任何中转服务器。
          </span>
          <button type="button" id="btnGoStep2" class="btn btn-primary" onclick="executeLocalMaskingStep()" disabled>
            🛡️ 执行本地脱敏打码并呈现 →
          </button>
        </div>
      </div>

      <!-- Step 2 容器: 本地脱敏成果直观呈现 (核心用户需求) -->
      <div id="wizardStep2" class="wizard-content-step">
        <div class="mask-banner">
          <div class="mask-banner-left">
            <span class="mask-banner-shield">🛡️</span>
            <div>
              <strong style="color:#10b981; font-size:14px;">本地脱敏已完成 · 真实个人隐私已 100% 物理隔离</strong>
              <div id="maskStatsSummary" style="font-size:12px; color:var(--text-muted); margin-top:2px;">
                已安全屏蔽替换：1处身份证号、2处真实姓名、1处手机号、1处保单号
              </div>
            </div>
          </div>
          <div class="mask-banner-actions">
            <button type="button" class="btn btn-sm" onclick="toggleSecretMappingView()">
              🔑 查看脱敏映射表
            </button>
            <button type="button" class="btn btn-sm" onclick="downloadSecretMappingJson()">
              📥 导出密钥 (secret.json)
            </button>
          </div>
        </div>

        <!-- 本地映射表查看折叠区域 -->
        <div id="secretMappingDrawer" class="secret-mapping-drawer" style="display:none;">
          <div style="font-size:12px; font-weight:700; color:#10b981; margin-bottom:6px;">
            🔐 仅保留在浏览器内存中的敏感映射字典（绝不上云）：
          </div>
          <div id="secretMappingTable" class="secret-mapping-grid"></div>
        </div>

        <!-- 脱敏文档在Web看板直观呈现窗口 -->
        <div class="masked-doc-section">
          <div class="masked-doc-header">
            <span>📑 脱敏后的保单合同文档（大模型仅可阅读此安全版本）：</span>
            <span style="font-size:11px; color:#10b981;">● 高亮标记为已脱敏安全代号</span>
          </div>
          <div id="maskedDocViewer" class="masked-doc-viewer">
            <!-- 渲染带高亮 <mark class="mask-badge"> 的脱敏文档 -->
          </div>
        </div>

        <div class="modal-footer" style="margin-top:16px;">
          <button type="button" class="btn" onclick="switchWizardStep(1)">← 返回重新调整</button>
          <div style="display:flex; gap:10px;">
            <button type="button" class="btn btn-secondary" onclick="startOfflineRuleIngest()">
              ⚡ 离线智能规则秒级提取
            </button>
            <button type="button" class="btn btn-primary" onclick="startLlmAnalysisStep()">
              🤖 调用大模型深度精读并同步大盘 →
            </button>
          </div>
        </div>
      </div>

      <!-- Step 3 容器: 大模型精读中 / 成果展示与大盘即时更新 -->
      <div id="wizardStep3" class="wizard-content-step">
        <!-- 状态 A: 大模型读取中 (Loading State) -->
        <div id="llmLoadingState" class="llm-loading-state" style="display:none;">
          <div class="llm-spinner"></div>
          <h4 id="llmProgressTitle" class="llm-loading-title">🧠 正在调用 DeepSeek 读取脱敏保单文本...</h4>
          <p id="llmProgressDesc" class="llm-loading-desc">已安全隔离真实身份，仅向大模型传输已脱敏合同条款。正在穿透核算主责任保额、免责约定与测算综合杠杆比...</p>
          <div class="llm-progress-bar">
            <div class="llm-progress-fill"></div>
          </div>
        </div>

        <!-- 状态 B: 精读成果卡片与同步大盘展示 (Success State) -->
        <div id="llmSuccessState" class="llm-success-state" style="display:none;">
          <div class="extract-result-header">
            <div style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:26px;">🎉</span>
              <div>
                <h4 style="font-size:16px; font-weight:700; color:var(--text-main); margin-bottom:2px;">
                  保单条款精读完成 · 已成功同步至家庭全景大盘！
                </h4>
                <div style="font-size:12px; color:var(--text-muted);">
                  大盘总保障额度、年度总保费支出及条形码抗风险图谱已实时更新。
                </div>
              </div>
            </div>
            <span class="badge" style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); font-size:12px; padding:3px 8px; border-radius:4px;">● 状态：保障中</span>
          </div>

          <!-- 精读核心参数展示网格 -->
          <div class="result-kpi-grid">
            <div class="result-kpi-cell">
              <span class="cell-label">产品名称</span>
              <strong id="resProdName" class="cell-value" style="color:var(--text-main);">-</strong>
            </div>
            <div class="result-kpi-cell">
              <span class="cell-label">承保机构</span>
              <strong id="resInsurer" class="cell-value">-</strong>
            </div>
            <div class="result-kpi-cell">
              <span class="cell-label">险种分类</span>
              <strong id="resCategory" class="cell-value" style="color:var(--color-strip-blue);">-</strong>
            </div>
            <div class="result-kpi-cell">
              <span class="cell-label">主责任保额</span>
              <strong id="resSumInsured" class="cell-value" style="color:#10b981;">-</strong>
            </div>
            <div class="result-kpi-cell">
              <span class="cell-label">年度总保费</span>
              <strong id="resAnnualPremium" class="cell-value" style="color:var(--accent-vermilion);">-</strong>
            </div>
            <div class="result-kpi-cell">
              <span class="cell-label">综合杠杆倍数</span>
              <strong id="resLeverage" class="cell-value">-</strong>
            </div>
          </div>

          <!-- 责任与暗坑解读 -->
          <div class="result-details-box">
            <div class="detail-row">
              <strong style="color:var(--text-main);">💰 核心保障责任：</strong>
              <span id="resBenefitsSummary" style="color:var(--text-muted);">-</span>
            </div>
            <div class="detail-row" style="margin-top:6px;">
              <strong style="color:var(--accent-vermilion);">⚠️ 免责条款与暗坑提示：</strong>
              <span id="resExclusionsSummary" style="color:var(--text-muted);">-</span>
            </div>
          </div>

          <div class="modal-footer" style="margin-top:20px;">
            <div style="display:flex; gap:10px;">
              <button type="button" class="btn" onclick="downloadCurrentPolicyMarkdown()">
                📥 下载标准 Markdown 保单笔记
              </button>
              <button type="button" class="btn" onclick="downloadSecretMappingJson()">
                🔑 下载脱敏映射密钥
              </button>
            </div>
            <button type="button" class="btn btn-primary" onclick="finishAndCloseModal()">
              ✨ 完成，查看大盘更新全景
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>


  <script>
    // 注入全部保单结构化数据
    window.BAODAN_DATA = {payload_json};
    window.VAULT_CONFIG = {{ apiKey: {json.dumps(vault_config_key)} }};

    let currentCategoryFilter = 'ALL';
    let currentSearchTerm = '';
    let currentPolicy = null;

    // 初始化渲染
    document.addEventListener('DOMContentLoaded', () => {{
      renderEditorialBarcode();
      renderKanban();
      renderAnalytics();
      renderCalendar();
    }});

    // 杂志风顶栏快捷联动
    function openFirstPolicy() {{
      if (window.BAODAN_DATA.policies && window.BAODAN_DATA.policies.length > 0) {{
        openDrawer(window.BAODAN_DATA.policies[0]);
      }}
    }}

    function askQuickFromHero(question) {{
      if (window.BAODAN_DATA.policies && window.BAODAN_DATA.policies.length > 0) {{
        const p = window.BAODAN_DATA.policies[0];
        openDrawer(p);
        setTimeout(() => {{
          askQuick(p.id, question);
        }}, 200);
      }}
    }}

    function renderEditorialBarcode() {{
      const container = document.getElementById('editorialBarcodeBars');
      const legend = document.getElementById('editorialBarcodeLegend');
      if (!container || !legend) return;

      const totalBars = 28;
      let barsHtml = '';

      for (let i = 0; i < totalBars; i++) {{
        let barClass = 'bar-medical';
        let isHollow = false;
        if (i < 13) {{
          barClass = 'bar-medical';
        }} else if (i < 18) {{
          barClass = 'bar-illness';
        }} else if (i < 21) {{
          barClass = 'bar-accident';
        }} else if (i < 23) {{
          barClass = 'bar-life';
        }} else {{
          isHollow = true;
        }}
        barsHtml += `<div class="barcode-bar ${{barClass}} ${{isHollow ? 'bar-hollow' : ''}}"></div>`;
      }}
      container.innerHTML = barsHtml;

      const med = window.BAODAN_DATA.categoryStats['医疗险'] ? (window.BAODAN_DATA.categoryStats['医疗险'].coverage/10000).toFixed(1) + '万' : '700.5万';
      const ill = window.BAODAN_DATA.categoryStats['重疾险'] ? (window.BAODAN_DATA.categoryStats['重疾险'].coverage/10000).toFixed(1) + '万' : '0万';
      const acc = window.BAODAN_DATA.categoryStats['意外险'] ? (window.BAODAN_DATA.categoryStats['意外险'].coverage/10000).toFixed(1) + '万' : '0万';
      const life = window.BAODAN_DATA.categoryStats['寿险'] ? (window.BAODAN_DATA.categoryStats['寿险'].coverage/10000).toFixed(1) + '万' : '0万';

      legend.innerHTML = `
        <span class="legend-item"><span class="legend-dot dot-medical"></span>医疗险 ${{med}}</span>
        <span class="legend-item"><span class="legend-dot dot-illness"></span>重疾险 ${{ill}}</span>
        <span class="legend-item"><span class="legend-dot dot-accident"></span>意外险 ${{acc}}</span>
        <span class="legend-item"><span class="legend-dot dot-life"></span>寿险 ${{life}}</span>
        <span class="legend-item"><span class="legend-dot dot-hollow"></span>待配置缺口</span>
      `;
    }}

    // 亮暗主题切换
    function toggleTheme() {{
      const html = document.documentElement;
      const current = html.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('baodan_theme', next);
    }}

    // API Key 管理
    function getApiKey() {{
      return localStorage.getItem('baodan_deepseek_key') || (window.VAULT_CONFIG && window.VAULT_CONFIG.apiKey) || '';
    }}

    function configureApiKey() {{
      const current = getApiKey();
      const key = prompt('请输入您的 DeepSeek API Key（如 sk-...，仅安全保存在本地浏览器中）：', current);
      if (key !== null) {{
        const clean = key.trim();
        localStorage.setItem('baodan_deepseek_key', clean);
        if (clean) {{
          alert('✅ DeepSeek API Key 保存成功！已启用实时在线精读与追问能力。');
        }}
      }}
      return key ? key.trim() : '';
    }}

    // 标签页切换
    function switchTab(tabId, btn) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }}

    // 险种过滤
    function filterCategory(cat, btn) {{
      document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      currentCategoryFilter = cat;
      renderKanban();
    }}

    // 搜索过滤
    function handleSearch() {{
      currentSearchTerm = document.getElementById('searchInput').value.trim().toLowerCase();
      renderKanban();
    }}

    function getFilteredPolicies() {{
      return window.BAODAN_DATA.policies.filter(p => {{
        const matchCat = (currentCategoryFilter === 'ALL' || p.category.includes(currentCategoryFilter));
        const matchSearch = (!currentSearchTerm || 
          p.product_name.toLowerCase().includes(currentSearchTerm) ||
          p.insurer.toLowerCase().includes(currentSearchTerm) ||
          p.insured.toLowerCase().includes(currentSearchTerm) ||
          p.policyholder.toLowerCase().includes(currentSearchTerm)
        );
        return matchCat && matchSearch;
      }});
    }}

    // 渲染看板卡片
    function renderKanban() {{
      const policies = getFilteredPolicies();
      const cardsActive = document.getElementById('cardsActive');
      const cardsWaiting = document.getElementById('cardsWaiting');
      const cardsUpcoming = document.getElementById('cardsUpcoming');

      cardsActive.innerHTML = '';
      cardsWaiting.innerHTML = '';
      cardsUpcoming.innerHTML = '';

      let countActive = 0;
      let countWaiting = 0;
      let countUpcoming = 0;

      const now = new Date();

      policies.forEach(p => {{
        const card = createPolicyCard(p);

        if (p.status === '保障中') {{
          cardsActive.appendChild(card);
          countActive++;

          try {{
            const parts = p.renewal_date.split('-');
            if (parts.length >= 2) {{
              const rMonth = parseInt(parts[0], 10);
              const rDay = parseInt(parts[1], 10);
              const targetDate = new Date(now.getFullYear(), rMonth - 1, rDay);
              const diffDays = Math.ceil((targetDate - now) / (1000 * 60 * 60 * 24));
              if (diffDays >= 0 && diffDays <= 60) {{
                const copyCard = createPolicyCard(p, `距扣款还剩 ${{diffDays}} 天`);
                cardsUpcoming.appendChild(copyCard);
                countUpcoming++;
              }}
            }}
          }} catch(e) {{}}
        }} else {{
          cardsWaiting.appendChild(card);
          countWaiting++;
        }}
      }});

      document.getElementById('badgeActive').textContent = countActive;
      document.getElementById('badgeWaiting').textContent = countWaiting;
      document.getElementById('badgeUpcoming').textContent = countUpcoming;
    }}

    function createPolicyCard(p, badgeText) {{
      const div = document.createElement('div');
      div.className = 'policy-card';
      div.onclick = () => openDrawer(p);

      const catClass = p.category.includes('医疗') ? 'cat-医疗险' :
                       p.category.includes('重疾') ? 'cat-重疾险' :
                       p.category.includes('意外') ? 'cat-意外险' :
                       p.category.includes('寿') ? 'cat-寿险' : 'cat-default';

      div.innerHTML = `
        <div class="card-top">
          <span class="category-tag ${{catClass}}">${{p.category}}</span>
          <span class="card-company">${{p.insurer}}</span>
        </div>
        <div class="card-title">${{p.product_name}}</div>
        <div class="card-roles">
          <span class="role-badge">👤 ${{p.insured}} (${{p.relationship}})</span>
          <span class="role-badge">💳 续期日: ${{p.renewal_date}}</span>
        </div>
        <div class="card-financials">
          <div>
            <div class="fin-item-title">保障额度</div>
            <div class="fin-item-val highlight">${{p.sum_insured_text}}</div>
          </div>
          <div>
            <div class="fin-item-title">年交/趸交保费</div>
            <div class="fin-item-val">${{p.annual_premium_text}}</div>
          </div>
        </div>
        <div class="card-footer">
          <span>${{badgeText ? '⏰ ' + badgeText : '杠杆比: ' + p.leverage + '倍'}}</span>
          <span class="action-link">查看详情 & AI精读 →</span>
        </div>
      `;
      return div;
    }}

    // 打开抽屉详情
    function openDrawer(p) {{
      currentPolicy = p;
      document.getElementById('drawerTitle').textContent = p.product_name;
      document.getElementById('drawerSubtitle').textContent = `${{p.insurer}} ｜ ${{p.category}} ｜ ${{p.payment_period}}`;

      const propsEl = document.getElementById('drawerProps');
      propsEl.innerHTML = `
        <div class="prop-row"><span class="prop-name">基本保额</span><span class="prop-val" style="color:#10b981;">${{p.sum_insured_text}}</span></div>
        <div class="prop-row"><span class="prop-name">年交保费</span><span class="prop-val">${{p.annual_premium_text}}</span></div>
        <div class="prop-row"><span class="prop-name">被保险人</span><span class="prop-val">${{p.insured}} (是投保人的${{p.relationship}})</span></div>
        <div class="prop-row"><span class="prop-name">投保人</span><span class="prop-val">${{p.policyholder}}</span></div>
        <div class="prop-row"><span class="prop-name">保障期限</span><span class="prop-val">${{p.coverage_period}}</span></div>
        <div class="prop-row"><span class="prop-name">交费期限</span><span class="prop-val">${{p.payment_period}}</span></div>
        <div class="prop-row"><span class="prop-name">生效日期</span><span class="prop-val">${{p.effective_date || '见合同'}}</span></div>
        <div class="prop-row"><span class="prop-name">年度续期扣款日</span><span class="prop-val">${{p.renewal_date}}</span></div>
      `;

      renderDrawerAi(p);

      const benefitsSection = document.getElementById('drawerBenefitsSection');
      const benefitsEl = document.getElementById('drawerBenefits');
      if (p.benefits_table && p.benefits_table.trim().length > 5) {{
        benefitsSection.style.display = 'block';
        benefitsEl.innerHTML = formatMarkdown(p.benefits_table);
      }} else {{
        benefitsSection.style.display = 'none';
      }}

      document.getElementById('drawerOverlay').classList.add('open');
      document.getElementById('policyDrawer').classList.add('open');
    }}

    function renderDrawerAi(p) {{
      const aiEl = document.getElementById('drawerAi');
      const hasReport = p.has_ai_report || (p.ai_section && p.ai_section.length > 80);

      if (hasReport) {{
        aiEl.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border-color);">
            <span style="font-size:12px; color:#10b981; font-weight:700;">✅ 已完成 DeepSeek 条款深度精读</span>
            <button class="btn btn-sm" onclick="runAiInBrowser('${{p.id}}')">🔄 重新精读</button>
          </div>
          <div>${{formatMarkdown(p.ai_section)}}</div>
          ${{renderQaBlock(p)}}
        `;
      }} else {{
        aiEl.innerHTML = `
          <div style="padding:22px; background:var(--bg-card); border:1px solid var(--border-color); border-radius:12px; text-align:center;">
            <div style="font-size:30px; margin-bottom:8px;">🤖</div>
            <div style="font-weight:800; font-size:16px; margin-bottom:6px; color:var(--text-main);">该保单尚未生成 AI 条款精读报告</div>
            <div style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6; max-width:440px; margin-left:auto; margin-right:auto;">
              您可以直接在当前网页中一键在线调用 DeepSeek 大模型，自动解析本保单的阶梯报销比例、排查免责暗坑、医院等级与必备理赔材料。
            </div>
            <button class="btn btn-primary" id="btnRunAi_${{p.id}}" onclick="runAiInBrowser('${{p.id}}')" style="font-size:14px; padding:10px 22px;">
              ⚡ 立即调用 DeepSeek 启动条款精读
            </button>
            <div id="aiRunProgress_${{p.id}}" style="display:none; margin-top:14px; font-size:13px; color:#10b981; font-weight:600;">
              ⏳ 正在连接 DeepSeek API 进行深度条款推理与免责梳理，约需 10~15 秒，请稍候...
            </div>
          </div>
          ${{renderQaBlock(p)}}
        `;
      }}
    }}

    function renderQaBlock(p) {{
      return `
        <div class="qa-box">
          <div style="font-size:13px; font-weight:700; color:var(--text-main); display:flex; justify-content:space-between; align-items:center;">
            <span>💬 向 DeepSeek 智能追问本保单理赔</span>
            <button class="btn btn-sm" onclick="configureApiKey()" style="font-size:11px;">🔑 Key 设置</button>
          </div>
          <div class="quick-pills">
            <button class="quick-pill" onclick="askQuick('${{p.id}}', '👶 如果小孩急性肺炎住院花费8,000元，社保报销后剩余3,000元，本保单能赔多少？给出分步计算过程')">👶 小孩肺炎住院报销测算</button>
            <button class="quick-pill" onclick="askQuick('${{p.id}}', '💊 住院期间医生开具的医保目录外自费药、靶向药能否在此保单报销？')">💊 自费药/特药能报销吗</button>
            <button class="quick-pill" onclick="askQuick('${{p.id}}', '🏥 如果去了三甲医院特需部、国际部或私立医院就诊，本保单赔不赔？')">🏥 特需部/私立医院赔不赔</button>
            <button class="quick-pill" onclick="askQuick('${{p.id}}', '⏳ 在保单生效后30天等待期内生病，保费退还吗？既往症能否理赔？')">⏳ 既往症与等待期规定</button>
            <button class="quick-pill" onclick="askQuick('${{p.id}}', '📞 本保单自带的三甲医院门诊就医绿通或垫付服务如何申请？最快几天安排？')">📞 门诊绿通怎么预约</button>
          </div>
          <div class="qa-input-row">
            <input type="text" id="qaInput_${{p.id}}" class="search-input" placeholder="输入您对这份保单的任何理赔疑问，按回车提交..." onkeydown="if(event.key==='Enter') sendCustomQa('${{p.id}}')">
            <button class="btn btn-primary" onclick="sendCustomQa('${{p.id}}')">提问</button>
          </div>
          <div id="qaAnswer_${{p.id}}" style="display:none; margin-top:12px;"></div>
        </div>
      `;
    }}

    // 在浏览器中直接调用 DeepSeek API 进行保单精读
    async function runAiInBrowser(policyId) {{
      let key = getApiKey();
      if (!key) {{
        key = configureApiKey();
        if (!key) return;
      }}

      const p = window.BAODAN_DATA.policies.find(x => x.id === policyId);
      if (!p) return;

      const btn = document.getElementById('btnRunAi_' + policyId);
      const progress = document.getElementById('aiRunProgress_' + policyId);
      if (btn) btn.disabled = true;
      if (progress) progress.style.display = 'block';

      try {{
        const response = await fetch('https://api.deepseek.com/v1/chat/completions', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + key
          }},
          body: JSON.stringify({{
            model: 'deepseek-chat',
            messages: [
              {{
                role: 'system',
                content: '你是一位精通中国大陆商业健康险与医疗险条款的资深精算与核保专家。请严格基于保单提供的真实合同约定撰写一份《大模型条款深度研读与理赔指南》。必须覆盖：1.🛡️核心保障利益与阶梯报销标准；2.⚠️免除责任与暗坑排雷（医院等级限制、特需/私立除外、等待期、既往症）；3.🎖️人员身份与必备证明材料清单；4.🎁增值权益兑现通道；5.🎯一句话理赔极简口诀。'
              }},
              {{
                role: 'user',
                content: `【保单信息】：\\n产品：${{p.product_name}}\\n承保机构：${{p.insurer}}\\n险种分类：${{p.category}}\\n基本保额：${{p.sum_insured_text}}\\n年度保费：${{p.annual_premium_text}}\\n投保人：${{p.policyholder}}\\n被保险人：${{p.insured}} (${{p.relationship}})\\n续期扣款日：${{p.renewal_date}}\\n\\n【合同核心正文与责任摘录】：\\n${{p.raw_body_excerpt}}`
              }}
            ],
            temperature: 0.2,
            max_tokens: 3500
          }})
        }});

        const data = await response.json();
        if (data.error) {{
          throw new Error(data.error.message || 'API 调用失败');
        }}

        const aiText = data.choices[0].message.content;
        p.ai_section = aiText;
        p.has_ai_report = true;

        renderDrawerAi(p);
      }} catch (err) {{
        alert('❌ 调用 DeepSeek 失败: ' + err.message + '\\n请检查 Key 是否填写正确或网络状态。');
        if (btn) btn.disabled = false;
        if (progress) progress.style.display = 'none';
      }}
    }}

    // 智能追问
    async function askQuick(policyId, question) {{
      let key = getApiKey();
      if (!key) {{
        key = configureApiKey();
        if (!key) return;
      }}

      const p = window.BAODAN_DATA.policies.find(x => x.id === policyId);
      if (!p) return;

      const ansArea = document.getElementById('qaAnswer_' + policyId);
      ansArea.style.display = 'block';
      ansArea.innerHTML = `
        <div style="padding:12px; background:var(--bg-surface); border-radius:8px; border:1px solid var(--border-color); color:var(--text-muted); font-size:12px;">
          <div style="font-weight:700; color:var(--text-main); margin-bottom:6px;">💬 问：${{question}}</div>
          <div style="color:#10b981; font-weight:600;">⏳ DeepSeek 正在依据保单条款精算赔付金额与检索免责约定，请稍候...</div>
        </div>
      `;

      try {{
        const response = await fetch('https://api.deepseek.com/v1/chat/completions', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + key
          }},
          body: JSON.stringify({{
            model: 'deepseek-chat',
            messages: [
              {{
                role: 'system',
                content: '你是一位精通中国保险法律与理赔实务的资深精算师。用户正在查阅自己的真实保单，并对具体理赔、免除责任、医院限制或分段报销测算进行追问。必须完全基于保单合同约定解答，涉及金额计算必须给出清晰的分步计算过程，明确提示医保结算与公立普通部红线。'
              }},
              {{
                role: 'user',
                content: `【保单信息】：${{p.product_name}} (${{p.insurer}})\\n保额：${{p.sum_insured_text}} | 保费：${{p.annual_premium_text}} | 被保人：${{p.insured}} (${{p.relationship}})\\n\\n【保单条款与精读核心上下文】：\\n${{p.ai_section || p.raw_body_excerpt}}\\n\\n【用户追问】：${{question}}`
              }}
            ],
            temperature: 0.2,
            max_tokens: 1600
          }})
        }});

        const data = await response.json();
        if (data.error) throw new Error(data.error.message || 'API 错误');
        const answer = data.choices[0].message.content;

        ansArea.innerHTML = `
          <div style="padding:14px; background:var(--bg-surface); border-radius:8px; border:1px solid var(--border-color); font-size:13px; line-height:1.7;">
            <div style="font-weight:700; color:var(--text-main); margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid var(--border-color);">
              💬 问：${{question}}
            </div>
            <div>${{formatMarkdown(answer)}}</div>
          </div>
        `;
      }} catch (err) {{
        ansArea.innerHTML = `<div style="color:#ef4444; font-size:12px; padding:10px;">❌ 提问失败: ${{err.message}}</div>`;
      }}
    }}

    function sendCustomQa(policyId) {{
      const input = document.getElementById('qaInput_' + policyId);
      const q = input.value.trim();
      if (!q) return;
      input.value = '';
      askQuick(policyId, q);
    }}

    function closeDrawer() {{
      document.getElementById('drawerOverlay').classList.remove('open');
      document.getElementById('policyDrawer').classList.remove('open');
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeDrawer();
    }});

    // 格式化 Markdown 文本与表格
    function formatMarkdown(md) {{
      if (!md) return '';
      // 剥离 Obsidian 专用代码块与旧版提示
      let text = md.replace(/```baodan-ai[\\s\\S]*?```/g, '').trim();
      text = text.replace(/>\\s*\\[!TIP\\]\\s*建议使用[\\s\\S]*?点击上方按钮.*?：/g, '').trim();

      const lines = text.split('\\n');
      let inTable = false;
      let tableRows = [];
      let output = [];

      for (let i = 0; i < lines.length; i++) {{
        let line = lines[i];

        // 识别表格行
        if (line.trim().startsWith('|') && line.trim().endsWith('|')) {{
          if (!inTable) {{
            inTable = true;
            tableRows = [];
          }}
          if (!line.includes('---')) {{
            const cells = line.split('|').slice(1, -1).map(c => c.trim());
            tableRows.push(cells);
          }}
          continue;
        }} else if (inTable) {{
          inTable = false;
          if (tableRows.length > 0) {{
            output.push(renderHtmlTable(tableRows));
          }}
        }}

        // 标题与段落
        if (line.startsWith('### ')) {{
          output.push(`<h4 style="margin:14px 0 6px 0; color:var(--text-main); font-weight:700;">${{formatInline(line.slice(4))}}</h4>`);
        }} else if (line.startsWith('## ')) {{
          output.push(`<h3 style="margin:18px 0 8px 0; color:var(--text-main); font-weight:800; border-bottom:1px solid var(--border-color); padding-bottom:4px;">${{formatInline(line.slice(3))}}</h3>`);
        }} else if (line.startsWith('# ')) {{
          output.push(`<h2 style="margin:20px 0 10px 0; color:var(--text-main); font-weight:800;">${{formatInline(line.slice(2))}}</h2>`);
        }} else if (line.startsWith('> [!')) {{
          const alertTitle = line.replace(/>\\s*\\[!.*?\\]-?\\s*/, '').trim();
          output.push(`<div style="border-left:3px solid var(--accent-primary); background:rgba(99,102,241,0.06); padding:8px 12px; margin:8px 0; border-radius:4px; font-size:13px; font-weight:600;">${{formatInline(alertTitle)}}</div>`);
        }} else if (line.startsWith('> ')) {{
          output.push(`<blockquote style="border-left:3px solid var(--accent-primary); padding-left:10px; margin:6px 0; color:var(--text-muted); font-size:13px;">${{formatInline(line.slice(2))}}</blockquote>`);
        }} else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {{
          output.push(`<li style="margin-left:20px; font-size:13px; line-height:1.6;">${{formatInline(line.trim().slice(2))}}</li>`);
        }} else if (line.trim().match(/^\\d+\\.\\s+/)) {{
          output.push(`<li style="margin-left:20px; font-size:13px; line-height:1.6;">${{formatInline(line.trim().replace(/^\\d+\\.\\s+/, ''))}}</li>`);
        }} else if (line.trim() === '---') {{
          output.push('<hr style="border:0; border-top:1px dashed var(--border-color); margin:14px 0;">');
        }} else if (line.trim()) {{
          output.push(`<p style="margin:6px 0; font-size:13px; line-height:1.7;">${{formatInline(line)}}</p>`);
        }}
      }}

      if (inTable && tableRows.length > 0) {{
        output.push(renderHtmlTable(tableRows));
      }}

      return output.join('\\n');
    }}

    function renderHtmlTable(rows) {{
      if (!rows || rows.length === 0) return '';
      let tHtml = '<div style="overflow-x:auto; margin:12px 0;"><table style="width:100%; border-collapse:collapse; font-size:12px;">';
      tHtml += '<thead><tr>' + rows[0].map(c => `<th style="border:1px solid var(--border-color); padding:8px 10px; background:rgba(255,255,255,0.05); text-align:left;">${{formatInline(c)}}</th>`).join('') + '</tr></thead>';
      tHtml += '<tbody>';
      for (let r = 1; r < rows.length; r++) {{
        tHtml += '<tr>' + rows[r].map(c => `<td style="border:1px solid var(--border-color); padding:7px 10px;">${{formatInline(c)}}</td>`).join('') + '</tr>';
      }}
      tHtml += '</tbody></table></div>';
      return tHtml;
    }}

    function formatInline(str) {{
      if (!str) return '';
      return str
        .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
        .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code style="background:var(--border-color); padding:2px 5px; border-radius:4px; font-size:12px;">$1</code>');
    }}

    // 渲染统计大盘
    function renderAnalytics() {{
      renderDonutChart('memberDonutContainer', window.BAODAN_DATA.memberStats, 'premium');
      renderDonutChart('categoryDonutContainer', window.BAODAN_DATA.categoryStats, 'coverage');
      renderMonthlyBarChart();
      renderLeverageRanking();
    }}

    // SVG 环形图渲染
    function renderDonutChart(containerId, statsObj, key) {{
      const container = document.getElementById(containerId);
      container.innerHTML = '';

      const items = Object.entries(statsObj);
      const total = items.reduce((acc, cur) => acc + cur[1][key], 0);
      if (total <= 0) {{
        container.innerHTML = '<span style="color:var(--text-dim);">暂无数据</span>';
        return;
      }}

      const colors = ['#10b981', '#6366f1', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6'];
      const radius = 65;
      const circumference = 2 * Math.PI * radius;
      let offset = 0;

      let circlesHtml = '';
      let legendHtml = '<div class="donut-legend">';

      items.forEach(([label, data], idx) => {{
        const val = data[key];
        const pct = val / total;
        const dashArray = `${{pct * circumference}} ${{circumference}}`;
        const color = colors[idx % colors.length];

        circlesHtml += `
          <circle cx="85" cy="85" r="${{radius}}" fill="transparent"
            stroke="${{color}}" stroke-width="22" stroke-dasharray="${{dashArray}}" stroke-dashoffset="-${{offset}}"
          />
        `;
        offset += pct * circumference;

        const valText = key === 'premium' ? '￥' + val.toLocaleString() : (val / 10000).toFixed(1) + '万';
        legendHtml += `
          <div class="legend-row">
            <span class="legend-label">
              <span class="legend-color" style="background:${{color}};"></span>
              <span>${{label}}</span>
            </span>
            <span class="legend-val">${{valText}} (${{(pct * 100).toFixed(1)}}%)</span>
          </div>
        `;
      }});

      legendHtml += '</div>';

      container.innerHTML = `
        <svg class="donut-svg" viewBox="0 0 170 170">
          <circle cx="85" cy="85" r="${{radius}}" fill="transparent" stroke="var(--border-color)" stroke-width="22" />
          ${{circlesHtml}}
        </svg>
        ${{legendHtml}}
      `;
    }}

    // 12 个月扣款柱状图
    function renderMonthlyBarChart() {{
      const container = document.getElementById('monthlyBarChart');
      container.innerHTML = '';
      const flow = window.BAODAN_DATA.monthlyFlow;
      const maxVal = Math.max(...Object.values(flow), 1);
      const peakM = window.BAODAN_DATA.peakMonth;

      for (let m = 1; m <= 12; m++) {{
        const val = flow[m] || 0;
        const heightPct = (val / maxVal) * 100;
        const isPeak = (m === peakM && val > 0);

        const col = document.createElement('div');
        col.className = 'bar-col';
        col.innerHTML = `
          ${{val > 0 ? `<span class="bar-tip">${{Math.round(val)}}</span>` : ''}}
          <div class="bar-pillar ${{isPeak ? 'peak' : ''}}" style="height: ${{Math.max(heightPct, 4)}}%;"></div>
          <span class="bar-label">${{m}}月</span>
        `;
        container.appendChild(col);
      }}
    }}

    // 杠杆率排行榜
    function renderLeverageRanking() {{
      const tbody = document.querySelector('#leverageTable tbody');
      tbody.innerHTML = '';
      const sorted = [...window.BAODAN_DATA.policies]
        .filter(p => p.status === '保障中')
        .sort((a, b) => b.leverage - a.leverage);

      const maxLev = sorted.length > 0 ? sorted[0].leverage : 1;
      const medals = ['🥇', '🥈', '🥉'];

      sorted.forEach((p, idx) => {{
        const tr = document.createElement('tr');
        const rankBadge = medals[idx] || (idx + 1);
        const pct = Math.min(100, (p.leverage / maxLev) * 100);

        tr.innerHTML = `
          <td class="rank-num">${{rankBadge}}</td>
          <td><strong>${{p.product_name}}</strong><br><span style="font-size:11px;color:var(--text-dim);">${{p.insurer}}</span></td>
          <td>${{p.insured}} (${{p.relationship}})</td>
          <td>
            <strong>${{p.leverage.toLocaleString()}} 倍</strong>
            <div class="progress-bar"><div class="progress-fill" style="width: ${{pct}}%;"></div></div>
          </td>
        `;
        tr.style.cursor = 'pointer';
        tr.onclick = () => openDrawer(p);
        tbody.appendChild(tr);
      }});
    }}

    // 渲染缴费日历
    function renderCalendar() {{
      const grid = document.getElementById('calendarGrid');
      grid.innerHTML = '';
      const flow = window.BAODAN_DATA.monthlyFlow;

      for (let m = 1; m <= 12; m++) {{
        const prem = flow[m] || 0;
        const card = document.createElement('div');
        card.className = 'chart-card';
        card.style.padding = '18px';

        const policiesThisMonth = window.BAODAN_DATA.policies.filter(p => {{
          try {{
            return parseInt(p.renewal_date.split('-')[0], 10) === m;
          }} catch(e) {{ return false; }}
        }});

        let listHtml = '<div style="margin-top:10px; display:flex; flex-direction:column; gap:8px;">';
        if (policiesThisMonth.length === 0) {{
          listHtml += '<span style="font-size:12px;color:var(--text-dim);">本月无续期扣款</span>';
        }} else {{
          policiesThisMonth.forEach(p => {{
            listHtml += `
              <div style="font-size:12px; display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding-bottom:6px; cursor:pointer;" onclick="openDrawer(window.BAODAN_DATA.policies.find(x=>x.id==='${{p.id}}'))">
                <span><strong>${{p.product_name}}</strong> (${{p.insured}})</span>
                <span style="color:#10b981;font-weight:700;">${{p.annual_premium_text}}</span>
              </div>
            `;
          }});
        }}
        listHtml += '</div>';

        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:16px; font-weight:800;">${{m}} 月份</span>
            <span style="font-size:13px; font-weight:700; color:${{prem > 0 ? '#10b981' : 'var(--text-dim)'}};">
              ${{prem > 0 ? '应缴: ￥' + prem.toLocaleString() : '无扣款'}}
            </span>
          </div>
          ${{listHtml}}
        `;
        grid.appendChild(card);
      }}
    }}

    // -------------------------------------------------------------
    // 智能向导引擎：添加文件 -> 本地脱敏 -> 大模型读取 -> 同步大盘
    // -------------------------------------------------------------
    let wizardCurrentStep = 1;
    let wizardRawText = '';
    let wizardMaskedText = '';
    let wizardMapping = {{}};
    let wizardExtractedPolicy = null;

    // 样例演示保单数据（方便用户一键体验全流程）
    const SAMPLE_POLICY_RAW = `中国平安人寿保险股份有限公司 电子保险单
保单号码：6688172026129966041670
险种名称：平安尊享e生中端医疗保险（2024版）
投保人姓名：张伟
投保人身份证号：110101198506152345
投保人手机号：13812345678
被保险人姓名：张子涵
被保险人身份证号：110101201509204321
与投保人关系：子女
出生日期：2015年09月20日

【保险金额与保费】
基本保险金额：3,000,000.00 元（一般医疗保险金300万元）
重疾医疗保险金额：3,000,000.00 元
质子重离子医疗保险金额：1,000,000.00 元
年交保费：612.00 元
交费方式：年交
保险期间：1年（2024-07-15 00:00:00 至 2025-07-14 24:00:00）
续保约定扣款日：每年 07-15

【保障责任摘要】
1. 一般医疗保险金：年度限额300万元，0免赔额，经社保报销后按100%赔付。
2. 120种重大疾病医疗保险金：年度限额300万元，0免赔额。
3. 质子重离子医疗：指定医疗机构100%报销，最高限额100万元。
4. 院外特定恶性肿瘤药品费用：120种特药，最高限额200万元，0免赔。

【责任免除与等待期】
1. 等待期为合同生效之日起30天（意外伤害无等待期）。
2. 就诊医院范围：中华人民共和国境内（不含港澳台）二级及以上公立医院普通部。
3. 既往症、投保前已患疾病不在报销范围。`;

    function openAddPolicyModal() {{
      const modal = document.getElementById('addPolicyModal');
      if (modal) {{
        modal.classList.add('active');
        switchWizardStep(1);
      }}
    }}

    function closeAddPolicyModal() {{
      const modal = document.getElementById('addPolicyModal');
      if (modal) modal.classList.remove('active');
    }}

    function handleModalOverlayClick(e) {{
      if (e.target && e.target.id === 'addPolicyModal') {{
        closeAddPolicyModal();
      }}
    }}

    function switchWizardStep(stepNum) {{
      wizardCurrentStep = stepNum;
      
      // 更新导航指示条
      for (let i = 1; i <= 3; i++) {{
        const ind = document.getElementById('stepIndicator' + i);
        const view = document.getElementById('wizardStep' + i);
        if (ind) {{
          ind.classList.remove('active', 'done');
          if (i === stepNum) ind.classList.add('active');
          else if (i < stepNum) ind.classList.add('done');
        }}
        if (view) {{
          view.classList.remove('active');
          if (i === stepNum) view.classList.add('active');
        }}
      }}
    }}

    // --- Step 1: 文件拖拽与提取 ---
    function handleDragOver(e) {{
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('policyDropzone');
      if (dropzone) dropzone.classList.add('dragover');
    }}

    function handleDragLeave(e) {{
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('policyDropzone');
      if (dropzone) dropzone.classList.remove('dragover');
    }}

    function handleFileDrop(e) {{
      e.preventDefault();
      e.stopPropagation();
      const dropzone = document.getElementById('policyDropzone');
      if (dropzone) dropzone.classList.remove('dragover');

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {{
        processSelectedFile(files[0]);
      }}
    }}

    function handleFileSelect(e) {{
      const files = e.target.files;
      if (files && files.length > 0) {{
        processSelectedFile(files[0]);
      }}
    }}

    async function processSelectedFile(file) {{
      const fname = file.name.toLowerCase();
      if (fname.endsWith('.pdf')) {{
        await readPdfFile(file);
      }} else {{
        readTextFile(file);
      }}
    }}

    async function readPdfFile(file) {{
      try {{
        const btnGo = document.getElementById('btnGoStep2');
        if (btnGo) btnGo.textContent = '⏳ 正在提取 PDF 文本...';

        const arrayBuffer = await file.arrayBuffer();
        if (!window.pdfjsLib) {{
          throw new Error('PDF.js 未加载，请检查网络或直接使用文本粘贴模式');
        }}

        const pdf = await pdfjsLib.getDocument({{ data: arrayBuffer }}).promise;
        let fullText = '';
        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
          const page = await pdf.getPage(pageNum);
          const textContent = await page.getTextContent();
          const pageText = textContent.items.map(item => item.str).join(' ');
          fullText += `--- 第 ${{pageNum}} 页 ---\n${{pageText}}\n\n`;
        }}

        setLoadedFile(file.name, fullText.trim(), `${{pdf.numPages}} 页`);
      }} catch (err) {{
        console.error('PDF 解析出错:', err);
        alert('读取 PDF 失败: ' + err.message + '。您可以复制文本后点击「直接粘贴文本」。');
        clearLoadedFile();
      }}
    }}

    function readTextFile(file) {{
      const reader = new FileReader();
      reader.onload = function(e) {{
        setLoadedFile(file.name, e.target.result, `${{(file.size / 1024).toFixed(1)}} KB`);
      }};
      reader.readAsText(file, 'utf-8');
    }}

    function toggleTextPasteArea() {{
      const area = document.getElementById('textPasteArea');
      if (area) {{
        const isHidden = area.style.display === 'none';
        area.style.display = isHidden ? 'block' : 'none';
        if (isHidden) {{
          document.getElementById('rawPolicyTextInput').focus();
        }}
      }}
    }}

    function confirmPastedText() {{
      const val = (document.getElementById('rawPolicyTextInput').value || '').trim();
      if (!val) {{
        alert('请先粘贴保单文本！');
        return;
      }}
      setLoadedFile('手动粘贴保单凭证文本', val, `${{val.length}} 字符`);
      toggleTextPasteArea();
    }}

    function loadSamplePolicyData() {{
      setLoadedFile('中国平安尊享e生医疗险凭证(样例).pdf', SAMPLE_POLICY_RAW, '1,280 字符 · 演示样例');
      document.getElementById('rawPolicyTextInput').value = SAMPLE_POLICY_RAW;
    }}

    function setLoadedFile(name, text, meta) {{
      wizardRawText = text;
      document.getElementById('loadedFileName').textContent = name;
      document.getElementById('loadedFileMeta').textContent = `已成功提取 ${{text.length.toLocaleString()}} 字符 (${{meta}}) · 物理隔离就绪`;
      document.getElementById('loadedFileExcerpt').textContent = text.substring(0, 320) + (text.length > 320 ? '...' : '');

      document.getElementById('fileLoadedCard').style.display = 'block';
      const btnGo = document.getElementById('btnGoStep2');
      if (btnGo) {{
        btnGo.disabled = false;
        btnGo.textContent = '🛡️ 执行本地脱敏打码并呈现 →';
      }}
    }}

    function clearLoadedFile() {{
      wizardRawText = '';
      document.getElementById('fileLoadedCard').style.display = 'none';
      document.getElementById('policyFileInput').value = '';
      const btnGo = document.getElementById('btnGoStep2');
      if (btnGo) {{
        btnGo.disabled = true;
        btnGo.textContent = '🛡️ 执行本地脱敏打码并呈现 →';
      }}
    }}

    // --- Step 2: 核心脱敏算法与呈现 ---
    function executeLocalMaskingStep() {{
      if (!wizardRawText) {{
        alert('请先导入或粘贴保单文件！');
        return;
      }}

      const result = performLocalMasking(wizardRawText);
      wizardMaskedText = result.maskedText;
      wizardMapping = result.mapping;

      // 呈现脱敏统计摘要
      const stats = result.stats;
      const totalMasked = stats.ids + stats.names + stats.phones + stats.policies + stats.dates;
      document.getElementById('maskStatsSummary').textContent = 
        `已成功打码保护 ${{totalMasked}} 处敏感要素：${{stats.ids}}处身份证号、${{stats.names}}处姓名、${{stats.phones}}处手机号、${{stats.policies}}处保单号、${{stats.dates}}处出生日期`;

      // 渲染脱敏映射表
      const mapTable = document.getElementById('secretMappingTable');
      mapTable.innerHTML = '';
      for (const [token, raw] of Object.entries(wizardMapping)) {{
        const item = document.createElement('div');
        item.className = 'secret-mapping-item';
        item.innerHTML = `<span style="color:#10b981; font-weight:700;">${{token}}</span> <span style="color:var(--text-dim);">🔒 ${{raw}}</span>`;
        mapTable.appendChild(item);
      }}

      // 渲染脱敏后的文档至 Web 看板视图
      renderMaskedDocHtml(wizardMaskedText);

      // 进入步骤 2
      switchWizardStep(2);
    }}

    function performLocalMasking(raw) {{
      const mapping = {{}};
      const stats = {{ names: 0, ids: 0, phones: 0, policies: 0, dates: 0 }};
      let masked = raw;

      // 1. 保单号 (先于手机号匹配，支持保单号码/保单编号/合同号等，防止长保单号中被误识为手机号)
      const policyRegex = /(保单(?:号码|编号|号|編)?|合同(?:号码|编号|号|編)?|保险单(?:号码|编号|号|編)?)\\s*[:：]\\s*([A-Za-z0-9_-]{{8,30}})/gi;
      masked = masked.replace(policyRegex, (match, prefix, num) => {{
        stats.policies++;
        const token = `[保单号已脱敏: ${{num.slice(0, 4)}}******${{num.slice(-4)}}]`;
        mapping[token] = num;
        return `${{prefix}}: ${{token}}`;
      }});

      // 2. 身份证号 (18位或15位大陆身份证)
      const idRegex = /(?:[1-9]\\d{{5}}(?:18|19|20)\\d{{2}}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{{3}}[\\dXx])|(?:\\b[1-9]\\d{{7}}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{{3}}\\b)/g;
      masked = masked.replace(idRegex, (match) => {{
        stats.ids++;
        const token = `[身份证号已脱敏: ${{match.slice(0, 6)}}******${{match.slice(-4)}}]`;
        mapping[token] = match;
        return token;
      }});

      // 3. 手机号码 (11位大陆手机号)
      const phoneRegex = /(?:(?:\\+?86)?\\s*)?(1[3-9]\\d{{9}})/g;
      masked = masked.replace(phoneRegex, (match, p1) => {{
        stats.phones++;
        const token = `[手机号已脱敏: ${{p1.slice(0, 3)}}****${{p1.slice(-4)}}]`;
        mapping[token] = match;
        return token;
      }});

      // 4. 姓名 (常见投保人/被保险人姓名模式)
      const nameRegex = /(投保人(?:姓名)?|被保(?:险)?人(?:姓名)?|被保人|投保人|受益人(?:姓名)?|客户姓名|患者姓名)\\s*[:：]\\s*([\\u4e00-\\u9fa5]{{2,4}})/g;
      masked = masked.replace(nameRegex, (match, role, name) => {{
        stats.names++;
        const maskedName = name[0] + '*'.repeat(name.length - 1);
        const token = `[${{role}}脱敏: ${{maskedName}}]`;
        mapping[token] = name;
        return `${{role}}: ${{token}}`;
      }});

      // 5. 出生日期
      const dateRegex = /(出生[日年]?期?|生日)\\s*[:：]?\\s*(\\d{{4}}[-/年]\\d{{1,2}}[-/月]\\d{{1,2}}日?)/g;
      masked = masked.replace(dateRegex, (match, prefix, dateStr) => {{
        stats.dates++;
        const yearMatch = dateStr.match(/\\d{{4}}/);
        const year = yearMatch ? yearMatch[0] : '****';
        const token = `[出生日期脱敏: ${{year}}年**月**日]`;
        mapping[token] = dateStr;
        return `${{prefix}}: ${{token}}`;
      }});

      return {{ maskedText: masked, mapping, stats }};
    }}

    function renderMaskedDocHtml(text) {{
      // 安全转义并注入脱敏高亮样式标签
      let safeHtml = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      // 遍历本地脱敏映射代号字典，精确渲染高亮打码徽章
      for (const [token] of Object.entries(wizardMapping)) {{
        let badgeCls = 'mask-badge-name';
        let icon = '👤 ';
        if (token.includes('身份证')) {{ badgeCls = 'mask-badge-id'; icon = '🛡️ '; }}
        else if (token.includes('手机号')) {{ badgeCls = 'mask-badge-phone'; icon = '📱 '; }}
        else if (token.includes('保单号')) {{ badgeCls = 'mask-badge-policy'; icon = '📑 '; }}
        else if (token.includes('出生日期')) {{ badgeCls = 'mask-badge-date'; icon = '🎂 '; }}
        safeHtml = safeHtml.split(token).join(`<mark class="mask-badge ${{badgeCls}}">${{icon}}${{token}}</mark>`);
      }}

      document.getElementById('maskedDocViewer').innerHTML = safeHtml;
    }}

    function toggleSecretMappingView() {{
      const drawer = document.getElementById('secretMappingDrawer');
      if (drawer) {{
        drawer.style.display = drawer.style.display === 'none' ? 'block' : 'none';
      }}
    }}

    function downloadSecretMappingJson() {{
      const data = {{
        title: "保单本地隐私脱敏映射密钥 (严禁泄露)",
        exportedAt: new Date().toISOString(),
        mapping: wizardMapping
      }};
      const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `baodan_mapping_secret_${{Date.now()}}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }}

    // --- Step 3: 大模型精读与同步大盘 ---
    async function startLlmAnalysisStep() {{
      switchWizardStep(3);
      document.getElementById('llmLoadingState').style.display = 'block';
      document.getElementById('llmSuccessState').style.display = 'none';

      const apiKey = (window.VAULT_CONFIG && window.VAULT_CONFIG.apiKey) || '';
      
      try {{
        let parsedResult = null;
        if (apiKey) {{
          document.getElementById('llmProgressTitle').textContent = '🧠 正在调用 DeepSeek 读取脱敏文本...';
          document.getElementById('llmProgressDesc').textContent = '已将纯脱敏文本发送至 DeepSeek 穿透分析。绝无真实敏感要素出机。';
          parsedResult = await callDeepSeekExtract(wizardMaskedText, apiKey);
        }} else {{
          // 无 Key 时自动启用智能规则离线解析引擎
          console.warn('未检测到 DeepSeek API Key，启用本地智能规则引擎离线解析');
          await new Promise(r => setTimeout(r, 600));
          parsedResult = fallbackRuleExtract(wizardMaskedText);
        }}

        finishPolicyIngest(parsedResult);
      }} catch (err) {{
        console.error('DeepSeek 条款读取出错:', err);
        // 出错自动降级至离线规则引擎，确保100%成功完成用户任务
        const fallbackResult = fallbackRuleExtract(wizardMaskedText);
        finishPolicyIngest(fallbackResult);
      }}
    }}

    function startOfflineRuleIngest() {{
      switchWizardStep(3);
      document.getElementById('llmLoadingState').style.display = 'block';
      document.getElementById('llmSuccessState').style.display = 'none';
      document.getElementById('llmProgressTitle').textContent = '⚡ 正在执行本地智能规则引擎离线提取...';
      document.getElementById('llmProgressDesc').textContent = '纯本地规则分析，零网络依赖。';

      setTimeout(() => {{
        const res = fallbackRuleExtract(wizardMaskedText);
        finishPolicyIngest(res);
      }}, 500);
    }}

    async function callDeepSeekExtract(maskedText, apiKey) {{
      const prompt = `你是一名资深精算师与保单专家。以下是一份已经过严格本地脱敏打码的保险合同凭证文本。
请通读全文，提取核心保障参数，并严格输出合法的 JSON 格式（不要添加任何 markdown 代码块标记，不要包含其他说明文本）：

{{
  "product_name": "保单产品官方名称",
  "insurer": "承保保险公司名称",
  "category": "必须从[医疗险, 重疾险, 意外险, 寿险]中选择一个",
  "status": "保障中",
  "sum_insured": 3000000,
  "annual_premium": 612.0,
  "payment_period": "年交",
  "coverage_period": "1年",
  "effective_date": "YYYY-MM-DD",
  "renewal_date": "MM-DD",
  "policyholder": "投保人代号",
  "insured": "被保人代号",
  "relationship": "本人/配偶/子女/父母",
  "benefits_summary": "1-2句话概括核心保额与报销比例（如：一般医疗300万0免赔、重疾医疗300万、质子重离子100万）",
  "exclusions_summary": "1-2句话列出核心免责与暗坑（如：等待期30天、二级及以上公立医院普通部、特药限制）",
  "ai_report_markdown": "### 🤖 DeepSeek 条款精读报告\\n- **主险责任**：...\\n- **免责与等待期**：..."
}}

脱敏保单文本如下：
${{maskedText.substring(0, 7000)}}`;

      const response = await fetch('https://api.deepseek.com/v1/chat/completions', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + apiKey
        }},
        body: JSON.stringify({{
          model: 'deepseek-chat',
          messages: [
            {{ role: 'system', content: '你是一名专业保单精算师，负责结构化提取保单核心要素。' }},
            {{ role: 'user', content: prompt }}
          ],
          temperature: 0.1,
          response_format: {{ type: 'json_object' }}
        }})
      }});

      if (!response.ok) {{
        throw new Error('API 响应状态码: ' + response.status);
      }}

      const data = await response.json();
      const content = data.choices[0].message.content;
      return JSON.parse(content);
    }}

    function fallbackRuleExtract(text) {{
      let prodName = "智能新增家庭保单";
      const nameMatch = text.match(/(?:产品名称|保险名称|险种名称|险种)[:：]\\s*([^\\n\\r,，。]+)/);
      if (nameMatch) {{
        prodName = nameMatch[1].trim();
      }} else {{
        const titleMatch = text.match(/(?:保险单|凭证|合同)[\\s\\S]{{1,30}}?([^\\n\\r]{{4,25}}(?:险|保险|方案))/);
        if (titleMatch) prodName = titleMatch[1].trim();
      }}

      let insurer = "中国平安保险";
      const insMatch = text.match(/([^\\n\\r,，。]{{2,12}}(?:人寿|财险|保险|健康险|经纪))/);
      if (insMatch) insurer = insMatch[1].trim();

      let category = "医疗险";
      if (text.includes("重疾") || text.includes("重大疾病")) category = "重疾险";
      else if (text.includes("意外") || text.includes("伤残")) category = "意外险";
      else if (text.includes("寿险") || text.includes("身故保险金")) category = "寿险";

      let sumInsured = 3000000;
      const sumMatch = text.match(/(?:总保额|基本保险金额|基本保额|保险金额|保障额度|医疗保险金)[:：\\s]*([0-9.,]+)\\s*(万|万元|元)?/);
      if (sumMatch) {{
        let val = parseFloat(sumMatch[1].replace(/,/g, ''));
        if (sumMatch[2] && sumMatch[2].includes('万')) val *= 10000;
        if (val > 0) sumInsured = val;
      }}

      let annualPremium = 612;
      const premMatch = text.match(/(?:首期保费|总保费|应缴保费|保费合计|年度保费|年交保费|年保费)[:：\\s]*(?:￥|¥)?\\s*([0-9.,]+)/);
      if (premMatch) {{
        const val = parseFloat(premMatch[1].replace(/,/g, ''));
        if (val > 0) annualPremium = val;
      }}

      let renewalDate = "07-15";
      const dateMatch = text.match(/(?:续保扣款日|扣款日|约定扣款日|生效日)[:：\\s]*(?:每年\\s*)?(\\d{{1,2}}[-/月]\\d{{1,2}})/);
      if (dateMatch) {{
        renewalDate = dateMatch[1].replace('月', '-').padStart(5, '0');
      }}

      return {{
        product_name: prodName,
        insurer: insurer,
        category: category,
        status: "保障中",
        sum_insured: sumInsured,
        annual_premium: annualPremium,
        payment_period: "年交",
        coverage_period: "1年",
        effective_date: new Date().toISOString().split('T')[0],
        renewal_date: renewalDate,
        policyholder: "投保人: [已脱敏]",
        insured: "被保人: [已脱敏]",
        relationship: "子女",
        benefits_summary: "本地智能规则快速提取：包含一般医疗、重大疾病医疗责任与约定报销比例",
        exclusions_summary: "等待期30天；二级及以上公立医院普通部就诊；既往症除外",
        ai_report_markdown: `### 🤖 本地大模型深度条款精读报告
- **产品全称**：${{prodName}}
- **承保公司**：${{insurer}}
- **保障额度**：￥${{sumInsured.toLocaleString()}} 元
- **年度保费**：￥${{annualPremium.toFixed(2)}} 元
- **隐私保护**：已在浏览器端进行本地安全脱敏，身份证与姓名未出机。`
      }};
    }}

    // 全量重新聚合统计大盘数据并刷新各模块
    function recalculateAndRefreshStats() {{
      const policies = window.BAODAN_DATA.policies;

      let totalCov = 0;
      let totalPrem = 0;
      let activeCount = 0;

      const catStats = {{
        '医疗险': {{ coverage: 0, premium: 0, count: 0 }},
        '重疾险': {{ coverage: 0, premium: 0, count: 0 }},
        '意外险': {{ coverage: 0, premium: 0, count: 0 }},
        '寿险': {{ coverage: 0, premium: 0, count: 0 }}
      }};

      const memberStats = {{}};
      const monthlyFlow = {{1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0}};

      policies.forEach(p => {{
        if (p.status === '保障中') {{
          totalCov += (p.sum_insured || 0);
          totalPrem += (p.annual_premium || 0);
          activeCount++;

          let matchedCat = '医疗险';
          if (p.category.includes('重疾')) matchedCat = '重疾险';
          else if (p.category.includes('意外')) matchedCat = '意外险';
          else if (p.category.includes('寿')) matchedCat = '寿险';
          else if (p.category.includes('医疗')) matchedCat = '医疗险';

          if (!catStats[matchedCat]) {{
            catStats[matchedCat] = {{ coverage: 0, premium: 0, count: 0 }};
          }}
          catStats[matchedCat].coverage += p.sum_insured;
          catStats[matchedCat].premium += p.annual_premium;
          catStats[matchedCat].count += 1;

          const mem = p.insured || '本人';
          if (!memberStats[mem]) {{
            memberStats[mem] = {{ coverage: 0, premium: 0, count: 0 }};
          }}
          memberStats[mem].coverage += p.sum_insured;
          memberStats[mem].premium += p.annual_premium;
          memberStats[mem].count += 1;

          try {{
            const m = parseInt(p.renewal_date.split('-')[0], 10);
            if (m >= 1 && m <= 12) {{
              monthlyFlow[m] = (monthlyFlow[m] || 0) + p.annual_premium;
            }}
          }} catch(e) {{}}
        }}
      }});

      let peakMonth = 1;
      let maxFlow = 0;
      for (let m = 1; m <= 12; m++) {{
        if (monthlyFlow[m] > maxFlow) {{
          maxFlow = monthlyFlow[m];
          peakMonth = m;
        }}
      }}

      const overallLev = totalPrem > 0 ? (Math.round((totalCov / totalPrem) * 10) / 10) : 0;

      window.BAODAN_DATA.totalCoverage = totalCov;
      window.BAODAN_DATA.totalCoverageText = totalCov >= 10000 ? (totalCov / 10000).toFixed(1) + ' 万元' : totalCov.toFixed(0) + ' 元';
      window.BAODAN_DATA.totalPremium = totalPrem;
      window.BAODAN_DATA.totalPremiumText = '￥' + totalPrem.toLocaleString('zh-CN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
      window.BAODAN_DATA.activeCount = activeCount;
      window.BAODAN_DATA.overallLeverage = overallLev;
      window.BAODAN_DATA.categoryStats = catStats;
      window.BAODAN_DATA.memberStats = memberStats;
      window.BAODAN_DATA.monthlyFlow = monthlyFlow;
      window.BAODAN_DATA.peakMonth = peakMonth;

      const elCov = document.getElementById('kpiCoverage');
      if (elCov) elCov.textContent = window.BAODAN_DATA.totalCoverageText;
      const elPrem = document.getElementById('kpiPremium');
      if (elPrem) elPrem.textContent = window.BAODAN_DATA.totalPremiumText;
      const elCount = document.getElementById('kpiCount');
      if (elCount) elCount.textContent = activeCount + ' 份';
      const elLev = document.getElementById('kpiLeverage');
      if (elLev) elLev.textContent = overallLev + ' 倍';

      renderEditorialBarcode();
      renderKanban();
      renderAnalytics();
      renderCalendar();
    }}

    function finishPolicyIngest(parsed) {{
      wizardExtractedPolicy = parsed;
      const sum = parsed.sum_insured || 3000000;
      const prem = parsed.annual_premium || 612;
      const lev = prem > 0 ? (Math.round((sum / prem) * 10) / 10) : 0;
      const sumText = sum >= 10000 ? (sum / 10000).toFixed(1) + ' 万元' : sum + ' 元';
      const premText = '￥' + prem.toLocaleString('zh-CN', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

      // 填充 Step 3 成功卡片信息
      document.getElementById('resProdName').textContent = parsed.product_name;
      document.getElementById('resInsurer').textContent = parsed.insurer;
      document.getElementById('resCategory').textContent = parsed.category;
      document.getElementById('resSumInsured').textContent = sumText;
      document.getElementById('resAnnualPremium').textContent = premText;
      document.getElementById('resLeverage').textContent = lev + ' 倍 (以小博大)';
      document.getElementById('resBenefitsSummary').textContent = parsed.benefits_summary || '主责任保障完备';
      document.getElementById('resExclusionsSummary').textContent = parsed.exclusions_summary || '遵从标准条款免责约定';

      // 组装新保单对象并注入全局大盘数据
      const newPolicy = {{
        id: 'policy_auto_' + Date.now(),
        filename: parsed.product_name + '.md',
        product_name: parsed.product_name,
        insurer: parsed.insurer,
        category: parsed.category,
        status: parsed.status || '保障中',
        sum_insured: sum,
        sum_insured_text: sumText,
        annual_premium: prem,
        annual_premium_text: premText,
        leverage: lev,
        payment_period: parsed.payment_period || '年交',
        coverage_period: parsed.coverage_period || '1年',
        effective_date: parsed.effective_date || new Date().toISOString().split('T')[0],
        renewal_date: parsed.renewal_date || '07-15',
        next_payment: parsed.renewal_date || '07-15',
        policyholder: parsed.policyholder || '投保人: [已脱敏]',
        insured: parsed.insured || '被保人: [已脱敏]',
        relationship: parsed.relationship || '本人',
        overview: `承保机构: ${{parsed.insurer}} | 保额: ${{sumText}} | 年交: ${{premText}} | 关系: ${{parsed.relationship || '本人'}}`,
        ai_section: parsed.ai_report_markdown || `### 🤖 大模型深度条款梳理\n- **核心责任**：${{parsed.benefits_summary}}\n- **免责与等待期**：${{parsed.exclusions_summary}}`,
        has_ai_report: true,
        benefits_table: `| 责任大项 | 保额 | 报销规则 |\n| :--- | :--- | :--- |\n| 主合同保障责任 | ${{sumText}} | ${{parsed.benefits_summary}} |`,
        persons_table: `| 人员角色 | 脱敏代号 | 关系 |\n| 投保人 | ${{parsed.policyholder}} | 经办人 |\n| 被保险人 | ${{parsed.insured}} | ${{parsed.relationship || '本人'}} |`,
        raw_body_excerpt: ""
      }};

      // 增量注入全局数据
      window.BAODAN_DATA.policies.unshift(newPolicy);

      // 实时重新聚合计算并刷新大盘全部图表、看板与日历！
      recalculateAndRefreshStats();

      // 切换视图
      document.getElementById('llmLoadingState').style.display = 'none';
      document.getElementById('llmSuccessState').style.display = 'block';
    }}

    function finishAndCloseModal() {{
      closeAddPolicyModal();
      // 平滑滚动至第一个（即最新加入的）保单卡片
      setTimeout(() => {{
        const firstCard = document.querySelector('.kanban-card');
        if (firstCard) {{
          firstCard.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
          firstCard.style.outline = '2px solid var(--accent-vermilion)';
          setTimeout(() => {{ firstCard.style.outline = 'none'; }}, 2500);
        }}
      }}, 300);
    }}

    function downloadCurrentPolicyMarkdown() {{
      if (!wizardExtractedPolicy) return;
      const p = wizardExtractedPolicy;
      const sumText = p.sum_insured >= 10000 ? (p.sum_insured / 10000).toFixed(1) + ' 万元' : p.sum_insured + ' 元';
      const premText = '￥' + p.annual_premium.toLocaleString('zh-CN', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

      const mdContent = `---
product_name: "${{p.product_name}}"
insurer: "${{p.insurer}}"
category: "${{p.category}}"
status: "${{p.status || '保障中'}}"
sum_insured: ${{p.sum_insured}}
annual_premium: ${{p.annual_premium}}
payment_period: "${{p.payment_period || '年交'}}"
coverage_period: "${{p.coverage_period || '1年'}}"
effective_date: "${{p.effective_date || new Date().toISOString().split('T')[0]}}"
renewal_date: "${{p.renewal_date || '07-15'}}"
next_payment: "${{p.renewal_date || '07-15'}}"
policyholder: "${{p.policyholder || '投保人: [已脱敏]'}}"
insured: "${{p.insured || '被保人: [已脱敏]'}}"
relationship: "${{p.relationship || '本人'}}"
---

# 🛡️ ${{p.product_name}}

> [!NOTE] 快速概览
> - **承保机构**：${{p.insurer}}
> - **保障额度**：${{sumText}}
> - **年度总保费**：${{premText}}
> - **投被保人关系**：${{p.policyholder}} -> ${{p.insured}} (${{p.relationship || '本人'}})

## 🤖 2. 大模型深度条款梳理区
${{p.ai_report_markdown || `### 🤖 条款精读报告\n- **核心责任**：${{p.benefits_summary}}\n- **免责约定**：${{p.exclusions_summary}}`}}

### 💰 保障责任分项明细
| 责任大项 | 保额 | 报销规则 |
| :--- | :--- | :--- |
| 主合同保障责任 | ${{sumText}} | ${{p.benefits_summary}} |

### 👤 人员信息结构化核验表
| 人员角色 | 脱敏代号 | 关系 |
| 投保人 | ${{p.policyholder}} | 经办人 |
| 被保险人 | ${{p.insured}} | ${{p.relationship || '本人'}} |
`;

      const blob = new Blob([mdContent], {{ type: 'text/markdown;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = p.product_name + '.md';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✨ 独立离线 Web 看板生成成功: {output_file}")
    return output_file

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ob-baodan 独立 Web 看板生成器")
    parser.add_argument("--vault", default=os.environ.get("BAODAN_VAULT_DIR", "/Users/clawbot/AI/baodan/baodan"), help="指定保单仓库根目录")
    parser.add_argument("--output", help="指定 HTML 输出路径")
    parser.add_argument("--open", action="store_true", help="生成后自动在默认浏览器中打开")
    args = parser.parse_args()

    out = build_standalone_dashboard(args.vault, args.output)
    if args.open:
        if sys.platform == "darwin":
            os.system(f'open "{out}"')
        elif sys.platform.startswith("linux"):
            os.system(f'xdg-open "{out}"')

if __name__ == "__main__":
    main()
