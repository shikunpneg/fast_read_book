# 部署指南

## 推送 GitHub

```bash
git remote add origin git@github.com:shikunpneg/fast_read_book.git
git push -u origin main
```

## 配置 PyPI Trusted Publishing（OIDC）

1. 打开 https://pypi.org/manage/account/publishing/
2. 添加 pending publisher：
   - Owner: `shikunpneg`
   - Repository: `fast_read_book`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. 保存

## GitHub 配置 Pages

1. 仓库 → Settings → Pages
2. Source: GitHub Actions
3. 保存

## 发布新版本

```bash
# 1. 改 setup.py version
# 2. 改 CHANGELOG.md
git add -A
git commit -m "release: v1.0.1"
git tag v1.0.1
git push --tags
```

GitHub Actions 会自动：

- 跑测试（3 OS × 5 Python 版本）
- 构建 wheel + sdist
- 发布到 PyPI
- 创建 GitHub Release（自动从 CHANGELOG 提取发布说明）
- 部署文档到 GitHub Pages
