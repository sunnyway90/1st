# ChatGPT 高评价插件 / Skills / MCP 清单

> 数据参考截止：2026 年 5 月。本清单为学习参考，非 OpenAI 官方排名。

## 口径说明

| 类别 | 实际对应 | 官方入口 |
|------|----------|----------|
| **插件** | 旧 ChatGPT Plugins 已废弃；现为 **Apps in ChatGPT**（Apps SDK + MCP） | [chatgpt.com/apps](https://chatgpt.com/apps) |
| **Skills** | **OpenAI ChatGPT Skills**（工作区流程）+ **Agent Skills**（`SKILL.md` 开放标准） | [OpenAI Skills 帮助](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) / [agentskills.io](https://agentskills.io) |
| **MCP** | Model Context Protocol 服务器；ChatGPT Apps 底层协议，也可在 Cursor 等 IDE 使用 | [cursor.com/docs/mcp](https://cursor.com/docs/mcp) |

**筛选标准：**

- 官方精选 / DevDay 首发合作伙伴
- 社区「App of the Week」或 GPT Store 使用量/评分 Top 榜
- GitHub [best-of-mcp-servers](https://github.com/tolkonepiu/best-of-mcp-servers) 质量分或 Stars 10K+
- 大厂官方维护（Microsoft、AWS、Anthropic、Stripe 等）

---

## 一、ChatGPT Apps 30 个（替代“插件”）

旧 Plugin 已停；以下均为 [chatgpt.com/apps](https://chatgpt.com/apps) 官方/验证集成。

| # | 名称 | 类别 | 链接 | 推荐理由 |
|---|------|------|------|----------|
| 1 | Wolfram | AI/ML | [wolfram.com](https://www.wolfram.com/wolfram-for-chatgpt/) | 社区「App of the Week」；符号计算，弥补 LLM 数学幻觉 |
| 2 | Spotify | 音乐 | [spotify.com](https://www.spotify.com) | OpenAI DevDay 首发；歌单/发现，使用量极高 |
| 3 | Canva | 设计 | [canva.com](https://www.canva.com) | 首发伙伴；PPT/海报/社交图，对话内预览 |
| 4 | Adobe Photoshop | 设计 | [adobe.com](https://www.adobe.com/products/photoshop.html) | Apps 首页 Featured；修图/滤镜 |
| 5 | Figma | 设计 | [figma.com](https://www.figma.com) | 首发伙伴；图表/设计协作 |
| 6 | Zillow | 房产 | [zillow.com](https://www.zillow.com) | 首发伙伴；房源+地图 |
| 7 | Expedia | 旅行 | [expedia.com](https://www.expedia.com) | 首发伙伴；机票酒店 |
| 8 | Booking.com | 旅行 | [booking.com](https://www.booking.com) | 首发伙伴；酒店预订 |
| 9 | Coursera | 教育 | [coursera.org](https://www.coursera.org) | 首发伙伴；课程+视频联动 |
| 10 | Instacart | 生鲜 | [instacart.com](https://www.instacart.com) | 官方宣布 rollout 的合作伙伴 |
| 11 | Slack | 通信 | [slack.com](https://slack.com) | 企业高频；搜频道/发消息 |
| 12 | Tavily AI | 搜索 | [tavily.com](https://tavily.com) | Agent 级实时网页搜索 |
| 13 | Parallel Search | 搜索 | [chatgpt.com/apps/parallel-search](https://chatgpt.com/apps/parallel-search) | AI 优化结构化搜索结果 |
| 14 | Hugging Face | AI/ML | [huggingface.co](https://huggingface.co) | 模型/数据集/Spaces 探索 |
| 15 | Datadog (Preview) | 可观测 | [datadoghq.com](https://www.datadoghq.com) | 日志/指标/链路排障 |
| 16 | Amplitude | 分析 | [amplitude.com](https://amplitude.com) | 产品行为/漏斗分析 |
| 17 | Mixpanel | 分析 | [mixpanel.com](https://mixpanel.com) | 事件分析/留存 |
| 18 | Airtable | 数据 | [airtable.com](https://www.airtable.com) | 结构化项目管理 |
| 19 | Hex | 数据 | [hex.tech](https://hex.tech) | SQL + Notebook 分析 |
| 20 | Supabase | 开发 | [supabase.com](https://supabase.com) | Postgres 后端管理 |
| 21 | Vercel | 开发 | [vercel.com](https://vercel.com) | 文档搜索/部署 |
| 22 | Neon Postgres | 开发 | [neon.com](https://neon.com) | Serverless 数据库分支 |
| 23 | Stripe | 支付 | [stripe.com](https://stripe.com) | 集成最佳实践 + MCP |
| 24 | Shopify | 电商 | [shopify.com](https://www.shopify.com) | GraphQL/Liquid 开发辅助 |
| 25 | Fireflies | 会议 | [fireflies.ai](https://fireflies.ai) | 转录/摘要/搜索会议 |
| 26 | Fathom | 会议 | [fathom.ai](https://fathom.ai) | Zoom/Meet 录制 + AI 摘要 |
| 27 | Calendly | 日程 | [calendly.com](https://calendly.com) | 预约链接/可用性 |
| 28 | Notion | 知识 | [notion.so](https://www.notion.so) | 官方 Notion MCP 集成包 |
| 29 | GitHub (Connector) | 开发 | [github.com](https://github.com) | 仓库/Issue/PR；Codex 必需 |
| 30 | Gmail + Google Drive (Connectors) | 办公 | [google.com](https://mail.google.com) / [drive.google.com](https://drive.google.com) | 邮件/文档上下文接入 |

### GPT Store 补充（自定义 GPT，非 Apps SDK）

若你更关心 GPT Store 高使用量/高评分 GPT，可参考 [GPTsHunter Top 500](https://github.com/AINativeLab/top-500-best-gpts)：

| 名称 | 类别 | 链接 | 备注 |
|------|------|------|------|
| Scholar GPT | 研究 | [Scholar GPT](https://chat.openai.com/g/g-kZ0eYXlJe-scholar-gpt) | 研究类 #1，3900 万+ 对话 |
| Consensus | 研究 | [Consensus](https://chat.openai.com/g/g-bo0FiWLY7-consensus) | 学术文献共识，评分 4.4 |
| SciSpace | 研究 | [SciSpace](https://chat.openai.com/g/g-NgAcklHd8-scispace) | 论文检索与引用 |
| Write For Me | 写作 | [Write For Me](https://chat.openai.com/g/g-B3hgivKK9) | 4800 万+ 对话 |
| Ethical Hacker GPT | 编程 | [Ethical Hacker GPT](https://chat.openai.com/g/g-j4PQ2hyqn-ethical-hacker-gpt) | 安全/渗透学习 |
| Python | 编程 | [Python](https://chat.openai.com/g/g-cKXjWStaE) | Python 学习辅助 |
| Code GPT | 编程 | [Code GPT](https://chat.openai.com/g/g-cksUvVWar) | 代码生成与调试 |

---

## 二、Skills 30 个（Agent Skills 为主）

适用于 ChatGPT（Agent Skills 格式）、Cursor、Claude Code 等。

| # | 名称 | 来源 | 链接 | 用途 |
|---|------|------|------|------|
| 1 | docx | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/docx) | Word 创建/编辑/分析 |
| 2 | pdf | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/pdf) | PDF 读写/表单 |
| 3 | pptx | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/pptx) | PPT 生成/编辑 |
| 4 | xlsx | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/xlsx) | Excel 表格/公式 |
| 5 | webapp-testing | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) | Playwright 测 Web 应用 |
| 6 | mcp-builder | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) | 生成 MCP Server |
| 7 | skill-creator | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | 创建新 Skill 指南 |
| 8 | frontend-design | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | 高质量前端 UI |
| 9 | canvas-design | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/canvas-design) | 视觉/海报设计 |
| 10 | brand-guidelines | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines) | 品牌规范应用 |
| 11 | internal-comms | Anthropic 官方 | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/internal-comms) | 内部沟通文档 |
| 12 | tavily-search | Cursor/Tavily | [cursor.com/marketplace/tavily](https://cursor.com/marketplace/tavily) | 网页搜索 |
| 13 | tavily-extract | Cursor/Tavily | [cursor.com/marketplace/tavily](https://cursor.com/marketplace/tavily) | URL 内容提取 |
| 14 | tavily-research | Cursor/Tavily | [cursor.com/marketplace/tavily](https://cursor.com/marketplace/tavily) | 多源深度调研 |
| 15 | tavily-crawl | Cursor/Tavily | [cursor.com/marketplace/tavily](https://cursor.com/marketplace/tavily) | 站点批量抓取 |
| 16 | stripe-best-practices | Stripe 官方 | [cursor.com/marketplace/stripe](https://cursor.com/marketplace/stripe) | Stripe 集成规范 |
| 17 | vercel-api | Vercel 官方 | [cursor.com/marketplace/skills/vercel-api](https://cursor.com/marketplace/skills/vercel-api) | Vercel 部署/API |
| 18 | sentry-setup / seer | Sentry 官方 | [cursor.com/marketplace/sentry](https://cursor.com/marketplace/sentry) | 生产错误调试 |
| 19 | shopify-admin | Shopify 官方 | [cursor.com/marketplace/shopify](https://cursor.com/marketplace/shopify) | Admin GraphQL |
| 20 | databricks-core | Databricks 官方 | [cursor.com/marketplace/databricks](https://cursor.com/marketplace/databricks) | Databricks CLI |
| 21 | ddsetup | Datadog 官方 | [cursor.com/marketplace/datadog](https://cursor.com/marketplace/datadog) | Datadog MCP 初始化 |
| 22 | notion-search / tasks-plan | Notion 官方 | [github.com/makenotion/cursor-notion-plugin](https://github.com/makenotion/cursor-notion-plugin) | 工作区搜索/任务 |
| 23 | create-plugin | Cursor 官方 | [cursor.com/marketplace](https://cursor.com/marketplace) | 脚手架创建插件 |
| 24 | orchestrate | Cursor 官方 | [cursor.com/marketplace](https://cursor.com/marketplace) | 并行 Cloud Agent |
| 25 | pr-review-canvas | Cursor 官方 | [cursor.com/marketplace](https://cursor.com/marketplace) | PR 可视化审查 |
| 26 | docs-canvas | Cursor 官方 | [cursor.com/marketplace](https://cursor.com/marketplace) | 文档 Canvas |
| 27 | Addy Osmani Agent Skills | 社区高评 | [officialskills.sh](https://officialskills.sh/) | 全 SDLC：规格→测试→发布 |
| 28 | Modern Web Guidance | Google Chrome 团队 | [cursor.com/marketplace](https://cursor.com/marketplace) | 现代 Web API 最佳实践 |
| 29 | GSAP | GSAP 官方 | [cursor.com/marketplace](https://cursor.com/marketplace) | 动画/ScrollTrigger |
| 30 | OpenAI ChatGPT Skills | OpenAI | [OpenAI Academy](https://academy.openai.com/en/public/clubs/work-users-ynjqu/resources/skills) | 可导出/导入的可复用业务流程 |

---

## 三、MCP Server 30 个（质量排名优先）

来源：[best-of-mcp-servers](https://github.com/tolkonepiu/best-of-mcp-servers) 每周质量分 + 官方 MCP 参考实现。

| # | 项目 | 类别 | 链接 | 推荐理由 |
|---|------|------|------|----------|
| 1 | pydantic/pydantic-ai | 代码执行 | [GitHub](https://github.com/pydantic/pydantic-ai) | 质量分 🥇35；安全 Python 沙箱 |
| 2 | bytedance/UI-TARS-desktop | 浏览器 | [GitHub](https://github.com/bytedance/UI-TARS-desktop) | 🥇31；Puppeteer 自动化 |
| 3 | Skyvern-AI/skyvern | 浏览器 | [GitHub](https://github.com/Skyvern-AI/skyvern) | 🥇30；视觉 + LLM 填表/抓取 |
| 4 | microsoft/playwright-mcp | 浏览器 | [GitHub](https://github.com/microsoft/playwright-mcp) | 🥈28；微软官方 Playwright |
| 5 | oraios/serena | 编码 Agent | [GitHub](https://github.com/oraios/serena) | 🥇29；LSP 符号级代码操作 |
| 6 | mindsdb/mindsdb | 聚合器 | [GitHub](https://github.com/mindsdb/mindsdb) | 🥇29；统一多数据源查询 |
| 7 | PipedreamHQ/pipedream | 聚合器 | [GitHub](https://github.com/PipedreamHQ/pipedream) | 🥇29；2500+ API 预置工具 |
| 8 | awslabs/mcp | 云平台 | [GitHub](https://github.com/awslabs/mcp) | 🥇28；AWS 官方全套 |
| 9 | elie222/inbox-zero | 通信 | [GitHub](https://github.com/elie222/inbox-zero) | 🥇28；Gmail 智能收件箱 |
| 10 | CodeGraphContext | 编码 Agent | [GitHub](https://github.com/CodeGraphContext/CodeGraphContext) | 🥇27；代码图谱上下文 |
| 11 | txn2/kubefwd | 云平台 | [GitHub](https://github.com/txn2/kubefwd) | 🥇27；K8s 端口转发 |
| 12 | containers/kubernetes-mcp-server | 云平台 | [GitHub](https://github.com/containers/kubernetes-mcp-server) | 🥈26；K8s/OpenShift CRUD |
| 13 | modelcontextprotocol/servers (GitHub) | 开发者 | [GitHub](https://github.com/modelcontextprotocol/servers) | Anthropic 参考；GitHub API |
| 14 | cloudflare/mcp-server-cloudflare | 云平台 | [GitHub](https://github.com/cloudflare/mcp-server-cloudflare) | 🥈22；Workers/KV/R2/D1 |
| 15 | korotovsky/slack-mcp-server | 通信 | [GitHub](https://github.com/korotovsky/slack-mcp-server) | 🥇25；Slack 工作区 |
| 16 | browserbase/mcp-server-browserbase | 浏览器 | [GitHub](https://github.com/browserbase/mcp-server-browserbase) | 🥈19；云端浏览器 |
| 17 | genomoncology/biomcp | 生医 | [GitHub](https://github.com/genomoncology/biomcp) | 🥇23；PubMed/ClinicalTrials |
| 18 | ahujasid/blender-mcp | 创意 | [GitHub](https://github.com/ahujasid/blender-mcp) | 🥇17；Blender 3D |
| 19 | Flux159/mcp-server-kubernetes | 云平台 | [GitHub](https://github.com/Flux159/mcp-server-kubernetes) | 🥈23；K8s TS 实现 |
| 20 | hashicorp/terraform-mcp-server | 云平台 | [GitHub](https://github.com/hashicorp/terraform-mcp-server) | 🥉20；Terraform 官方 |
| 21 | microsoft/mcp | 开发者 | [GitHub](https://github.com/microsoft/mcp) | ~32K Stars；微软生态 MCP |
| 22 | mcp.sentry.dev | 监控 | [mcp.sentry.dev](https://mcp.sentry.dev/) | Sentry 官方远程 MCP |
| 23 | mcp.notion.com | 生产力 | [Notion MCP 文档](https://developers.notion.com/docs/mcp) | Notion 官方 hosted MCP |
| 24 | executeautomation/mcp-playwright | 浏览器 | [GitHub](https://github.com/executeautomation/mcp-playwright) | 5.5K Stars；Playwright 社区版 |
| 25 | chigwell/telegram-mcp | 通信 | [GitHub](https://github.com/chigwell/telegram-mcp) | 🥈21；Telegram API |
| 26 | Softeria/ms-365-mcp-server | 通信 | [GitHub](https://github.com/Softeria/ms-365-mcp-server) | 🥈20；Outlook/Office 365 |
| 27 | julien040/anyquery | 聚合器 | [GitHub](https://github.com/julien040/anyquery) | 🥈19；SQL 查 40+ 应用 |
| 28 | metatool-ai/metamcp | 聚合器 | [GitHub](https://github.com/metatool-ai/metamcp) | 🥉17；GUI 管理多 MCP |
| 29 | 1mcp-app/agent | 聚合器 | [GitHub](https://github.com/1mcp-app/agent) | 🥈18；多 MCP 合一 |
| 30 | Stripe MCP | 支付 | [Stripe MCP 文档](https://docs.stripe.com/mcp) | Stripe 官方；账单/支付集成 |

---

## 入门 5 件套（按场景）

### 编程 / 开发

| 工具 | 类型 | 为什么选它 |
|------|------|------------|
| GitHub (Connector) | ChatGPT App | 读仓库、Issue、PR，写代码必备上下文 |
| Supabase 或 Vercel | ChatGPT App | 快速搭后端/部署 |
| webapp-testing | Skill | 用 Playwright 自动测 Web 应用 |
| microsoft/playwright-mcp | MCP | 浏览器自动化与 E2E 测试 |
| oraios/serena | MCP | 符号级代码理解与编辑 |

### 研究 / 学习

| 工具 | 类型 | 为什么选它 |
|------|------|------------|
| Wolfram | ChatGPT App | 精确数学/科学计算，避免 LLM 算错 |
| Scholar GPT 或 Consensus | GPT Store | 学术文献检索与综述 |
| tavily-research | Skill | 多源深度调研 + 引用 |
| Hugging Face | ChatGPT App | 探索 ML 模型与数据集 |
| genomoncology/biomcp | MCP | 生物医学文献（PubMed 等） |

### 生活 / 日常

| 工具 | 类型 | 为什么选它 |
|------|------|------------|
| Spotify | ChatGPT App | 对话里做歌单、发现音乐 |
| Canva | ChatGPT App | 快速做海报、PPT、社交图 |
| Calendly | ChatGPT App | 约会议、查可用时间 |
| Gmail + Google Drive | Connectors | 邮件/文档上下文接入对话 |
| Expedia 或 Booking.com | ChatGPT App | 查机票酒店 |

---

## 数据来源

1. [awesome-chatgpt-apps](https://github.com/rdmgator12/awesome-chatgpt-apps) — ChatGPT Apps 社区目录（945+ Apps，2026-05）
2. [top-500-best-gpts](https://github.com/AINativeLab/top-500-best-gpts) — GPT Store 日榜（GPTsHunter）
3. [best-of-mcp-servers](https://github.com/tolkonepiu/best-of-mcp-servers) — MCP 质量排名（400 项目，每周更新）
4. [anthropics/skills](https://github.com/anthropics/skills) — Anthropic 官方 Agent Skills
5. [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) — 跨平台 Skills 合集
6. [cursor.com/marketplace](https://cursor.com/marketplace) — Cursor 官方插件/Skills 市场
7. [OpenAI Apps SDK 公告](https://openai.com/index/introducing-apps-in-chatgpt/) — DevDay 首发合作伙伴

## 局限与更新建议

- ChatGPT Apps / GPT Store **无公开 API 完整榜单**；Apps 以社区目录 + 官方 Featured 为准，GPT 以 GPTsHunter 日榜为准。
- MCP 生态 **每周变化**；建议每季度对照 `best-of-mcp-servers` 更新本清单。
- 大陆用户：部分 Apps/Connectors 可能受账号地区与网络影响，需自行验证可用性。
