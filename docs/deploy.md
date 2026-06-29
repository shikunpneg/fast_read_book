# 部署指南

## 推送 GitHub

```bash
git remote add origin git@github.com:shikunpneg/fast_read_book.git
git push -u origin main
```

## GitHub 仓库配置

### 1. 创建 Environment

1. 打开 https://github.com/shikunpneg/fast_read_book/settings/environments
2. 点击 **New environment**
3. Name: `pypi`
4. 勾选 **Required reviewers**（可选，提高安全性）
5. 保存

### 2. 配置 Pages

1. Settings → Pages
2. Source: **GitHub Actions**
3. 保存

## PyPI 配置 Trusted Publishing（OIDC）

> Trusted Publishing 是 PyPI 推荐的现代方式，**不需要在 GitHub 存 token**。

### 步骤

1. 打开 https://pypi.org/manage/account/publishing/
2. **Add a new pending publisher**：
   - **Owner**: `shikunpneg`
   - **Project name**: `kg-book-tool`
   - **Repository**: `fast_read_book`
   - **Workflow filename**: `release.yml`
   - **Environment name**: `pypi`（必须与 GitHub Environment 名一致）
3. 提交

> ⚠️ 1.0.0 已通过手动 twine upload 发布；trusted publisher 第一次跑需要先重新发布（v1.0.1）。

### 工作流

1. **在 GitHub 仓库** → Settings → Environments → `pypi`（必须已创建）
2. **PyPI** → Add pending publisher（按上面填写）
3. **从 PyPI 项目页** https://pypi.org/manage/project/kg-book-tool/publishing/ 确认 trusted publisher 状态从 pending → approved

## 发布新版本

```bash
# 1. 改 setup.py 中的 version
# 2. 改 CHANGELOG.md
git add -A
git commit -m "release: v1.0.1"
git tag v1.0.1
git push --tags
```

GitHub Actions 会自动：

- 跑测试（3 OS × 5 Python 版本）
- 构建 wheel + sdist
- 通过 Trusted Publishing 发布到 PyPI
- 创建 GitHub Release（自动从 CHANGELOG 提取发布说明）
- 部署文档到 GitHub Pages

## 故障排查

| 错误 | 解决 |
|------|------|
| `invalid-publisher` | 检查 PyPI trusted publisher 配置 + GitHub Environment 名称一致 |
| `Environment name 'pypi' not found` | 在 GitHub Settings → Environments 创建 `pypi` |
| `403 Forbidden on tag` | tag 必须是 `v*` 格式（如 `v1.0.0`） |
| `twine check` 失败 | `setup.py` 中 `long_description_content_type` 是否为 `text/markdown` |

## PyPI Token 备用方案（不推荐）

如果不想用 Trusted Publishing：

1. PyPI → Account settings → API tokens → Add token
2. GitHub → Settings → Secrets and variables → Actions → New repository secret
   - Name: `PYPI_API_TOKEN`
   - Value: `pypi-...`
3. 改 release.yml `publish` 步骤：
   ```yaml
   - name: Publish to PyPI (Token)
     env:
       TWINE_USERNAME: __token__
       TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
     run: twine upload dist/*
   ```
