# 桑伯恩地图公司：巴菲特投资逻辑图谱

> 来源：1961年1月30日致合伙人信 · 1960年了结 · 占净资产约35%

---

## 1. 总览：双重业务与核心矛盾

```mermaid
flowchart TB
    subgraph SAN["桑伯恩地图公司"]
        MAP["🗺️ 地图主业<br/>垄断75年 · 低资本 · 几乎不需销售"]
        PORT["📈 投资组合<br/>250万美元 · 债券+股票各半"]
    end

    MAP -->|"50年代「记分卡」承保兴起"| DECAY["主业利润崩塌<br/>50万/年 → 不足10万/年"]
    PORT -->|"留存收益持续投入"| GROW["组合欣欣向荣<br/>20美元/股 → 65美元/股"]

    DECAY --> GAP["市场定价扭曲"]
    GROW --> GAP

    GAP --> LOGIC["巴菲特逻辑：<br/>买投资组合打七折，<br/>地图业务负估值白送"]

    style DECAY fill:#fee,stroke:#c33
    style GROW fill:#efe,stroke:#3a3
    style LOGIC fill:#eef,stroke:#33c
```

---

## 2. 估值逻辑：1938 vs 1958

```mermaid
flowchart LR
    subgraph Y38["1938 · 萧条期"]
        P38["股价 110"]
        I38["组合 20"]
        M38["地图业务估值<br/>= 110 − 20<br/>= +90 ✅"]
        P38 --> M38
        I38 --> M38
    end

    subgraph Y58["1958 · 繁荣期"]
        P58["股价 45"]
        I58["组合 65"]
        M58["地图业务估值<br/>= 45 − 65<br/>= −20 ❌"]
        P58 --> M58
        I58 --> M58
    end

    Y38 -.->|"同样垄断性信息资产<br/>销售方式20年不变"| Y58

    style M38 fill:#efe,stroke:#3a3
    style M58 fill:#fee,stroke:#c33
```

**读法：** 分拆估值（SOTP）——隐藏资产被烂主业拖累，出现「负估值」安全边际。

---

## 3. 治理失灵：谁在做决策？

```mermaid
flowchart TB
    BOARD["14人董事会"]
    
    BOARD --> INS["9位保险界董事<br/>合计持股 46 股"]
    BOARD --> LAW["律师 10股"]
    BOARD --> BANK["银行家 10股 · 发现问题并增持"]
    BOARD --> MGT["2位高管 ~300股 · 清楚问题却无力"]
    BOARD --> HEIR["总裁遗孀 ~15,000股"]

    INS --> PROB1["几乎无股权 · 过去十年保险公司清一色卖出"]
    PORT_PROFIT["投资组合赚钱"] --> PROB2["董事觉得无需振兴地图"]
    PROB2 --> PROB3["8年股息削减5次<br/>未见降薪/压缩董事费用"]

    PROB1 --> STALE["因循守旧 → 盈利反映在产品形态落后"]
    PROB2 --> STALE
    PROB3 --> STALE

    style INS fill:#fee,stroke:#c33
    style STALE fill:#fdd,stroke:#933
```

---

## 4. 巴菲特行动链：从识别到了结

```mermaid
flowchart TD
    A["识别：组合65 + 股价45<br/>地图信息仍值千万美元级重建成本"] --> B["结盟大股东"]
    
    B --> B1["收购遗孀 ~15,000股"]
    B --> B2["券商客户 ~10,000股"]
    B --> B3["另一大股东 ~8,000股"]
    B --> B4["公开市场买入 ~24,000股"]
    
    B1 & B2 & B3 & B4 --> C["三方合计 ~46,000股"]

    C --> D["目标：拆分两项业务<br/>① 组合按公允价值兑现<br/>② 电子化复兴地图盈利"]

    D --> E{"董事会抵制<br/>管理层+博思艾伦支持"}
    
    E --> F["拟定退出方案<br/>避免委托书争夺战"]
    F --> G["SEC裁定公平合理"]

    G --> H["72%股份退出<br/>50%股东参与"]
    H --> I["退出方：获得组合对应证券公允价值"]
    H --> J["留守方：地图业务保留125万+债券<br/>消除100万+潜在资本利得税<br/>每股收益↑ 分红率↑"]

    I --> K["✅ 1960年按计划了结"]

    style A fill:#eef,stroke:#33c
    style K fill:#efe,stroke:#3a3
```

---

## 5. 投资类型定位（合伙基金策略谱系）

```mermaid
flowchart LR
    MAIN["主要利润来源"]
    
    MAIN --> U["低估证券<br/>买入 → 修复 → 卖出"]
    MAIN --> W["特殊情况 Workouts<br/>利润取决于公司行动<br/>而非市场走势"]
    MAIN --> C["控股型投资 ← 桑伯恩在此<br/>可遇不可求 · 需保密"]

    C --> LESSON1["持仓保密必要"]
    C --> LESSON2["一年不足以衡量成绩"]

    style C fill:#ffe,stroke:#cc3
    style U fill:#eef,stroke:#99c
    style W fill:#eef,stroke:#99c
```

---

## 6. 一图串起来：巴菲特完整推理链

```mermaid
flowchart TB
    START(["发现标的"]) --> S1["主业衰落<br/>记分卡蚕食地图承保"]
    START --> S2["隐藏资产壮大<br/>组合每股65美元"]
    START --> S3["股价仅45美元<br/>地图业务负估值"]

    S1 & S2 & S3 --> INSIGHT["安全边际 + 催化剂可能<br/>= 买资产打折扣"]

    INSIGHT --> BLOCK["障碍：无股权董事阻碍变革"]
    BLOCK --> ACTION["积累股权 + 结盟 + 推动分拆"]
    ACTION --> EXIT["公平退出方案 · SEC认可"]
    EXIT --> RESULT["释放组合公允价值<br/>1960年了结重仓"]

    RESULT --> META["元逻辑"]
    META --> M1["分部估值看隐藏资产"]
    META --> M2["低估需公司行动催化"]
    META --> M3["治理与激励决定能否兑现"]

    style INSIGHT fill:#ffe,stroke:#cc3
    style RESULT fill:#efe,stroke:#3a3
```

---

## 关键数字速查

| 项目 | 数值 |
|------|------|
| 基金仓位占比 | ~35% 净资产 |
| 1938 股价 / 组合 | 110 / 20 → 地图估值 +90 |
| 1958 股价 / 组合 | 45 / 65 → 地图估值 −20 |
| 地图业务利润（30年代 vs 1958-59） | 50万+ / 不足10万 |
| 仍有「地图」承保的火险保费 | 逾5亿美元 |
| 结盟后合计持股 | ~46,000 股 |
| 退出方案参与比例 | 72% 股份 · 50% 股东 |
