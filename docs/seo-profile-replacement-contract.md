# SEO 配置替换规范与契约 (docs/seo-profile-replacement-contract.md)

本文件规定了如何通过替换 `site-seo-profile.json` 快速将本站升级或迁移至新的关键词矩阵。

## 替换流程：
1. 更新 `site-seo-profile.json` 中的 `primaryKeywords`、`secondaryKeywords`、`navigationItems` 等字段。
2. 运行 `python scripts/build_site.py` 重新生成静态 HTML。
3. 检查导航栏与首页 Hero 区域文案是否自动同步。
